"""
AWS Bedrock LLM provider — connects to AWS Bedrock to run Claude 3 Haiku
using the modern Converse API (boto3 client.converse()).
"""

import os
import re
import json
import logging
import asyncio
import boto3
from botocore.exceptions import ClientError

from llm.base import BaseLLM

logger = logging.getLogger(__name__)


class BedrockProvider(BaseLLM):
    """LLM provider using AWS Bedrock with Claude 3 Haiku via the Converse API."""

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
    ):
        # Allow override from arguments or environment variables
        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        )
        self.region = (
            region
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "us-east-1"
        )

        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        # Create bedrock-runtime client
        client_kwargs = {
            "service_name": "bedrock-runtime",
            "region_name": self.region,
        }
        if aws_access_key and aws_secret_key:
            client_kwargs["aws_access_key_id"] = aws_access_key
            client_kwargs["aws_secret_access_key"] = aws_secret_key

        logger.info(
            "Initializing BedrockProvider (Converse API) with model_id=%s, region=%s",
            self.model_id,
            self.region,
        )
        self.client = boto3.client(**client_kwargs)
        self.last_usage = {"input_tokens": 0, "output_tokens": 0}


    # -----------------------------------------------------------------
    # Public interface (matches BaseLLM + extended chat methods)
    # -----------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.3,
        num_predict: int = 2048,
    ) -> str:
        """Generate a text response from a single user prompt."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        return await self._converse(messages, system, temperature, num_predict)

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        num_predict: int = 2048,
    ) -> dict:
        """Generate a structured JSON response from a single user prompt."""
        raw = await self.generate(prompt, system, temperature, num_predict)
        return self._parse_json(raw)

    async def chat(
        self,
        messages: list,
        temperature: float = 0.3,
        num_predict: int = 2048,
        system: str = "",
    ) -> str:
        """Generate a chat response using a list of messages.

        Args:
            messages: List of message dicts, e.g. [{"role": "user", "content": "..."}]
                      Content can be a plain string or already in Converse format
                      [{"text": "..."}].
            temperature: Sampling temperature.
            num_predict: Maximum number of tokens to generate.
            system: Optional system prompt.

        Returns:
            The generated text response.
        """
        # Convert incoming messages to Converse API format
        converse_messages = []
        extracted_system = system

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            # Pull system messages out — Converse API takes them separately
            if role == "system":
                if not extracted_system:
                    extracted_system = content if isinstance(content, str) else ""
                continue

            # Normalise content to Converse format: list of content blocks
            if isinstance(content, str):
                content_blocks = [{"text": content}]
            elif isinstance(content, list):
                content_blocks = content
            else:
                content_blocks = [{"text": str(content)}]

            converse_messages.append({"role": role, "content": content_blocks})

        return await self._converse(
            converse_messages, extracted_system, temperature, num_predict
        )

    async def chat_json(
        self,
        messages: list,
        temperature: float = 0.1,
        num_predict: int = 2048,
        system: str = "",
    ) -> dict:
        """Generate a structured JSON response from a chat session."""
        raw = await self.chat(messages, temperature, num_predict, system)
        return self._parse_json(raw)

    # -----------------------------------------------------------------
    # Core Converse API call
    # -----------------------------------------------------------------

    async def _converse(
        self,
        messages: list,
        system: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Call Bedrock Converse API and return the text response.

        Args:
            messages: Messages in Converse format
                      [{"role": "user", "content": [{"text": "..."}]}]
            system: System prompt string.
            temperature: Sampling temperature (0.0–1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            The model's text response.
        """
        # Build the Converse API request
        request_kwargs = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system:
            request_kwargs["system"] = [{"text": system}]

        try:
            # converse() is a synchronous boto3 call; run in executor
            loop = asyncio.get_event_loop()

            def _invoke():
                return self.client.converse(**request_kwargs)

            response = await loop.run_in_executor(None, _invoke)

            # Extract text from the response
            output_message = response["output"]["message"]
            content_blocks = output_message.get("content", [])

            text_parts = []
            for block in content_blocks:
                if "text" in block:
                    text_parts.append(block["text"])

            return "\n".join(text_parts).strip()

        except ClientError as e:
            error_msg = e.response["Error"]["Message"]
            logger.error("Bedrock Converse API error: %s", error_msg)
            raise RuntimeError(f"Bedrock Converse API error: {error_msg}") from e
        except Exception as e:
            logger.error("Bedrock generation failed: %s", str(e))
            raise RuntimeError(f"LLM generation failed: {str(e)}") from e

    # -----------------------------------------------------------------
    # JSON parsing helper
    # -----------------------------------------------------------------

    def _parse_json(self, raw: str) -> dict:
        """Extract a JSON object from the LLM's raw text response."""
        # Try direct parse first
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code fences: ```json ... ``` or ``` ... ```
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object in the response
        brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from LLM response: %s", raw[:200])
        return {"error": "Failed to parse structured response", "raw": raw}

    def get_and_reset_usage(self) -> dict:
        """Retrieve and reset the token usage metrics from recent operations."""
        usage = self.last_usage.copy()
        self.last_usage = {"input_tokens": 0, "output_tokens": 0}
        return usage

