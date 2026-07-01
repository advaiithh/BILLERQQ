"""
Planner — uses LLM to classify user intent and extract entities.

Takes the user's natural language message, sends it to Qwen3,
and returns a structured plan for the Executor to act on.
"""

import os
import logging
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FAST_PLANNER = os.getenv("FAST_PLANNER", "true").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

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
    "RECURRING",
    "OVERDUE",
    "STB_INFO",
    "GUIDE",
    "UNKNOWN",
}


class Planner:
    """Analyzes user messages and produces structured execution plans."""

    def __init__(self, llm):
        """
        Args:
            llm: An instance of BaseLLM (BedrockProvider).
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
            # Fast planner: handle common intents with simple regex and avoid an LLM call.
            if FAST_PLANNER or DEMO_MODE:
                fast_plan = self._fast_plan(message)
                if fast_plan:
                    logger.info("Fast plan: %s", fast_plan)
                    return fast_plan

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

    def _fast_plan(self, message: str) -> dict:
        """Quick regex-based classification for common queries."""
        text = message.strip().lower()

        if re.search(r"\b(guide|how to|where is|tell me about|what is|how do i|help)\b", text):
            category = "billerq"
            if "customer" in text:
                category = "customer"
            elif "payment" in text:
                category = "payment"
            elif "invoice" in text or "bill" in text:
                category = "invoice"
            elif "subscription" in text:
                category = "subscription"
            elif "complaint" in text:
                category = "complaint"
            elif "report" in text:
                category = "report"
            elif "chatbot" in text:
                category = "chatbot"
            return {"intent": "GUIDE", "entities": {"customer_name": category}, "uses_context": False, "confidence": 0.95}

        if re.search(r"\b(active customers|how many active customers|active customer)\b", text):
            return {"intent": "ACTIVE_CUSTOMERS", "entities": {}, "uses_context": False, "confidence": 0.9}

        if re.search(r"\b(package report|show package report|package summary)\b", text):
            return {"intent": "REPORT", "entities": {"report_type": "package"}, "uses_context": False, "confidence": 0.9}

        if re.search(r"\b(recent payments|show recent payments|payments today)\b", text):
            return {"intent": "RECENT_PAYMENTS", "entities": {}, "uses_context": False, "confidence": 0.9}

        if re.search(r"\b(overdue|payment due|due payments)\b", text):
            return {"intent": "OVERDUE", "entities": {}, "uses_context": False, "confidence": 0.9}

        if re.search(r"\b(unpaid customers|unpaid|collect outstanding)\b", text):
            return {"intent": "UNPAID_CUSTOMERS", "entities": {}, "uses_context": False, "confidence": 0.9}

        if re.search(r"\b(complaints|complaint status|complaint report)\b", text):
            return {"intent": "COMPLAINTS", "entities": {}, "uses_context": False, "confidence": 0.9}

        if re.search(r"\b(subscription|subscriptions|renewal)\b", text):
            return {"intent": "SUBSCRIPTION", "entities": {}, "uses_context": False, "confidence": 0.8}

        if re.search(r"\b(recurring|recurring profiles|recurring invoices)\b", text):
            return {"intent": "RECURRING", "entities": {}, "uses_context": False, "confidence": 0.9}

        return None

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
