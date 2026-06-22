"""
Executor — routes planner output to the correct tool functions.

Maps intent → tool function, handles customer resolution,
and returns raw API data for the formatter.
"""

import logging

from agent.resolver import resolver
from tools import customer, payment, subscription, reports, complaints
from api.client import api_client

logger = logging.getLogger(__name__)


class Executor:
    """Executes plans by calling the appropriate tool functions."""

    async def execute(self, plan: dict, memory=None, billerq_token: str = "") -> dict:
        """Execute a plan and return raw results.

        Args:
            plan: Plan dict from the Planner (intent + entities).
            memory: ConversationMemory for the current session.
            billerq_token: Optional BillerQ token from the frontend user session.

        Returns:
            dict with keys:
                - "success": bool
                - "data": API response data (if success)
                - "error": Error message (if failed)
                - "customer_id": Resolved customer ID (if applicable)
                - "customer_name": Resolved customer name (if applicable)
        """
        intent = plan.get("intent", "UNKNOWN")
        entities = plan.get("entities", {})
        uses_context = plan.get("uses_context", False)

        # Set the per-request token override on the API client
        # This allows all downstream tool calls to use the frontend user's token
        api_client._request_token_override = billerq_token if billerq_token else None

        logger.info("Executing intent: %s", intent)

        try:
            # --- Customer resolution (for intents that need a customer) ---
            customer_id = None
            customer_name = None

            if intent in self._CUSTOMER_INTENTS:
                resolution = await self._resolve_customer_from_plan(
                    entities, uses_context, memory
                )
                if not resolution["found"]:
                    return {
                        "success": False,
                        "error": resolution.get("error", "Customer not found."),
                        "candidates": resolution.get("candidates"),
                    }
                customer_id = resolution["customer_id"]
                customer_name = resolution["customer_name"]

            # --- Route to the correct tool ---
            result = await self._route(intent, entities, customer_id)

            return {
                "success": True,
                "data": result,
                "intent": intent,
                "customer_id": customer_id,
                "customer_name": customer_name,
            }

        except Exception as e:
            logger.error("Execution failed for intent %s: %s", intent, str(e))
            return {
                "success": False,
                "error": f"Failed to process your request: {str(e)}",
            }

    # Intents that require customer resolution
    _CUSTOMER_INTENTS = {
        "CUSTOMER_SEARCH",
        "CUSTOMER_PROFILE",
        "PAYMENT_HISTORY",
        "SUBSCRIPTION",
        "STB_INFO",
    }

    async def _resolve_customer_from_plan(
        self, entities: dict, uses_context: bool, memory
    ) -> dict:
        """Resolve customer from entities or conversation context.

        Priority:
            1. Explicit customer_name in entities
            2. Mobile number in entities
            3. Context (uses_context=True and memory has a customer)
        """
        customer_name = entities.get("customer_name")
        mobile = entities.get("mobile")

        # Try explicit name
        if customer_name:
            return await resolver.resolve_customer(customer_name)

        # Try mobile number
        if mobile:
            return await resolver.resolve_customer(mobile)

        # Try context (follow-up question)
        if uses_context and memory:
            if memory.last_customer_id:
                logger.info(
                    "Using context customer: %s (ID %d)",
                    memory.last_customer_name, memory.last_customer_id,
                )
                return {
                    "found": True,
                    "customer_id": memory.last_customer_id,
                    "customer_name": memory.last_customer_name,
                    "customer_data": None,
                }

        return {
            "found": False,
            "error": "I need a customer name to help with that. Could you tell me which customer you're asking about?",
        }

    async def _route(self, intent: str, entities: dict, customer_id: int = None) -> dict:
        """Route an intent to the correct tool function.

        Args:
            intent: Classified intent string.
            entities: Extracted entities from the plan.
            customer_id: Resolved customer ID (if applicable).

        Returns:
            Raw API response data.
        """
        # ----- Customer Intents -----
        if intent == "CUSTOMER_SEARCH":
            if customer_id:
                return await customer.get_customer_profile(customer_id)
            query = entities.get("customer_name") or entities.get("mobile", "")
            return await customer.search_customer(query)

        if intent == "CUSTOMER_PROFILE":
            return await customer.get_customer_profile(customer_id)

        # ----- Payment Intents -----
        if intent == "PAYMENT_HISTORY":
            return await payment.get_payment_history(customer_id)

        if intent == "RECENT_PAYMENTS":
            return await payment.get_recent_payments()

        if intent == "UNPAID_CUSTOMERS":
            return await payment.get_unpaid_customers()

        if intent == "OVERDUE":
            return await payment.get_overdues()

        # ----- Subscription Intents -----
        if intent == "SUBSCRIPTION":
            return await subscription.get_subscription(customer_id)

        if intent == "EXPIRING_SUBSCRIPTIONS":
            return await subscription.get_pending_subscriptions()

        # ----- Compare -----
        if intent == "COMPARE_CUSTOMERS":
            return await self._handle_compare(entities)

        # ----- Area -----
        if intent == "AREA_CUSTOMERS":
            area = entities.get("area_name", "")
            if area:
                return await customer.get_customers_by_area(area)
            return await customer.get_all_customers()

        # ----- Analytics -----
        if intent == "ACTIVE_CUSTOMERS":
            return await customer.get_customer_status_count()

        if intent == "ANALYTICS":
            # Get dashboard + connection data for a comprehensive view
            dashboard = await reports.get_dashboard_data()
            connection = await reports.get_connection_data()
            status_count = await customer.get_customer_status_count()
            return {
                "dashboard": dashboard,
                "connections": connection,
                "customer_status": status_count,
            }

        # ----- Reports -----
        if intent == "REPORT":
            return await self._handle_report(entities)

        # ----- Complaints -----
        if intent == "COMPLAINTS":
            complaints_data = await complaints.get_complaints()
            status_count = await complaints.get_complaint_status_count()
            
            # Clean up/minimize complaints_data to prevent payload truncation
            if isinstance(complaints_data, dict) and "data" in complaints_data:
                inner_data = complaints_data["data"]
                if isinstance(inner_data, dict) and "data" in inner_data:
                    complaints_list = inner_data["data"]
                    if isinstance(complaints_list, list):
                        cleaned_list = []
                        for comp in complaints_list:
                            cleaned_comp = {
                                "id": comp.get("id"),
                                "complaint_no": comp.get("complaint_no"),
                                "customer_name": comp.get("customer_name"),
                                "problem_type": comp.get("problem_type"),
                                "status": comp.get("status"),
                                "area_name": comp.get("area_name"),
                                "subscriber_id": comp.get("subscriber_id"),
                                "phone": comp.get("phone"),
                                "assigned_user": comp.get("assigned_user"),
                                "formatted_created_at": comp.get("formatted_created_at"),
                                "updated_at": comp.get("updated_at"),
                            }
                            # Clean up the complaint forum comments
                            forum = comp.get("complaint_forum")
                            if isinstance(forum, list):
                                cleaned_forum = []
                                for f in forum:
                                    cleaned_forum.append({
                                        "comments": f.get("comments"),
                                        "status": f.get("status"),
                                        "updated_date": f.get("updated_date"),
                                        "updated_by": f.get("updated_by"),
                                    })
                                cleaned_comp["complaint_forum"] = cleaned_forum
                            cleaned_list.append(cleaned_comp)
                        inner_data["data"] = cleaned_list

            return {
                "complaints": complaints_data,
                "status_count": status_count,
            }

        # ----- STB Info -----
        if intent == "STB_INFO":
            return await customer.get_customer_stb(customer_id)

        # ----- Unknown -----
        return {
            "message": "I'm not sure how to help with that. "
            "You can ask me about customers, payments, subscriptions, "
            "complaints, or reports."
        }

    async def _handle_compare(self, entities: dict) -> dict:
        """Handle customer comparison by resolving and fetching multiple profiles."""
        names = entities.get("customer_names", [])
        if not names or len(names) < 2:
            return {"error": "I need at least two customer names to compare."}

        # Resolve all customers
        resolutions = await resolver.resolve_customers(names)

        results = {}
        for i, res in enumerate(resolutions):
            name = names[i]
            if res["found"]:
                profile = await customer.get_customer_profile(res["customer_id"])
                results[name] = {
                    "resolved": True,
                    "customer_id": res["customer_id"],
                    "profile": profile,
                }
            else:
                results[name] = {
                    "resolved": False,
                    "error": res.get("error", f"Could not find '{name}'"),
                }

        return {"comparison": results, "customer_names": names}

    async def _handle_report(self, entities: dict) -> dict:
        """Route to the specific report based on report_type entity."""
        report_type = (entities.get("report_type") or "package").lower()

        report_map = {
            "package": reports.get_package_report,
            "wallet": reports.get_wallet_report,
            "tax": reports.get_tax_report,
            "subscription": reports.get_subscription_report,
            "addon": reports.get_addon_report,
            "income": reports.get_income_summary,
            "expense": reports.get_expense_summary,
            "collection": reports.get_agent_collection_report,
        }

        handler = report_map.get(report_type)
        if handler:
            return await handler()

        # Default: package report
        return await reports.get_package_report()
