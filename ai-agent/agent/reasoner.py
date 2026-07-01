"""
Reasoner — generates multi-step execution plans from user goals and entities.
Uses the API Metadata Registry to dynamically choose tool paths.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class Reasoner:
    """Translates user intents and goals into sequential execution steps."""

    def __init__(self, llm=None):
        self.llm = llm
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """Load api_registry.json file."""
        registry_path = Path(__file__).parent.parent / "metadata" / "api_registry.json"
        if registry_path.exists():
            try:
                return json.loads(registry_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Failed to parse api_registry.json: %s", str(e))
        return {}

    async def generate_plan(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate a sequential plan of execution.

        Args:
            intent: The high-level intent/goal (e.g., "CUSTOMER_PROFILE", "ANALYTICS", "COMPARE_CUSTOMERS").
            entities: Extracted entity parameters.
            context: Stored conversation memory.

        Returns:
            A dict with key "steps", which is a list of step dicts.
            Each step: {"tool": "registry_key", "arguments": {...}, "action": "optional_action"}
        """
        logger.info("Generating plan for intent: %s", intent)

        # 1. Rule-based fast paths for simple intents to maximize speed/reliability
        rule_plan = self._get_rule_based_plan(intent, entities, context)
        if rule_plan:
            logger.info("Using deterministic rule-based plan: %s", rule_plan)
            return rule_plan

        # 2. Generative multi-step planner for complex queries
        if self.llm:
            try:
                return await self._generate_llm_plan(intent, entities, context)
            except Exception as e:
                logger.error("LLM reasoning failed: %s. Falling back to default plan.", str(e))

        # 3. Fallback plan if LLM is not available or failed
        return self._get_fallback_plan(intent, entities)

    def _get_rule_based_plan(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Simple mapping for fast execution of standard single-intent tools."""
        customer_name = entities.get("customer_name")
        mobile = entities.get("mobile")

        # Map basic customer intents
        if intent == "CUSTOMER_PROFILE":
            return {
                "steps": [
                    {
                        "tool": "get_customer_profile",
                        "arguments": {"customer_id": "$customer_id"},
                        "description": "Fetch customer details"
                    }
                ]
            }
        
        elif intent == "PAYMENT_HISTORY":
            return {
                "steps": [
                    {
                        "tool": "payment_history",
                        "arguments": {"customer_id": "$customer_id"},
                        "description": "Fetch customer payments"
                    }
                ]
            }

        elif intent == "SUBSCRIPTION":
            return {
                "steps": [
                    {
                        "tool": "show_subscription",
                        "arguments": {"customer_id": "$customer_id"},
                        "description": "Fetch customer subscription"
                    }
                ]
            }

        elif intent == "STB_INFO":
            return {
                "steps": [
                    {
                        "tool": "get_single_stb",
                        "arguments": {"customer_id": "$customer_id"},
                        "description": "Fetch set-top box info"
                    }
                ]
            }

        elif intent == "RECENT_PAYMENTS":
            return {
                "steps": [
                    {
                        "tool": "get_recent_payment",
                        "arguments": {},
                        "description": "Get recent system payments"
                    }
                ]
            }

        elif intent == "UNPAID_CUSTOMERS":
            return {
                "steps": [
                    {
                        "tool": "get_unpaid_customers",
                        "arguments": {},
                        "description": "Get unpaid customer list"
                    }
                ]
            }

        elif intent == "OVERDUE":
            return {
                "steps": [
                    {
                        "tool": "overdues",
                        "arguments": {},
                        "description": "Get overdue summary data"
                    }
                ]
            }

        elif intent == "CUSTOMER_SEARCH":
            # Direct search
            query = customer_name or mobile or ""
            return {
                "steps": [
                    {
                        "tool": "show_customer",
                        "arguments": {"search_value": query},
                        "description": f"Search customers matching '{query}'"
                    }
                ]
            }

        elif intent == "AREA_CUSTOMERS":
            area = entities.get("area_name", "")
            return {
                "steps": [
                    {
                        "tool": "show_customer",
                        "arguments": {},
                        "action": "filter_by_area",
                        "area_name": area,
                        "description": f"Fetch all customers and filter by area '{area}'"
                    }
                ]
            }

        elif intent == "ACTIVE_CUSTOMERS":
            return {
                "steps": [
                    {
                        "tool": "get_customer_status_count",
                        "arguments": {},
                        "description": "Fetch status-wise customer counts"
                    }
                ]
            }

        # Dynamic multi-step default for complaints
        elif intent == "COMPLAINTS":
            return {
                "steps": [
                    {
                        "tool": "get_complaint",
                        "arguments": {},
                        "description": "Get all complaints"
                    },
                    {
                        "tool": "complaint_status_count",
                        "arguments": {},
                        "description": "Get complaints status count"
                    }
                ]
            }

        # Dynamic multi-step default for business analytics
        elif intent == "ANALYTICS":
            return {
                "steps": [
                    {"tool": "get_dashboard_data", "arguments": {}, "description": "Get dashboard metrics"},
                    {"tool": "get_connection_data", "arguments": {}, "description": "Get collection charts and agents"},
                    {"tool": "get_customer_status_count", "arguments": {}, "description": "Get customer status counts"},
                    {"tool": "complaint_status_count", "arguments": {}, "description": "Get complaints counts"},
                    {"tool": "package_report", "arguments": {}, "description": "Get packages report"}
                ]
            }

        return None

    async def _generate_llm_plan(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Use LLM (Qwen) to build a multi-step dynamic execution plan based on the registry."""
        registry_str = json.dumps(self.registry, indent=2)
        
        system_instruction = (
            "You are the Reasoner module of BillerQ AI Assistant. Your job is to convert user requests into a list of API tool steps.\n"
            "Produce ONLY valid JSON with a single key 'steps'. No explanation, no comments, no thinking blocks.\n\n"
            f"Available APIs from the Registry:\n{registry_str}\n\n"
            "Each step must be formatted as:\n"
            "{\n"
            "  \"tool\": \"registry_key_name\",\n"
            "  \"arguments\": {\"param1\": \"val1\"},\n"
            "  \"action\": \"optional_processing_instruction\" (e.g. \"compare\", \"group_by\", \"filter\")\n"
            "}\n\n"
            "Rules:\n"
            "1. If customer details/profile/payments/subscriptions are needed, include tool calls with parameter 'customer_id'. Use place-holder '$customer_id' or '$customer_id_X' (where X is 0, 1, etc.) if multiple customers need resolution.\n"
            "2. For comparisons, plan tool calls for each customer name in customer_names.\n"
            "3. If the user asks for financial reports or summary audits, call 'get_dashboard_data', 'get_connection_data', 'get_customer_status_count', etc."
        )

        user_prompt = (
            f"User Goal: {intent}\n"
            f"Extracted Entities: {json.dumps(entities)}\n"
            f"Context: {json.dumps(context or {})}\n"
        )

        plan_json = await self.llm.generate_json(
            prompt=user_prompt,
            system=system_instruction,
            temperature=0.1
        )

        if "steps" in plan_json and isinstance(plan_json["steps"], list):
            return plan_json
        
        raise ValueError("Invalid plan structure generated by LLM")

    def _get_fallback_plan(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Returns a generic single tool call based on closest intent matching."""
        # Compare customers fallback
        if intent == "COMPARE_CUSTOMERS":
            names = entities.get("customer_names", [])
            steps = []
            for i, name in enumerate(names):
                steps.append({
                    "tool": "get_customer_profile",
                    "arguments": {"customer_id": f"$customer_id_{i}"},
                    "description": f"Fetch profile for customer {name}"
                })
                steps.append({
                    "tool": "show_subscription",
                    "arguments": {"customer_id": f"$customer_id_{i}"},
                    "description": f"Fetch subscription for customer {name}"
                })
            return {"steps": steps}
        
        # Default report mapping
        if intent == "REPORT":
            rep_type = (entities.get("report_type") or "package").lower()
            tool_name = "package_report"
            if rep_type == "wallet":
                tool_name = "wallet_report"
            elif rep_type == "tax":
                tool_name = "tax_report"
            elif rep_type == "addon":
                tool_name = "addon_report"
            elif rep_type == "subscription":
                tool_name = "subscription_report"
            elif rep_type == "collection":
                tool_name = "agent_collection_report"
            elif rep_type == "income":
                tool_name = "income_summary_report"
            elif rep_type == "expense":
                tool_name = "expense_summary_report"

            return {
                "steps": [
                    {
                        "tool": tool_name,
                        "arguments": {},
                        "description": f"Fetch {rep_type} report"
                    }
                ]
            }

        return {"steps": []}
