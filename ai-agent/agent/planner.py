"""
Planner — uses LLM to classify user intent and extract entities.

Takes the user's natural language message, sends it to Qwen3,
and returns a structured plan for the Executor to act on.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Load the planner prompt template
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_prompt.txt"
_PLANNER_SYSTEM_PROMPT = ""

def _load_prompt():
    global _PLANNER_SYSTEM_PROMPT
    if not _PLANNER_SYSTEM_PROMPT:
        _PLANNER_SYSTEM_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")
    return _PLANNER_SYSTEM_PROMPT


# Valid intents the planner can output
VALID_INTENTS = {
    "CUSTOMER_SEARCH",
    "CUSTOMER_PROFILE",
    "PAYMENT_HISTORY",
    "RECENT_PAYMENTS",
    "UNPAID_CUSTOMERS",
    "SUBSCRIPTION",
    "EXPIRING_SUBSCRIPTIONS",
    "COMPARE_CUSTOMERS",
    "AREA_CUSTOMERS",
    "ACTIVE_CUSTOMERS",
    "ANALYTICS",
    "REPORT",
    "COMPLAINTS",
    "OVERDUE",
    "STB_INFO",
    "UNKNOWN",
}


class Planner:
    """Analyzes user messages and produces structured execution plans."""

    def __init__(self, llm):
        """
        Args:
            llm: An instance of BaseLLM (OllamaProvider or BedrockProvider).
        """
        self.llm = llm

    async def plan(self, message: str, context: dict = None) -> dict:
        """Analyze a user message and produce a structured plan.

        Args:
            message: The user's raw message text.
            context: Session context from ConversationMemory.get_context().

        Returns:
            A plan dict with keys:
                - intent: str (one of VALID_INTENTS)
                - entities: dict (extracted entities)
                - uses_context: bool
                - confidence: float
        """
        system_prompt = _load_prompt()

        # Build the user prompt with context if available
        user_prompt = self._build_prompt(message, context)

        logger.info("Planning for message: '%s'", message[:100])

        try:
            plan = await self.llm.generate_json(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.1,  # Low temp for consistent classification
            )

            # Validate and sanitize the plan
            plan = self._validate_plan(plan, message)

            logger.info(
                "Plan: intent=%s, entities=%s, uses_context=%s",
                plan.get("intent"),
                plan.get("entities"),
                plan.get("uses_context"),
            )

            return plan

        except Exception as e:
            logger.error("Planning failed: %s", str(e))
            return {
                "intent": "UNKNOWN",
                "entities": {},
                "uses_context": False,
                "confidence": 0.0,
                "error": str(e),
            }

    def _build_prompt(self, message: str, context: dict = None) -> str:
        """Build the user prompt, including conversation context if available."""
        parts = []

        if context and context.get("history"):
            parts.append("Recent conversation:")
            for turn in context["history"][-3:]:  # Last 3 turns
                parts.append(f"User: {turn['user']}")
                parts.append(f"Assistant: {turn['assistant'][:100]}...")
            parts.append("")

        if context and context.get("last_customer_name"):
            parts.append(
                f"Last referenced customer: {context['last_customer_name']} "
                f"(ID: {context['last_customer_id']})"
            )
            parts.append("")

        parts.append(f"User message: {message}")

        return "\n".join(parts)

    def _validate_plan(self, plan: dict, original_message: str) -> dict:
        """Validate and sanitize the LLM's plan output."""
        # Check for parse errors
        if "error" in plan:
            return {
                "intent": "UNKNOWN",
                "entities": {},
                "uses_context": False,
                "confidence": 0.0,
                "error": plan.get("error", "Failed to parse plan"),
            }

        # Validate intent
        intent = plan.get("intent", "UNKNOWN").upper()
        if intent not in VALID_INTENTS:
            logger.warning("Invalid intent '%s', falling back to UNKNOWN", intent)
            intent = "UNKNOWN"
        plan["intent"] = intent

        # Ensure entities dict exists
        if "entities" not in plan or not isinstance(plan["entities"], dict):
            plan["entities"] = {}

        # Ensure uses_context is a bool
        plan["uses_context"] = bool(plan.get("uses_context", False))

        # Ensure confidence is a float
        try:
            plan["confidence"] = float(plan.get("confidence", 0.5))
        except (TypeError, ValueError):
            plan["confidence"] = 0.5

        return plan
