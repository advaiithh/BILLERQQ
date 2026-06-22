"""
Resolver — converts natural-language entity references to BillerQ API IDs.

Example:
    "Joy P" → customer_id: 44350
"""

import logging
from typing import Optional

from tools.customer import search_customer

logger = logging.getLogger(__name__)


class Resolver:
    """Resolves human-readable names to system IDs via the BillerQ search API."""

    async def resolve_customer(self, name: str) -> dict:
        """Resolve a customer name/mobile to their customer record.

        Args:
            name: Customer name, mobile number, or subscriber ID.

        Returns:
            dict with keys:
                - "found": bool
                - "customer_id": int (if found)
                - "customer_name": str (if found)
                - "customer_data": dict (full record if found)
                - "candidates": list (if multiple matches)
                - "error": str (if not found)
        """
        # Clean up common prefixes from the search name (e.g., "subscriber 1322" -> "1322")
        cleaned_name = name.strip()
        for prefix in [
            "subscriber id ", "subscriber id", 
            "subscriber no ", "subscriber no", 
            "subscriber ", 
            "sub id ", "sub id", 
            "customer id ", "customer id", 
            "customer ", 
            "id "
        ]:
            if cleaned_name.lower().startswith(prefix):
                cleaned_name = cleaned_name[len(prefix):].strip()
                break

        logger.info("Resolving customer: '%s' (cleaned: '%s')", name, cleaned_name)

        try:
            response = await search_customer(cleaned_name)
        except Exception as e:
            logger.error("Customer search API failed: %s", str(e))
            return {
                "found": False,
                "error": f"Failed to search for customer: {str(e)}",
            }

        # Extract the customer list from the response
        customers = self._extract_customers(response)

        if not customers:
            return {
                "found": False,
                "error": f"No customer found matching '{name}'.",
            }

        # Exact match (single result)
        if len(customers) == 1:
            customer = customers[0]
            return self._build_found_result(customer)

        # Multiple results — try to find the best match
        best = self._find_best_match(customers, cleaned_name)
        if best:
            return self._build_found_result(best)

        # Multiple ambiguous matches — return candidates
        candidates = [
            {
                "id": c.get("id") or c.get("customer_id"),
                "name": c.get("name") or c.get("customer_name", "Unknown"),
                "area": c.get("area_name") or c.get("area", ""),
                "mobile": c.get("mobile") or c.get("phone", ""),
            }
            for c in customers[:5]  # Cap at 5 candidates
        ]

        return {
            "found": False,
            "error": f"Multiple customers found matching '{name}'. Please be more specific.",
            "candidates": candidates,
        }

    async def resolve_customers(self, names: list[str]) -> list[dict]:
        """Resolve multiple customer names in parallel.

        Args:
            names: List of customer names to resolve.

        Returns:
            List of resolution results (one per name).
        """
        import asyncio
        tasks = [self.resolve_customer(name) for name in names]
        return await asyncio.gather(*tasks)

    def _extract_customers(self, response: dict) -> list:
        """Extract customer list from various API response formats."""
        if isinstance(response, list):
            return response

        if isinstance(response, dict):
            # Try common response wrapper keys
            for key in ["data", "customers", "customer", "results"]:
                if key in response:
                    val = response[key]
                    if isinstance(val, list):
                        return val
                    if isinstance(val, dict):
                        return [val]

            # Maybe the response itself is a single customer record
            if "id" in response or "customer_id" in response:
                return [response]

        return []

    def _find_best_match(self, customers: list, name: str) -> Optional[dict]:
        """Find the best matching customer by name, subscriber_id, or mobile similarity.

        Uses case-insensitive exact match first, then substring match.
        """
        name_lower = name.lower().strip()

        # Pass 1: exact match on subscriber_id
        for c in customers:
            c_sub = str(c.get("subscriber_id") or "").lower().strip()
            if c_sub == name_lower:
                return c

        # Pass 2: exact match on mobile
        for c in customers:
            c_mob = str(c.get("mobile") or c.get("phone") or "").lower().strip()
            # Remove country code prefix if query doesn't have it, or vice versa
            if c_mob == name_lower or c_mob.endswith(name_lower) or name_lower.endswith(c_mob):
                return c

        # Pass 3: exact match on name
        for c in customers:
            c_name = (c.get("name") or c.get("customer_name") or "").lower().strip()
            if c_name == name_lower:
                return c

        # Pass 4: name starts with query
        for c in customers:
            c_name = (c.get("name") or c.get("customer_name") or "").lower().strip()
            if c_name.startswith(name_lower):
                return c

        # Pass 5: query is contained in name
        for c in customers:
            c_name = (c.get("name") or c.get("customer_name") or "").lower().strip()
            if name_lower in c_name:
                return c

        return None

    def _build_found_result(self, customer: dict) -> dict:
        """Build a successful resolution result from a customer record."""
        customer_id = customer.get("id") or customer.get("customer_id")
        customer_name = customer.get("name") or customer.get("customer_name") or "Unknown"

        logger.info("Resolved '%s' → ID %s", customer_name, customer_id)

        return {
            "found": True,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "customer_data": customer,
        }


# Singleton
resolver = Resolver()
