"""
Formatter — converts raw API responses into human-friendly text.

Uses LLM for complex formatting (comparisons, analytics summaries)
and templates for simple cases to save LLM calls.
"""

import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Demo mode or simple response formatting should avoid an LLM call
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"
SIMPLE_FORMAT_INTENTS = {
    "ACTIVE_CUSTOMERS",
    "RECENT_PAYMENTS",
    "UNPAID_CUSTOMERS",
    "OVERDUE",
    "COMPLAINTS",
    "RECURRING",
    "ANALYTICS",
    "REPORT",
}

# Load the formatter prompt template
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "formatter_prompt.txt"
_FORMATTER_SYSTEM_PROMPT = ""


def _load_prompt():
    global _FORMATTER_SYSTEM_PROMPT
    if not _FORMATTER_SYSTEM_PROMPT:
        _FORMATTER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
    return _FORMATTER_SYSTEM_PROMPT


def sanitize_and_truncate_data(data, max_list_len=5):
    """Recursively traverses data to truncate lists to a maximum length to prevent context limit errors."""
    if isinstance(data, list):
        if len(data) > max_list_len:
            truncated = [sanitize_and_truncate_data(item, max_list_len) for item in data[:max_list_len]]
            truncated.append(f"... ({len(data) - max_list_len} more items truncated)")
            return truncated
        return [sanitize_and_truncate_data(item, max_list_len) for item in data]
    
    if isinstance(data, dict):
        return {
            k: sanitize_and_truncate_data(v, max_list_len)
            for k, v in data.items()
        }
        
    return data


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

        # Use fallback formatting for demo mode and simple intents to avoid a slow LLM call.
        if DEMO_MODE or intent in SIMPLE_FORMAT_INTENTS:
            return self._fallback_format(intent, data, customer_name)

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

        # Intelligently truncate lists to keep JSON structure and other keys intact
        truncated_data = sanitize_and_truncate_data(data, max_list_len=5)
        data_str = json.dumps(truncated_data, indent=2, default=str)
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

                # Try to sort by a date-like key so we show the most recent items
                date_keys = [
                    "date",
                    "created_at",
                    "formatted_created_at",
                    "payment_date",
                    "due_date",
                    "updated_at",
                ]

                def _find_date_key(item):
                    for k in date_keys:
                        if isinstance(item, dict) and k in item and item.get(k):
                            return k
                    return None

                sort_key = None
                # discover a key present in at least one item
                for item in display_data[:10]:
                    k = _find_date_key(item)
                    if k:
                        sort_key = k
                        break

                if sort_key:
                    try:
                        sorted_list = sorted(
                            display_data,
                            key=lambda x: x.get(sort_key) or "",
                            reverse=True,
                        )
                    except Exception:
                        sorted_list = display_data
                else:
                    sorted_list = display_data

                parts.append("Most recent:")
                name_keys = ["customer_name", "name", "full_name", "subscriber_name", "customer"]

                for i, item in enumerate(sorted_list[:5]):
                    if isinstance(item, dict):
                        name = None
                        for nk in name_keys:
                            if nk in item and item.get(nk):
                                name = item.get(nk)
                                break

                        extra = []
                        # include date/amount snippet if available
                        for k in (sort_key, "amount", "outstanding", "days_overdue", "status", "problem_type", "package_name", "type", "start_date"):
                            if k and isinstance(item.get(k), (str, int, float)) and item.get(k):
                                extra.append(f"{k}: {item.get(k)}")

                        summary = name if name else ", ".join(f"{k}: {v}" for k, v in list(item.items())[:4])
                        if extra:
                            summary = f"{summary} ({'; '.join(extra)})"

                        parts.append(f"  {i+1}. {summary}")
                    else:
                        parts.append(f"  {i+1}. {str(item)[:120]}")

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
