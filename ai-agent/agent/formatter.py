"""
Formatter — converts raw API responses into human-friendly text.

Uses LLM for complex formatting (comparisons, analytics summaries)
and templates for simple cases to save LLM calls.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Load the formatter prompt template
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "formatter_prompt.txt"
_FORMATTER_SYSTEM_PROMPT = ""


def _load_prompt():
    global _FORMATTER_SYSTEM_PROMPT
    if not _FORMATTER_SYSTEM_PROMPT:
        _FORMATTER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
    return _FORMATTER_SYSTEM_PROMPT


class Formatter:
    """Formats raw API data into user-friendly chat responses."""

    def __init__(self, llm):
        """
        Args:
            llm: An instance of BaseLLM (OllamaProvider or BedrockProvider).
        """
        self.llm = llm

    async def format_response(
        self,
        intent: str,
        data: dict,
        original_message: str,
        customer_name: str = None,
    ) -> str:
        """Format API data into a human-readable response.

        Uses template formatting for simple cases, LLM for complex ones.

        Args:
            intent: The classified intent string.
            data: Raw API response data.
            original_message: The user's original question.
            customer_name: Resolved customer name (if applicable).

        Returns:
            Formatted response string for the chat.
        """
        # Handle error responses
        if not data:
            return "I couldn't find any data for your request. Please try again."

        if isinstance(data, dict) and "error" in data:
            return data["error"]

        if isinstance(data, dict) and "message" in data and len(data) == 1:
            return data["message"]

        # For complex data, use the LLM formatter
        return await self._llm_format(intent, data, original_message, customer_name)

    async def _llm_format(
        self,
        intent: str,
        data: dict,
        original_message: str,
        customer_name: str = None,
    ) -> str:
        """Use the LLM to format complex data into readable text."""
        system_prompt = _load_prompt()

        # Truncate data if too large (keep LLM context manageable)
        data_str = json.dumps(data, indent=2, default=str)
        if len(data_str) > 4000:
            data_str = data_str[:4000] + "\n... (data truncated for brevity)"

        user_prompt = (
            f"User's question: {original_message}\n"
            f"Intent: {intent}\n"
        )
        if customer_name:
            user_prompt += f"Customer: {customer_name}\n"
        user_prompt += f"\nRaw API data:\n{data_str}"

        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.3,
            )
            return response.strip()

        except Exception as e:
            logger.error("LLM formatting failed: %s", str(e))
            # Fallback: return a basic formatted version
            return self._fallback_format(intent, data, customer_name)

    def _fallback_format(self, intent: str, data: dict, customer_name: str = None) -> str:
        """Basic fallback formatting when LLM is unavailable."""
        parts = []

        if customer_name:
            parts.append(f"Results for {customer_name}:")
        else:
            parts.append("Here's what I found:")

        parts.append("")

        # Try to extract meaningful data
        if isinstance(data, dict):
            display_data = data.get("data", data)

            if isinstance(display_data, list):
                count = len(display_data)
                parts.append(f"Found {count} record(s).")
                # Show first 5 items
                for i, item in enumerate(display_data[:5]):
                    if isinstance(item, dict):
                        summary = ", ".join(
                            f"{k}: {v}" for k, v in list(item.items())[:4]
                        )
                        parts.append(f"  {i+1}. {summary}")
                if count > 5:
                    parts.append(f"  ... and {count - 5} more.")

            elif isinstance(display_data, dict):
                for key, value in list(display_data.items())[:10]:
                    if not key.startswith("_"):
                        parts.append(f"  {key}: {value}")
        else:
            parts.append(str(data)[:500])

        return "\n".join(parts)

    async def format_error(self, error_message: str, candidates: list = None) -> str:
        """Format an error response, optionally with candidate suggestions.

        Args:
            error_message: The error message.
            candidates: Optional list of candidate matches for ambiguous queries.

        Returns:
            Formatted error response string.
        """
        parts = [error_message]

        if candidates:
            parts.append("")
            parts.append("Did you mean one of these?")
            for i, c in enumerate(candidates, 1):
                name = c.get("name", "Unknown")
                area = c.get("area", "")
                mobile = c.get("mobile", "")
                detail = f"  {i}. {name}"
                if area:
                    detail += f" ({area})"
                if mobile:
                    detail += f" — {mobile}"
                parts.append(detail)

        return "\n".join(parts)
