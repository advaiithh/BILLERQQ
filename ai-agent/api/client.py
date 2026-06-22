"""
Centralized HTTP client for BillerQ API communication.

This is the ONLY file that makes HTTP requests to the BillerQ backend.
All tools route through this client for consistent auth, retries, and logging.

Auth strategy:
    - On first API call, logs in with email/password from .env to get a token.
    - On 401 Unauthorized, automatically re-logs-in and retries once.
    - Optionally accepts a per-request token (from the BillerQ frontend session).
"""

import os
import time
import logging
import asyncio
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from api.registry import get_endpoint

load_dotenv()

logger = logging.getLogger(__name__)


class BillerQClient:
    """Async HTTP client for the BillerQ API.

    Features:
        - Auto-login via email/password to obtain bearer token
        - Automatic token refresh on 401 Unauthorized
        - Connection pooling via httpx.AsyncClient
        - Automatic retry with exponential backoff (3 attempts)
        - Request/response logging
        - Per-request token override (for frontend user sessions)
        - Configurable timeout (30s default)
    """

    def __init__(self):
        self.base_url = os.getenv("BILLERQ_API_BASE", "https://admin.billerq.com/public/api").rstrip("/")
        self.login_email = os.getenv("BILLERQ_LOGIN_EMAIL", "")
        self.login_password = os.getenv("BILLERQ_LOGIN_PASSWORD", "")
        try:
            self.industry_id = int(os.getenv("BILLERQ_INDUSTRY_ID", "1"))
        except ValueError:
            self.industry_id = 1
        self.timeout = 30.0
        self.max_retries = 3
        self._client: Optional[httpx.AsyncClient] = None
        self._token: Optional[str] = None
        self._token_time: float = 0
        self._login_lock = asyncio.Lock()
        # Set by the executor to override the token for a single request batch
        self._request_token_override: Optional[str] = None

    # ------------------------------------------------------------------
    # Token Management
    # ------------------------------------------------------------------

    async def _ensure_token(self):
        """Ensure we have a valid bearer token, logging in if needed."""
        if self._token:
            return
        await self._login()

    async def _login(self):
        """Authenticate with BillerQ and store the bearer token.

        Calls POST /login with email and password.
        The response contains a token string like '23765|VsM9p...'.
        """
        async with self._login_lock:
            # Double-check after acquiring lock (another coroutine may have logged in)
            if self._token and (time.time() - self._token_time) < 60:
                return

            if not self.login_email or not self.login_password:
                raise RuntimeError(
                    "BillerQ login credentials not configured. "
                    "Set BILLERQ_LOGIN_EMAIL and BILLERQ_LOGIN_PASSWORD in .env"
                )

            login_url = f"{self.base_url}/login"
            logger.info("Logging in to BillerQ API at %s (industry_id: %d) ...", login_url, self.industry_id)

            try:
                # Use a temporary client for login to avoid auth header issues
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as temp_client:
                    response = await temp_client.post(
                        login_url,
                        json={
                            "email": self.login_email,
                            "password": self.login_password,
                            "industry_id": self.industry_id,
                        },
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                # Extract token from response
                # BillerQ returns token in various possible keys
                token = (
                    data.get("token")
                    or data.get("access_token")
                    or data.get("plainTextToken")
                    or data.get("data", {}).get("token")
                    or data.get("data", {}).get("access_token")
                )

                if not token:
                    logger.error("Login response has no token. Response keys: %s", list(data.keys()))
                    raise RuntimeError(
                        f"Login succeeded but no token found in response. "
                        f"Response keys: {list(data.keys())}"
                    )

                self._token = str(token)
                self._token_time = time.time()

                # Dynamically update the base URL to the tenant/company URL returned by the login
                returned_url = data.get("data", {}).get("url")
                if returned_url:
                    old_base = self.base_url
                    self.base_url = returned_url.rstrip("/")
                    logger.info("Updated base URL from %s to %s", old_base, self.base_url)

                # Close existing client so the next request creates one with the new token & base URL
                await self._close_client()

                logger.info("✅ Login successful — token obtained (expires on next login)")

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Login failed: HTTP %d — %s",
                    e.response.status_code, e.response.text[:300],
                )
                raise RuntimeError(
                    f"BillerQ login failed: HTTP {e.response.status_code}. "
                    f"Check your email/password in .env"
                ) from e
            except Exception as e:
                logger.error("Login failed: %s", str(e))
                raise RuntimeError(f"BillerQ login failed: {str(e)}") from e

    def _get_headers(self, override_token: Optional[str] = None) -> dict:
        """Build request headers with Bearer token.

        Args:
            override_token: If provided, use this token instead of the agent's own.
        """
        token = override_token or self._token
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    # ------------------------------------------------------------------
    # HTTP Client Management
    # ------------------------------------------------------------------

    async def _get_client(self, override_token: Optional[str] = None) -> httpx.AsyncClient:
        """Get or create the shared async HTTP client."""
        if override_token:
            # For per-request tokens, create a temporary client
            return httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(override_token),
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )

        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self._get_headers(),
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
        return self._client

    async def _close_client(self):
        """Close the internal HTTP client (used when token changes)."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def close(self):
        """Close the HTTP client and release connections."""
        await self._close_client()

    # ------------------------------------------------------------------
    # Request Execution
    # ------------------------------------------------------------------

    async def _request_with_retry(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
        override_token: Optional[str] = None,
    ) -> dict:
        """Execute an HTTP request with retry logic and auto-login.

        Args:
            method: HTTP method ("GET" or "POST").
            endpoint: The API path (e.g., "/admin/show-customer").
            params: Query parameters for GET requests.
            json_data: JSON body for POST requests.
            override_token: If provided, use this token instead of auto-login.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            RuntimeError: If all retry attempts fail.
        """
        # Ensure we have logged in at least once to resolve the tenant base URL
        await self._ensure_token()

        # Clean up the endpoint path
        req_endpoint = endpoint
        if not req_endpoint.startswith("/"):
            req_endpoint = f"/{req_endpoint}"

        # Track whether we've already retried after a 401
        retried_after_401 = False
        use_temp_client = override_token is not None

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                client = await self._get_client(override_token)

                logger.info(
                    "API %s %s (attempt %d/%d) params=%s",
                    method, req_endpoint, attempt, self.max_retries, params,
                )

                if method.upper() == "GET":
                    response = await client.get(req_endpoint, params=params)
                elif method.upper() == "POST":
                    response = await client.post(req_endpoint, json=json_data, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Log response status
                logger.info(
                    "API response: %d %s (%d bytes)",
                    response.status_code,
                    response.reason_phrase,
                    len(response.content),
                )

                # Handle 401 — token expired, re-login and retry once
                if response.status_code == 401 and not retried_after_401 and not override_token:
                    retried_after_401 = True
                    logger.warning("Got 401 Unauthorized — token expired, re-logging in...")
                    self._token = None
                    await self._login()
                    # Don't count this as a retry attempt
                    continue

                # Raise for other HTTP errors (4xx, 5xx)
                response.raise_for_status()

                return response.json()

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    "API HTTP error %d on attempt %d: %s",
                    e.response.status_code, attempt, str(e),
                )
                # Don't retry client errors (4xx) except 429 (rate limit)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise RuntimeError(
                        f"API request failed: HTTP {e.response.status_code} — {e.response.text[:200]}"
                    ) from e

            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_error = e
                logger.warning(
                    "API connection error on attempt %d: %s",
                    attempt, str(e),
                )

            except Exception as e:
                last_error = e
                logger.error("Unexpected API error on attempt %d: %s", attempt, str(e))

            finally:
                # Clean up temporary client if we created one
                if use_temp_client and client and not client.is_closed:
                    await client.aclose()

            # Exponential backoff before retry
            if attempt < self.max_retries:
                wait_time = 2 ** attempt
                logger.info("Retrying in %ds...", wait_time)
                await asyncio.sleep(wait_time)

        raise RuntimeError(
            f"API request failed after {self.max_retries} attempts: {str(last_error)}"
        ) from last_error

    # ------------------------------------------------------------------
    # Public API Methods
    # ------------------------------------------------------------------

    async def get(
        self,
        registry_key: str,
        params: Optional[dict] = None,
        override_token: Optional[str] = None,
    ) -> dict:
        """Make a GET request using a registry key.

        Args:
            registry_key: Logical name from API_REGISTRY (e.g., "show_customer").
            params: Optional query parameters.
            override_token: Optional token to use instead of the agent's own.

        Returns:
            Parsed JSON response.
        """
        token = override_token or self._request_token_override
        endpoint = get_endpoint(registry_key)
        return await self._request_with_retry("GET", endpoint, params=params, override_token=token)

    async def post(
        self,
        registry_key: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        override_token: Optional[str] = None,
    ) -> dict:
        """Make a POST request using a registry key.

        Args:
            registry_key: Logical name from API_REGISTRY.
            data: JSON body to send.
            params: Optional query parameters.
            override_token: Optional token to use instead of the agent's own.

        Returns:
            Parsed JSON response.
        """
        token = override_token or self._request_token_override
        endpoint = get_endpoint(registry_key)
        return await self._request_with_retry("POST", endpoint, params=params, json_data=data, override_token=token)

    async def get_raw(
        self,
        endpoint_path: str,
        params: Optional[dict] = None,
        override_token: Optional[str] = None,
    ) -> dict:
        """Make a GET request using a raw endpoint path (bypass registry).

        Use this only when the registry key doesn't exist.

        Args:
            endpoint_path: Full API path (e.g., "/admin/some-endpoint").
            params: Optional query parameters.
            override_token: Optional token to use instead of the agent's own.

        Returns:
            Parsed JSON response.
        """
        token = override_token or self._request_token_override
        return await self._request_with_retry("GET", endpoint_path, params=params, override_token=token)


# Singleton instance — import and use throughout the app
api_client = BillerQClient()
