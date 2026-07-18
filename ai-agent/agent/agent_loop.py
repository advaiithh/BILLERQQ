import asyncio
import logging
import json
import re
import os
from datetime import datetime, timedelta

# Import BillerQ tools
from tools.customer import (
    search_customer,
    get_customer_profile,
    get_all_customers,
    get_single_customer,
    get_customers_by_area,
    get_customer_status_count,
    get_customer_list,
    get_archived_customers,
    get_customer_stb,
    get_wallets,
)
from tools.payment import (
    get_payment_history,
    get_recent_payments,
    get_unpaid_customers,
    get_payment_due_data,
    get_overdues,
    get_overdue_list,
    get_customer_payment_report,
    get_online_payments,
    get_payment_receipt,
    get_invoices,
    get_cancelled_invoices,
)
from tools.subscription import (
    get_subscription,
    get_single_subscription,
    get_subscription_history,
    get_pending_subscriptions,
    get_recurring_data,
    get_addon,
    get_addon_history,
    get_items,
    get_all_addons,
)
from tools.reports import (
    get_package_report,
    get_wallet_report,
    get_tax_report,
    get_addon_report,
    get_subscription_report,
    get_agent_collection_report,
    get_income_summary,
    get_expense_summary,
    get_dashboard_data,
    get_connection_data,
    get_packages,
    get_areas,
    get_stb_status_count,
    get_stbs,
)
from tools.complaints import (
    get_complaints,
    get_complaint_status_count,
    get_problem_types,
)
from tools.lead import (
    get_enquiries,
    get_enquiry_status_count,
    get_leads,
    get_lead_count,
    get_followups,
)
from tools.banking import (
    get_accounts,
    get_transactions,
)
from tools.expenses_income import (
    get_expenses,
    get_incomes,
    get_headers,
    get_vendors,
)
from tools.communication import (
    get_sms_logs,
    get_whatsapp_logs,
)
from tools.staff import (
    get_staff,
    get_roles,
)
from tools.settings import (
    get_message_settings,
    get_providers,
    get_categories,
    get_tax_classes,
)

logger = logging.getLogger("billerq-agent")

# Map of tool names to actual python functions
TOOL_MAP = {
    "search_customer": search_customer,
    "get_customer_profile": get_customer_profile,
    "get_all_customers": get_all_customers,
    "get_single_customer": get_single_customer,
    "get_customers_by_area": get_customers_by_area,
    "get_customer_status_count": get_customer_status_count,
    "get_customer_list": get_customer_list,
    "get_archived_customers": get_archived_customers,
    "get_customer_stb": get_customer_stb,
    "get_payment_history": get_payment_history,
    "get_recent_payments": get_recent_payments,
    "get_unpaid_customers": get_unpaid_customers,
    "get_payment_due_data": get_payment_due_data,
    "get_overdues": get_overdues,
    "get_overdue_list": get_overdue_list,
    "get_customer_payment_report": get_customer_payment_report,
    "get_online_payments": get_online_payments,
    "get_payment_receipt": get_payment_receipt,
    "get_invoices": get_invoices,
    "get_cancelled_invoices": get_cancelled_invoices,
    "get_subscription": get_subscription,
    "get_single_subscription": get_single_subscription,
    "get_subscription_history": get_subscription_history,
    "get_pending_subscriptions": get_pending_subscriptions,
    "get_package_report": get_package_report,
    "get_wallet_report": get_wallet_report,
    "get_tax_report": get_tax_report,
    "get_addon_report": get_addon_report,
    "get_subscription_report": get_subscription_report,
    "get_agent_collection_report": get_agent_collection_report,
    "get_income_summary": get_income_summary,
    "get_expense_summary": get_expense_summary,
    "get_dashboard_data": get_dashboard_data,
    "get_connection_data": get_connection_data,
    "get_complaints": get_complaints,
    "get_complaint_status_count": get_complaint_status_count,
    "get_problem_types": get_problem_types,
    "get_packages": get_packages,
    "get_areas": get_areas,
    "get_stb_status_count": get_stb_status_count,
    "get_stbs": get_stbs,
    "get_addon": get_addon,
    "get_all_addons": get_all_addons,
    "get_addon_history": get_addon_history,
    "get_enquiries": get_enquiries,
    "get_enquiry_status_count": get_enquiry_status_count,
    "get_leads": get_leads,
    "get_lead_count": get_lead_count,
    "get_followups": get_followups,
    "get_accounts": get_accounts,
    "get_transactions": get_transactions,
    "get_expenses": get_expenses,
    "get_incomes": get_incomes,
    "get_headers": get_headers,
    "get_vendors": get_vendors,
    "get_sms_logs": get_sms_logs,
    "get_whatsapp_logs": get_whatsapp_logs,
    "get_wallets": get_wallets,
    "get_items": get_items,
    "get_staff": get_staff,
    "get_roles": get_roles,
    "get_message_settings": get_message_settings,
    "get_providers": get_providers,
    "get_categories": get_categories,
    "get_tax_classes": get_tax_classes,
    "get_recurring_data": get_recurring_data,
}

ROUTER_SYSTEM_PROMPT_TEMPLATE = """You are the API Router for BillerQ AI Assistant.
Your task is to analyze the user's message and determine the single most appropriate BillerQ API tool to run.
You must also extract arguments for that tool and the customer name/identifier if specified.
"""

FORMATTER_SYSTEM_PROMPT_TEMPLATE = """You are the Response Formatter for BillerQ AI Assistant.
       - **Mobile:** [Mobile]
       - **Area:** [Area]
     • **Payment from [Customer Name]** (Sub ID: **[SubID]**)
       - **Invoice:** [InvNo]
       - **Amount:** **₹[Amt]**
       - **Method:** **[Method]**
       - **Date:** **[Date]**
     • **Complaint #[ID]** — **[Customer Name]**
       - **Status:** [OPEN/IN PROGRESS/RESOLVED]
       - **Problem Type:** [Problem Type]
       - **Date:** [Date]
     • **Recurring Profile for [Customer Name]** (Sub ID: **[SubID]**)
       - **Package:** [Package Name]
       - **Type:** [Type]
       - **Start Date:** [Date]
   - **Direct user to click below for remaining**: For the remaining records, write "For the remaining, click the link below." or similar text. Do not list any more.
2. If the user query is about a specific customer:
   - Display their profile details using next-next lines with nested sub-bullets:
     👤 **Customer Profile: [Customer Name]**
     - **Subscriber ID:** **[SubID]**
     - **Status:** [ACTIVE/INACTIVE]
     - **Mobile:** [Mobile]
     - **Area:** [Area]
     - **Address:** [Address]
     - **Joined:** [Date]
3. If the user query is about status counts or active items, or if status summary metrics are available:
   - First show the active items list in a highlighted way.
   - Under that, show a standard metrics summary block:
     📊 **Summary Metrics:**
     - **Active [Items]:** [Count] 🟢
     - **Total [Items]:** [Count]
     - **Inactive/Archived [Items]:** [Count] 🔴
4. Use markdown bolding (**value**) strategically to highlight key metrics, amounts, counts, customer names, status values, dates, and methods. Use clean bullet points (•), nested sub-bullets (-), and emojis (e.g., 📊, 💰, 💳, 👥, ⚠️, 📉) to structure sections and make them extremely easy to read. Avoid headers (like # or ##) or markdown code fences.
5. Use ₹ symbol for Indian Rupee currency values.
6. Keep the tone friendly, helpful, and professional. Do not reference raw IDs, API keys, or technical jargon.
7. If no tool was run or the result is an error, answer the user's query directly or explain the error helpfully in conversational language.
8. **Keep response extremely short**: To optimize processing speed, the response MUST be brief and direct. Avoid conversational filler, introductory pleasantries, or concluding remarks. Get straight to the numbers and requested data points.
"""


class BillerQAgent:
    """Agent running a structured pipeline using BedrockProvider (Claude Haiku)."""

    def __init__(self, llm):
        self.llm = llm

    async def run(self, message: str, context: dict = None, billerq_token: str = "", billerq_api_url: str = "", billerq_user_role: int | None = None) -> tuple[str, dict]:
        """Runs the agent pipeline to answer a user query using the hybrid rule-based and LLM architecture."""
        current_date = datetime.now().strftime("%d %B %Y")
        
        # 1. Resolve company_id and user_id dynamically from token and api_url
        company_id = "default_company"
        if billerq_api_url:
            from urllib.parse import urlparse
            try:
                parsed = urlparse(billerq_api_url)
                parts = parsed.netloc.split('.')
                if len(parts) > 1:
                    company_id = parts[0]
            except Exception:
                pass
        
        user_id = "default_user"
        if billerq_token and "|" in billerq_token:
            user_id = billerq_token.split("|")[0]

        from api.client import api_client
        original_base_url = api_client.base_url
        api_client._request_token_override = billerq_token if billerq_token else None
        api_client._request_user_role_override = billerq_user_role
        if billerq_api_url:
            api_client.base_url = billerq_api_url.rstrip("/")
            logger.info("Overriding API client base URL for run context with: %s", api_client.base_url)

        try:
            msg_lower = message.lower().strip()
            router_result = None

            # --- A. Try Rule Router (Disabled per user request) ---
            fast_result = None
            
            # --- B. Try Cache Lookup (Disabled per user request) ---
            cached_intent = None

            # --- C. Run Claude Planner if no routing match yet ---
            if not router_result:
                from agent.tool_registry import get_selected_tools
                selected_tools = get_selected_tools(message)
                
                # Format a highly compacted tools block
                tools_list_str = ""
                for idx, t in enumerate(selected_tools, 1):
                    tools_list_str += f"{idx}. `{t['name']}` - {t['description']} (Arguments: {t['args']})\n"
                
                # Construct tiny system prompt
                tiny_system_prompt = f"""You are the API Router for BillerQ AI Assistant.
Your task is to analyze the user's message and determine the single most appropriate BillerQ API tool to run.
You must also extract arguments for that tool and the customer name/identifier if specified.

Today's Date: {current_date}

BillerQ Platform Info:
- BillerQ is a Cable TV & Broadband billing and subscription management platform.
- The founders of BillerQ are Vipin VP (Founder) and Sageesh Thachukuzhiyil (Co-founder).

## Available Tools:
{tools_list_str}
If no tool is needed (e.g. general greeting, chit-chat, simple question about the company or founders that doesn't need database access), select "none".

## Rules for Response:
1. Output ONLY a valid JSON object. Do not include markdown code blocks, explanation, or other text outside of the JSON.
2. The JSON schema must be:
{{{{
  "tool": "tool_name_or_none",
  "arguments": {{{{}}}},
  "customer_name": "name_or_null"
}}}}
3. If the query concerns a specific customer, ALWAYS populate "customer_name" with their name, phone number, or subscriber ID."""
                
                router_messages = [{"role": "system", "content": tiny_system_prompt}]
                
                # Include limited history (last 2 turns)
                if context and context.get("history"):
                    for turn in context["history"][-2:]:
                        router_messages.append({"role": "user", "content": turn.get("user", "")})
                        router_messages.append({"role": "assistant", "content": turn.get("assistant", "")})
                        
                router_messages.append({"role": "user", "content": message})
                
                logger.info("Routing query via Bedrock: '%s'", message[:100])
                
                try:
                    router_raw = await self.llm.chat(router_messages, temperature=0.1, num_predict=100)
                    logger.info("Router LLM response: %s", router_raw)
                    router_result = self._parse_router_response(router_raw)
                    
                    # Log planner token usage
                    from agent.token_logger import log_llm_usage
                    usage = self.llm.get_and_reset_usage() if hasattr(self.llm, "get_and_reset_usage") else {}
                    log_llm_usage(
                        stage="planner",
                        company_id=company_id,
                        user_id=user_id,
                        input_tokens=usage.get("input_tokens"),
                        output_tokens=usage.get("output_tokens")
                    )
                except Exception as e:
                    logger.exception("Router Bedrock call failed")
                    err_msg = str(e).lower()
                    if "throttle" in err_msg or "rate limit" in err_msg or "too many tokens" in err_msg:
                        raise RuntimeError("AWS Bedrock rate limit exceeded (ThrottlingException): Too many tokens per day. Please check your AWS Bedrock quota limits.") from e
                    if any(w in err_msg for w in ["signature", "credential", "aws", "bedrock", "invalid", "accesskey"]):
                        raise RuntimeError("AWS Bedrock connection failed. Please verify that your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION in the .env file are correct and active.") from e
                    router_result = {"tool": "none", "arguments": {}, "customer_name": None}

                # Cache the parsed intent result (only if it doesn't target a specific customer name for tenant security)
                if router_result.get("tool") and not router_result.get("customer_name"):
                    billerq_cache.set(company_id, "intent", message, router_result, ttl_seconds=3600)

            # --- D. Execute Mapped Tool ---
            tool_name = router_result.get("tool", "none")
            tool_args = router_result.get("arguments", {})
            customer_name_query = router_result.get("customer_name")
            
            # Blacklist check
            blacklist_words = ["customer", "agent", "user", "complaint", "list", "show", "get", "view", "total", "count"]
            if customer_name_query:
                q_words = str(customer_name_query).lower().split()
                if q_words and all(w in blacklist_words for w in q_words):
                    customer_name_query = None

            # Local argument adjustments
            if tool_name == "get_invoices":
                if "pending" in msg_lower or "unpaid" in msg_lower:
                    tool_args["payment_status"] = "pending"
                elif "paid" in msg_lower:
                    tool_args["payment_status"] = "paid"
            elif tool_name in ("get_all_customers", "search_customer", "get_customer_list"):
                if "inactive" in msg_lower:
                    tool_args["status"] = "inactive"
                elif "active" in msg_lower:
                    tool_args["status"] = "active"

            # Resolve Customer details if needed
            resolved_cust_id = None
            resolved_cust_name = None
            resolved_agent_id = None
            
            # If the tool requires a customer_id but we only have customer_name_query
            requires_customer = tool_name in ("get_customer_profile", "get_payment_history", "get_subscription", "get_customer_stb", "get_invoices")
            
            if customer_name_query and (requires_customer or tool_name == "search_customer"):
                from agent.resolver import Resolver
                resolver = Resolver()
                try:
                    resolved = await resolver.resolve_customer(customer_name_query)
                    if resolved and resolved.get("found"):
                        resolved_cust_id = resolved.get("customer_id")
                        resolved_cust_name = resolved.get("customer_name")
                        logger.info("Resolved customer name '%s' to ID: %s", customer_name_query, resolved_cust_id)
                        if requires_customer:
                            tool_args["customer_id"] = resolved_cust_id
                    elif resolved and not resolved.get("found") and resolved.get("error"):
                        logger.warning("Customer resolution failed: %s", resolved.get("error"))
                except Exception:
                    logger.exception("Error resolving customer ID")

            # Fallback to last customer in context memory if available and needed
            if not resolved_cust_id and requires_customer and context and context.get("last_customer_id"):
                resolved_cust_id = context.get("last_customer_id")
                resolved_cust_name = context.get("last_customer_name")
                tool_args["customer_id"] = resolved_cust_id
                logger.info("Used fallback customer from session memory: %s (ID: %s)", resolved_cust_name, resolved_cust_id)

            # Resolve agent user_id for agent reports
            if tool_name == "get_agent_collection_report" and customer_name_query:
                try:
                    staff_resp = await self._execute_tool("get_staff", {}, billerq_token, billerq_api_url, billerq_user_role)
                    staff_list = staff_resp.get("data", []) if isinstance(staff_resp, dict) else []
                    if isinstance(staff_list, dict):
                        staff_list = staff_list.get("data", [])
                    
                    matched_user = None
                    for staff in staff_list:
                        n1 = re.sub(r"[^a-zA-Z0-9]", "", customer_name_query.lower())
                        n2 = re.sub(r"[^a-zA-Z0-9]", "", str(staff.get("name", "")).lower())
                        if n1 and n2 and (n1 in n2 or n2 in n1):
                            matched_user = staff
                            break
                    if matched_user:
                        resolved_agent_id = matched_user.get("user_id") or matched_user.get("id")
                        tool_args["agent_id"] = resolved_agent_id
                        logger.info("Resolved agent name to ID: %s (ID: %s)", customer_name_query, resolved_agent_id)
                except Exception:
                    logger.exception("Error resolving agent user_id")

            # Retrieve API response (checking cache first)
            tool_result = None
            if tool_name != "none":
                if requires_customer and not tool_args.get("customer_id"):
                    # Build detailed error message if resolution failed
                    error_msg = f"Could not find or resolve a customer named '{customer_name_query or 'unknown'}'. Please try again with their exact name or subscriber ID."
                    if 'resolved' in locals() and resolved and not resolved.get("found") and resolved.get("error"):
                        error_msg = resolved.get("error")
                    tool_result = {"error": error_msg}
                else:
                    api_cache_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
                    cached_api_result = billerq_cache.get(company_id, "api", api_cache_key)
                    
                    if cached_api_result:
                        logger.info("API result cache hit for tool: %s", tool_name)
                        tool_result = cached_api_result
                    else:
                        tool_result = await self._execute_tool(tool_name, tool_args, billerq_token, billerq_api_url, billerq_user_role)
                        # Cache the result with tool-specific TTL
                        ttl = 300 # default 5 minutes
                        if "dashboard" in tool_name or "status_count" in tool_name or "connection_data" in tool_name:
                            ttl = 60 # 1 minute
                        elif "report" in tool_name:
                            ttl = 120 # 2 minutes
                        billerq_cache.set(company_id, "api", api_cache_key, tool_result, ttl_seconds=ttl)

            # --- E. Format Response ---
            rule_based_response = None
            if tool_name != "none":
                from agent.templates import build_template_response
                rule_based_response = await build_template_response(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_result=tool_result,
                    message=message,
                    resolved_cust_name=resolved_cust_name or customer_name_query,
                    resolved_cust_id=resolved_cust_id,
                    resolved_agent_id=resolved_agent_id,
                    billerq_token=billerq_token,
                    billerq_api_url=billerq_api_url,
                    billerq_user_role=billerq_user_role,
                    agent=self
                )

            # Fallback to Bedrock Formatter only for complex analysis
            final_text = ""
            if False:  # Disabled template formatting per user request to let Claude always format dynamically
                logger.info("Bypassing Formatter LLM — using template response directly.")
                final_text = rule_based_response
            else:
                if tool_name == "none":
                    formatter_system_prompt = "You are BillerQ AI, a helpful, polite customer support agent. Answer the user's question directly."
                    formatter_messages = [
                        {"role": "system", "content": formatter_system_prompt},
                        {"role": "user", "content": message}
                    ]
                else:
                    from agent.reducer import compact_api_result
                    pruned_data = compact_api_result(tool_name, tool_result)
                    
                    formatter_system_prompt = f"You are the Response Formatter for BillerQ AI Assistant. Today's Date: {current_date}. Answer user's question in friendly markdown."
                    formatter_user_prompt = f"User Question: {message}\nTool run: {tool_name}\nData:\n{json.dumps(pruned_data, indent=2)}"
                    formatter_messages = [
                        {"role": "system", "content": formatter_system_prompt},
                        {"role": "user", "content": formatter_user_prompt}
                    ]
                
                try:
                    logger.info("Formatting response via Bedrock...")
                    final_text = await self.llm.chat(formatter_messages, temperature=0.3, num_predict=400)
                    final_text = final_text.strip()
                    
                    # Log formatter token usage
                    from agent.token_logger import log_llm_usage
                    usage = self.llm.get_and_reset_usage() if hasattr(self.llm, "get_and_reset_usage") else {}
                    log_llm_usage(
                        stage="formatter",
                        company_id=company_id,
                        user_id=user_id,
                        input_tokens=usage.get("input_tokens"),
                        output_tokens=usage.get("output_tokens")
                    )
                except Exception as e:
                    logger.exception("Formatter Bedrock call failed")
                    err_msg = str(e).lower()
                    if "throttle" in err_msg or "rate limit" in err_msg or "too many tokens" in err_msg:
                        raise RuntimeError("AWS Bedrock rate limit exceeded (ThrottlingException): Too many tokens per day. Please check your AWS Bedrock quota limits.") from e
                    if any(w in err_msg for w in ["signature", "credential", "aws", "bedrock", "invalid", "accesskey"]):
                        raise RuntimeError("AWS Bedrock connection failed. Please verify that your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION in the .env file are correct and active.") from e
                    final_text = await self._get_fallback_dashboard_response(billerq_token, billerq_api_url, billerq_user_role)

            # Ensure that redirect button metadata matches the tool executed
            metadata = self._get_redirect_metadata(tool_name, resolved_cust_id, resolved_cust_name or customer_name_query, message, resolved_agent_id=resolved_agent_id)
            
            # Fetch and attach LLM token usage info to metadata
            if hasattr(self.llm, "get_and_reset_usage"):
                usage_info = self.llm.get_and_reset_usage()
                metadata["token_usage"] = usage_info
            
            return final_text, metadata
        finally:
            api_client._request_token_override = None
            api_client._request_user_role_override = None
            api_client.base_url = original_base_url
    def _parse_router_response(self, response_str: str) -> dict:
        """Parse router LLM response looking for JSON object or keywords."""
        response_str = response_str.strip()
        
        # Try direct JSON parsing first
        json_match = re.search(r"({.*})", response_str, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1).strip())
                if isinstance(parsed, dict):
                    return {
                        "tool": parsed.get("tool", "none"),
                        "arguments": parsed.get("arguments", {}),
                        "customer_name": parsed.get("customer_name")
                    }
            except Exception:
                pass
                
        # Keyword extraction fallback
        for tool_name in TOOL_MAP.keys():
            if tool_name in response_str:
                cust_name = None
                cust_match = re.search(r'customer_name["\s:]+["\']?([^"\'\n}]+)', response_str)
                if cust_match:
                    cust_name = cust_match.group(1).strip()
                return {
                    "tool": tool_name,
                    "arguments": {},
                    "customer_name": cust_name
                }
                
        return {"tool": "none", "arguments": {}, "customer_name": None}

    def _get_redirect_metadata(self, tool_name: str, resolved_cust_id: int = None, resolved_cust_name: str = None, message_str: str = "", resolved_agent_id: int = None) -> dict:
        """Constructs redirection metadata for the frontend."""
        metadata = {}
        if resolved_cust_id:
            metadata["customer_id"] = resolved_cust_id
        if resolved_cust_name:
            metadata["customer_name"] = resolved_cust_name

        # Query-based overrides for general tools (like get_dashboard_data / get_connection_data)
        msg_lower = (message_str or "").lower()
        if "wallet" in msg_lower:
            metadata["redirect_url"] = "/report/wallet-balance"
            metadata["redirect_label"] = "View wallet balance"
            return metadata
        elif "due" in msg_lower or "outstanding" in msg_lower:
            metadata["redirect_url"] = "/report/payment-due"
            metadata["redirect_label"] = "View payment due"
            return metadata
        elif "collection" in msg_lower or "collected" in msg_lower:
            metadata["redirect_url"] = "/report/payment-collection"
            metadata["redirect_label"] = "View collections"
            return metadata

        if not tool_name or tool_name == "none":
            metadata["redirect_url"] = "/dashboard/default"
            metadata["redirect_label"] = "View Dashboard"
            return metadata

        tool_map = {
            "get_customer_status_count": ("/customers/customer", "View customers"),
            "get_all_customers": ("/customers/customer", "View customers"),
            "get_customers_by_area": ("/customers/customer", "View customers"),
            "search_customer": ("/customers/customer", "View customers"),
            "get_unpaid_customers": ("/report/unpaid-customer", "View unpaid customers"),
            "get_overdue_list": ("/report/payment-due", "View overdue payments"),
            "get_overdues": ("/report/payment-due", "View overdue payments"),
            "get_payment_due_data": ("/report/payment-due", "View overdue payments"),
            "get_recent_payments": ("/report/customer-payment", "View payments"),
            "get_package_report": ("/report/package-summary", "View report"),
            "get_wallet_report": ("/report/wallet-balance", "View report"),
            "get_tax_report": ("/report/tax-report", "View report"),
            "get_subscription_report": ("/report/subscription-summary", "View report"),
            "get_addon_report": ("/report/addon-summary", "View report"),
            "get_agent_collection_report": ("/report/payment-collection", "View report"),
            "get_income_summary": ("/report/income-summary", "View report"),
            "get_expense_summary": ("/report/expense-summary", "View report"),
            "get_dashboard_data": ("/dashboard/default", "Open analytics"),
            "get_connection_data": ("/dashboard/default", "Open analytics"),
            "get_complaints": ("/complaints", "View complaints"),
            "get_complaint_status_count": ("/complaints", "View complaints"),
            "get_invoices": ("/billing/invoice", "View invoices"),
            "get_cancelled_invoices": ("/billing/invoice", "View invoices"),
            "get_archived_customers": ("/customers/customer", "View customers"),
            "get_pending_subscriptions": ("/customers/customer", "View customers"),
            "get_online_payments": ("/report/online-payment", "View online payments"),
            "get_customer_payment_report": ("/report/customer-payment", "View payments"),
            "get_problem_types": ("/complaints", "View complaints"),
            "get_packages": ("/dashboard/default", "Open analytics"),
            "get_areas": ("/customers/customer", "View customers"),
            "get_stb_status_count": ("/dashboard/default", "Open analytics"),
            "get_stbs": ("/dashboard/default", "Open analytics"),
            "get_enquiries": ("/lead-manage/enquiry", "View enquiries"),
            "get_leads": ("/lead-manage/lead", "View leads"),
            "get_followups": ("/lead-manage/follow-up", "View follow-ups"),
            "get_accounts": ("/banking/account", "View bank accounts"),
            "get_transactions": ("/banking/transaction", "View banking transactions"),
            "get_expenses": ("/expenses-income/expense", "View expenses"),
            "get_incomes": ("/expenses-income/income", "View incomes"),
            "get_headers": ("/expenses-income/header", "View headers"),
            "get_vendors": ("/expenses-income/vendor", "View vendors"),
            "get_sms_logs": ("/report/sms-message-logs", "View SMS logs"),
            "get_whatsapp_logs": ("/report/whatsApp-message-logs", "View WhatsApp logs"),
            "get_items": ("/Services/item", "View items"),
            "get_both_subscription_addon": ("/billing/invoice", "View invoices"),
            "get_staff": ("/staff/staff", "View staff"),
            "get_roles": ("/staff/role", "View roles"),
            "get_message_settings": ("/settings/message-credit", "View credits"),
            "get_providers": ("/settings/cas-isp-provider", "View providers"),
            "get_categories": ("/settings/categories", "View categories"),
            "get_tax_classes": ("/settings/tax-class", "View tax classes"),
            "get_wallets": ("/customers/wallet", "View wallets"),
            "get_recurring_data": ("/billing/recurring", "View recurring"),
            "show_guide": (
                ("/customers/customer", "Open Customers") if resolved_cust_name == "customer" else
                ("/complaints", "Open Complaints") if resolved_cust_name == "complaint" else
                ("/billing/invoice", "Open Invoices") if resolved_cust_name == "invoice" else
                ("/billing/subscription", "Open Subscriptions") if resolved_cust_name == "subscription" else
                ("/report/unpaid-customer", "Open Reports") if resolved_cust_name == "report" else
                ("/dashboard/default", "Open Dashboard")
            )
        }

        # Dynamic overrides
        if tool_name == "get_connection_data":
            # If it's a collection query (either overall collections or agent collections), redirect to collection report
            if resolved_cust_name or resolved_cust_id or any(k in message_str.lower() for k in ["agent", "collection", "due"]):
                tool_map["get_connection_data"] = ("/report/payment-collection", "View report")
        elif tool_name == "get_agent_collection_report":
            base_url = "/report/payment-collection"
            params = []
            msg_lower = message_str.lower()
            start_date, end_date = None, None
            if "last year" in msg_lower or "2025" in msg_lower:
                start_date = "01-01-2025"
                end_date = "31-12-2025"
            elif "this year" in msg_lower or "2026" in msg_lower:
                start_date = "01-01-2026"
                end_date = "31-12-2026"
            elif "2024" in msg_lower:
                start_date = "01-01-2024"
                end_date = "31-12-2024"
                
            if start_date and end_date:
                params.append(f"start_date={start_date}")
                params.append(f"end_date={end_date}")
                
            if resolved_agent_id:
                params.append(f"user={resolved_agent_id}")
                
            if params:
                redirect_url = f"{base_url}?{'&'.join(params)}"
            else:
                redirect_url = base_url
                
            tool_map["get_agent_collection_report"] = (redirect_url, "View report")

        url_label = tool_map.get(tool_name)
        if url_label:
            metadata["redirect_url"] = url_label[0]
            metadata["redirect_label"] = url_label[1]

        return metadata

    def _format_curr(self, val):
        try:
            if isinstance(val, (int, float)):
                return f"{val:,.2f}"
            cleaned = str(val).replace(",", "").strip()
            return f"{float(cleaned):,.2f}"
        except Exception:
            return str(val)

    async def _get_customer_dashboard_response(self, billerq_token, billerq_api_url, billerq_user_role, status_filter=None):
        try:
            counts_resp = await self._execute_tool("get_customer_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
            counts_data = counts_resp.get("data") if isinstance(counts_resp, dict) else []
        except Exception:
            counts_data = []
            
        active_count = 0
        inactive_count = 0
        total_count = 0
        if isinstance(counts_data, list):
            active_count = next((c.get("count") for c in counts_data if c.get("status") == "Active"), 0)
            inactive_count = next((c.get("count") for c in counts_data if c.get("status") == "Inactive"), 0)
            total_count = next((c.get("count") for c in counts_data if c.get("status") == "Total"), 0)

        try:
            archived_resp = await self._execute_tool("get_archived_customers", {}, billerq_token, billerq_api_url, billerq_user_role)
            archived_raw = archived_resp.get("data", []) if isinstance(archived_resp, dict) else []
            if isinstance(archived_raw, dict):
                archived_data = archived_raw.get("data", [])
                archived_count = archived_raw.get("total", len(archived_data))
            elif isinstance(archived_raw, list):
                archived_data = archived_raw
                archived_count = len(archived_raw)
            else:
                archived_data = []
                archived_count = 0
        except Exception:
            archived_data = []
            archived_count = 0

        target_status = status_filter if status_filter else "active"
        lines = []

        if target_status == "archived":
            lines.append("⚠️ **ARCHIVED CUSTOMERS** (Top 5)\n")
            if not archived_data:
                lines.append("- No archived customers found.")
            else:
                for c in archived_data[:5]:
                    cname = c.get("name") or c.get("customer_name") or "Unknown"
                    sub_id = c.get("subscriber_id") or "N/A"
                    mobile = c.get("mobile") or "N/A"
                    jdate = c.get("join_date") or "N/A"
                    lines.append(
                        f"👤 **{cname.strip()}** (ID: `{sub_id}`)\n"
                        f"• **Status:** ARCHIVED ⚠️\n"
                        f"• **Mobile:** {mobile}\n"
                        f"• **Joined:** {jdate}\n"
                    )
            list_total = archived_count
        else:
            try:
                cust_resp = await self._execute_tool("get_all_customers", {"status": target_status}, billerq_token, billerq_api_url, billerq_user_role)
                cust_data = cust_resp.get("data", {}) if isinstance(cust_resp, dict) else {}
                customers = cust_data.get("data", []) if isinstance(cust_data, dict) else []
            except Exception:
                customers = []

            status_label = target_status.upper()
            emoji = "🟢" if status_label == "ACTIVE" else "🔴" if status_label == "INACTIVE" else "⚠️"
            lines.append(f"{emoji} **{status_label} CUSTOMERS** (Top 5)\n")
            
            if not customers:
                lines.append(f"- No {target_status} customers found.")
            else:
                for c in customers[:5]:
                    cname = c.get("name") or c.get("customer_name") or "Unknown"
                    sub_id = c.get("subscriber_id") or "N/A"
                    status = (c.get("status") or target_status).upper()
                    mobile = c.get("mobile") or "N/A"
                    area = c.get("area_name") or c.get("area") or "N/A"
                    status_emoji = "🟢" if status == "ACTIVE" else "🔴" if status in ("INACTIVE", "BLOCKED") else "⚠️"
                    lines.append(
                        f"👤 **{cname.strip()}** (ID: `{sub_id}`)\n"
                        f"• **Status:** {status} {status_emoji}\n"
                        f"• **Mobile:** {mobile}\n"
                        f"• **Area:** {area}\n"
                    )
            
            list_total = len(customers)
            if target_status == "active" and active_count > 0:
                list_total = active_count
            elif target_status == "inactive" and inactive_count > 0:
                list_total = inactive_count

        if list_total > 5:
            remaining = list_total - 5
            lines.append(f"---\n💡 *For the remaining {remaining:,} customers, click the redirection button below.*")

        lines.append("\n---")
        lines.append("\n📊 **Customer Metrics Summary:**")
        lines.append(f"- **Active Customers:** {active_count} 🟢")
        lines.append(f"- **Total Customers:** {total_count}")
        lines.append(f"- **Inactive Customers:** {inactive_count} 🔴")
        lines.append(f"- **Archived Customers:** {archived_count} ⚠️")

        return "\n".join(lines)

    async def _get_complaints_dashboard_response(self, billerq_token, billerq_api_url, billerq_user_role, status_filter=None, customer_name_filter=None, problem_type_filter=None, area_filter=None):
        try:
            counts_resp = await self._execute_tool("get_complaint_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
            counts_data = counts_resp.get("data") if isinstance(counts_resp, dict) else []
        except Exception:
            counts_data = []
        
        open_count = 0
        in_progress_count = 0
        closed_count = 0
        total_count = 0
        if isinstance(counts_data, list):
            for item in counts_data:
                st = str(item.get("status", "")).lower()
                cnt = item.get("count", 0)
                if st == "open":
                    open_count = cnt
                elif "progress" in st:
                    in_progress_count = cnt
                elif st in ("closed", "resolved"):
                    closed_count = cnt
                elif st == "total":
                    total_count = cnt
        
        if total_count == 0:
            total_count = open_count + in_progress_count + closed_count

        try:
            complaints_resp = await self._execute_tool("get_complaints", {}, billerq_token, billerq_api_url, billerq_user_role)
            complaints_wrapper = complaints_resp.get("data", {}) if isinstance(complaints_resp, dict) else {}
            items = []
            if isinstance(complaints_wrapper, dict):
                items = complaints_wrapper.get("data", [])
            elif isinstance(complaints_wrapper, list):
                items = complaints_wrapper
        except Exception:
            items = []

        # Local pre-filtering by customer, problem type, area
        if customer_name_filter:
            cust_lower = str(customer_name_filter).lower().strip()
            cust_norm = re.sub(r'\s+', '', cust_lower)
            is_digit = cust_lower.isdigit()
            filtered = []
            for item in items:
                cname_val = str(item.get("customer_name") or item.get("name") or "").lower()
                sub_val = str(item.get("subscriber_id") or "").lower()
                phone_val = str(item.get("phone") or "").lower()
                cname_norm = re.sub(r'\s+', '', cname_val)
                sub_norm = re.sub(r'\s+', '', sub_val)
                phone_norm = re.sub(r'\s+', '', phone_val)
                if cust_norm in cname_norm or cust_norm in sub_norm or cust_norm in phone_norm:
                    filtered.append(item)
                elif is_digit and cust_lower in str(item.get("id", "")):
                    filtered.append(item)
            items = filtered

        if problem_type_filter:
            prob_lower = str(problem_type_filter).lower().strip()
            items = [item for item in items if prob_lower in str(item.get("problem_type", "")).lower()]

        if area_filter:
            area_lower = str(area_filter).lower().strip()
            area_norm = re.sub(r'\s+', '', area_lower)
            items = [item for item in items if area_norm in re.sub(r'\s+', '', str(item.get("area_name", "")).lower())]

        # If filtered by customer/problem/area, recompute counts locally from this filtered subset
        if customer_name_filter or problem_type_filter or area_filter:
            open_count = sum(1 for item in items if str(item.get("status", "")).lower() == "open")
            in_progress_count = sum(1 for item in items if "progress" in str(item.get("status", "")).lower())
            closed_count = sum(1 for item in items if str(item.get("status", "")).lower() in ("closed", "resolved"))
            total_count = len(items)

        # Apply status filter
        if status_filter:
            status_lower = status_filter.lower().replace("-", " ").strip()
            if status_lower in ("closed", "resolved"):
                items = [item for item in items if str(item.get("status", "")).lower() in ("closed", "resolved")]
            elif "progress" in status_lower:
                items = [item for item in items if "progress" in str(item.get("status", "")).lower()]
            elif status_lower == "open":
                items = [item for item in items if str(item.get("status", "")).lower() == "open"]
            else:
                items = [item for item in items if status_lower in str(item.get("status", "")).lower()]

        target_status = status_filter.upper() if status_filter else "OPEN"
        lines = []
        emoji = "🟢" if target_status == "OPEN" else "🟠" if "PROGRESS" in target_status else "🔴"
        lines.append(f"{emoji} **{target_status} COMPLAINTS** (Top 5)\n")
        
        if not items:
            lines.append(f"- No {target_status.lower()} complaints found.")
        else:
            for item in items[:5]:
                cname = item.get("customer_name") or item.get("name") or "Unknown"
                comp_no = item.get("complaint_no") or item.get("id") or "N/A"
                prob = item.get("problem_type") or "N/A"
                status = (item.get("status") or "N/A").upper()
                date = item.get("created_at") or "N/A"
                status_emoji = "🔴" if status == "OPEN" else "🟠" if "PROGRESS" in status else "🟢"
                lines.append(
                    f"🛠️ **Complaint #{comp_no}** — **{cname.strip()}**\n"
                    f"• **Status:** {status} {status_emoji}\n"
                    f"• **Problem Type:** {prob}\n"
                    f"• **Date:** {date}\n"
                )

        list_total = len(items)
        if list_total > 5:
            remaining = list_total - 5
            lines.append(f"---\n💡 *For the remaining {remaining:,} complaints, click the redirection button below.*")

        lines.append("\n---")
        lines.append("\n📊 **Complaints Summary:**")
        lines.append(f"- **Open Complaints:** {open_count} 🟢")
        lines.append(f"- **In-Progress Complaints:** {in_progress_count} 🟠")
        lines.append(f"- **Closed Complaints:** {closed_count} 🔴")
        lines.append(f"- **Total Complaints:** {total_count}")

        return "\n".join(lines)

    async def _get_fallback_dashboard_response(self, billerq_token, billerq_api_url, billerq_user_role):
        try:
            db_resp = await self._execute_tool("get_dashboard_data", {}, billerq_token, billerq_api_url, billerq_user_role)
            data = db_resp.get("data", {}) if isinstance(db_resp, dict) else {}
        except Exception:
            data = {}

        comp = data.get("complaints", {}) if isinstance(data, dict) else {}
        subs = data.get("subscriptions", {}) if isinstance(data, dict) else {}
        pay = data.get("payment_collection", {}) if isinstance(data, dict) else {}
        cond = data.get("check_condition", {}) if isinstance(data, dict) else {}

        total_customers = cond.get('customers', 0)
        try:
            sc_resp = await self._execute_tool("get_customer_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
            sc_data = sc_resp.get("data", []) if isinstance(sc_resp, dict) else []
            for sc_item in sc_data:
                if sc_item.get("status") == "Total":
                    total_customers = sc_item.get("count", total_customers)
        except Exception:
            pass

        lines = [
            "I couldn't understand that query. Please try typing a clear prompt, such as:",
            "• *\"Show active customers\"*",
            "• *\"Show recent payments\"*",
            "• *\"Who has overdue payments?\"*",
            "• *\"Show all complaints\"*",
            "",
            "📊 **Dashboard Overview:**",
            f"- **Total Customers:** {total_customers:,}",
            f"- **Active STBs:** {cond.get('stb', 0):,} 🟢",
            f"- **Active Packages:** {cond.get('packages', 0):,}",
            "",
            "💰 **Payments & Collection:**",
            f"- **Collected Today:** ₹{pay.get('today', '0.00')}",
            f"- **Collected This Month:** ₹{pay.get('this_month', '0.00')}",
            f"- **Outstanding Dues:** ₹{pay.get('dues', '0.00')} 🔴",
            f"- **Wallet Amount:** ₹{pay.get('wallet_amount', '0.00')}",
            "",
            "📦 **Subscriptions Summary:**",
            f"- **Total Active Subscriptions:** {subs.get('totalSubscriptions', 0)} 🟢",
            f"- **Expired Subscriptions:** {subs.get('expired', 0)} 🔴",
            f"- **Expiring Today:** {subs.get('today', 0)} ⚠️",
            "",
            "🛠️ **Complaints Status:**",
            f"- **Unresolved Complaints:** {comp.get('un_resolved', 0)} 🔴",
            f"- **In Process:** {comp.get('in_process', 0)} 🟠",
            f"- **Resolved:** {comp.get('resolved', 0)} 🟢"
        ]
        return "\n".join(lines)

    def _get_guide_response(self, category: str) -> str:
        """Returns step-by-step instructions for BillerQ core modules."""
        guides = {
            "customer": (
                "👤 **Guide: How to Add a Customer**\n\n"
                "**Step 1: Go to Customers**\n"
                "  - Click **Customers** in the left sidebar, then select **Customer** from the submenu.\n"
                "**Step 2: Click 'Add'**\n"
                "  - Click the **Add** button at the top-right corner of the customer list page.\n"
                "**Step 3: Fill in Details**\n"
                "  - Enter the required fields: **First Name**, **Last Name**, **Mobile Number**, and **Area**.\n"
                "**Step 4: Set Subscriber ID**\n"
                "  - The system will auto-generate a Subscriber ID, or you can key in a custom one (e.g., CUST-01).\n"
                "**Step 5: Choose a Package**\n"
                "  - Select the subscriber's base subscription plan from the **Package** dropdown.\n"
                "**Step 6: Save**\n"
                "  - Click **Save** or **Submit**. The subscriber is registered and will show up in the customer list immediately."
            ),
            "payment": (
                "💳 **Guide: How to Record a Payment**\n\n"
                "**Step 1: Locate the Customer**\n"
                "  - Open **Customers → Customer** and search for them by name, phone, or subscriber ID.\n"
                "**Step 2: Open Profile**\n"
                "  - Click on their **Subscriber ID** link to open their details page.\n"
                "**Step 3: Go to Billing Tab**\n"
                "  - Click on the **Billing** or **Payments** tab within their profile.\n"
                "**Step 4: Click 'Collect Payment'**\n"
                "  - Click the **Collect Payment** button to launch the receipt form.\n"
                "**Step 5: Enter Details**\n"
                "  - Key in the **amount** and select the payment channel: **Cash, UPI, Card, or Bank Transfer**.\n"
                "**Step 6: Save & Send Receipt**\n"
                "  - Click **Confirm** or **Save**. The payment is recorded and you can send a receipt copy via SMS/WhatsApp."
            ),
            "invoice": (
                "🧾 **Guide: How to Create an Invoice**\n\n"
                "**Step 1: Open Billing**\n"
                "  - Click **Billing** in the left sidebar.\n"
                "**Step 2: Click 'New Invoice'**\n"
                "  - Click the **Add Invoice** or **+ New** button at the top right.\n"
                "**Step 3: Select Subscriber**\n"
                "  - Search and select the **customer** you wish to bill.\n"
                "**Step 4: Add Line Items**\n"
                "  - Add the target **service/package** as a line item. Adjust the quantity and rate.\n"
                "**Step 5: Set Due Date**\n"
                "  - Choose the payment **due date** and write any terms or descriptions.\n"
                "**Step 6: Save & Send**\n"
                "  - Click **Save** to store, or **Send** to deliver it directly via email/WhatsApp."
            ),
            "subscription": (
                "📦 **Guide: How to Manage Subscriptions**\n\n"
                "**Step 1: Open Customer Profile**\n"
                "  - Go to **Customers → Customer** and click on their **Subscriber ID**.\n"
                "**Step 2: Go to Subscriptions Tab**\n"
                "  - Click the **STB/Modem** or **Subscription** tab inside the profile.\n"
                "**Step 3: Activate a Plan**\n"
                "  - Click **Add Subscription**, select the package, set the **start date**, and click Save.\n"
                "**Step 4: Renew a Subscription**\n"
                "  - Locate the expiring subscription and click **Renew**. Select duration and confirm.\n"
                "**Step 5: Cancel/Deactivate**\n"
                "  - Click the **Deactivate** or **Cancel** button next to their subscription."
            ),
            "complaint": (
                "🛠️ **Guide: How to Log and Track Complaints**\n\n"
                "**Step 1: Go to Complaints**\n"
                "  - Click **Complaints** in the left sidebar.\n"
                "**Step 2: Add New Ticket**\n"
                "  - Click **+ Add** or **New Complaint**.\n"
                "**Step 3: Select Subscriber**\n"
                "  - Search and select the target **customer** reporting the issue.\n"
                "**Step 4: Select Problem Type**\n"
                "  - Select the category (e.g., STB Issue, Broadband, Billing, Signal Not Found).\n"
                "**Step 5: Assign & Describe**\n"
                "  - Write a brief description and optionally assign it to a technician/staff member.\n"
                "**Step 6: Save**\n"
                "  - Click **Save**. The ticket status will initialize as OPEN. Track it in the complaints listing."
            ),
            "report": (
                "📊 **Guide: How to View and Export Reports**\n\n"
                "**Step 1: Go to Reports**\n"
                "  - Click **Reports** in the left sidebar.\n"
                "**Step 2: Choose Report**\n"
                "  - Select from: **Collection, Payment Due, Wallet, Package**, etc.\n"
                "**Step 3: Choose Dates & Filters**\n"
                "  - Set the date range and select options (e.g. Area, Agent, Package) to filter details.\n"
                "**Step 4: Export Data**\n"
                "  - Click the **Export** button to save the sheet as **Excel** or **PDF**."
            ),
            "chatbot": (
                "🤖 **Guide: How to Use the AI Chatbot**\n\n"
                "• **Voice Input:** Tap the 🎙️ mic button and speak. It detects silence, stops, and submits your query.\n"
                "• **Fast Queries:** Click the ☰ button on the input bar to list top reports.\n"
                "• **Pronoun Recall:** Ask \"Show me Jinto Joseph\", then ask \"what is his mobile?\" or \"show his bills\" — the AI remembers Jinto.\n"
                "• **Side-by-Side Comparisons:** Ask **\"Compare Joy P and Advaith\"** to generate a visual comparison table."
            ),
            "billerq": (
                "ℹ️ **About BillerQ**\n\n"
                "**BillerQ** is an all-in-one Cable TV, Broadband, and subscription management application designed to simplify billing, customer management, and agent collections.\n\n"
                "**Key Sections:**\n"
                "1. **Dashboard** — Live connection totals, collection meters, and complaint status.\n"
                "2. **Customers** — Register subscribers, manage profiles, and assign STBs.\n"
                "3. **Billing** — Generating invoices, recording payments, and tracking dues.\n"
                "4. **Services/Products** — Package plans, addons, and item inventories.\n"
                "5. **Complaints** — Creating tickets, assigning staff, and tracking status.\n"
                "6. **Reports** — Collection logs, wallet summaries, and tax reports.\n\n"
                "Feel free to ask me anything like *\"how do I add a customer\"* or *\"where are complaints\"*, and I will display the step-by-step tutorial!"
            )
        }
        return guides.get(category, guides["billerq"])

    async def _get_stb_dashboard_response(self, billerq_token, billerq_api_url, billerq_user_role, status_filter=None):
        try:
            counts_resp = await self._execute_tool("get_stb_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
            counts_data = counts_resp.get("data") if isinstance(counts_resp, dict) else []
        except Exception:
            counts_data = []

        active_count = 0
        inactive_count = 0
        suspended_count = 0
        total_count = 0
        if isinstance(counts_data, list):
            for item in counts_data:
                st = str(item.get("status", "")).lower()
                cnt = item.get("count", 0)
                if st == "active":
                    active_count = cnt
                elif st == "inactive":
                    inactive_count = cnt
                elif st == "suspended":
                    suspended_count = cnt
                elif st == "total":
                    total_count = cnt

        if total_count == 0:
            total_count = active_count + inactive_count + suspended_count

        try:
            stb_resp = await self._execute_tool("get_stbs", {}, billerq_token, billerq_api_url, billerq_user_role)
            stb_wrapper = stb_resp.get("data", {}) if isinstance(stb_resp, dict) else {}
            items = []
            if isinstance(stb_wrapper, dict):
                items = stb_wrapper.get("data", [])
            elif isinstance(stb_wrapper, list):
                items = stb_wrapper
        except Exception:
            items = []

        target_status = status_filter if status_filter else "active"
        target_items = [i for i in items if str(i.get("status", "")).lower() == target_status.lower()]
        if not target_items and not status_filter:
            target_items = items

        lines = []
        status_label = target_status.upper()
        emoji = "🟢" if status_label == "ACTIVE" else "🔴" if status_label == "INACTIVE" else "⚠️"
        lines.append(f"{emoji} **{status_label} STBs** (Top 5)")

        if not target_items:
            lines.append(f"- No {target_status} STBs found.")
        else:
            for item in target_items[:5]:
                cname = item.get("customer_name") or item.get("name") or "Unknown"
                stb_no = item.get("stb_no") or "N/A"
                card_no = item.get("card_no") or "N/A"
                brand = item.get("brand") or "N/A"
                status = item.get("status") or "N/A"
                lines.append(f"• **STB: {stb_no}** — **{cname}**\n  - **Status:** {status.upper()}\n  - **Card No:** {card_no}\n  - **Brand:** {brand}")

        list_total = len(target_items)
        if target_status == "active" and active_count > 0:
            list_total = active_count
        elif target_status == "inactive" and inactive_count > 0:
            list_total = inactive_count

        if list_total > 5:
            lines.append("\nFor the remaining, click the link below.")

        lines.append("\n---")
        lines.append("\n📊 **STB/Device Summary:**")
        lines.append(f"- **Active STBs:** {active_count} 🟢")
        lines.append(f"- **Inactive STBs:** {inactive_count} 🔴")
        lines.append(f"- **Suspended STBs:** {suspended_count} ⚠️")
        lines.append(f"- **Total STBs:** {total_count}")

        return "\n".join(lines)

    async def _get_enquiry_dashboard_response(self, billerq_token, billerq_api_url, billerq_user_role, status_filter=None):
        try:
            counts_resp = await self._execute_tool("get_enquiry_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
            counts_data = counts_resp.get("data") if isinstance(counts_resp, dict) else []
        except Exception:
            counts_data = []
        
        active_count = 0
        converted_count = 0
        lost_count = 0
        total_count = 0
        if isinstance(counts_data, list):
            for item in counts_data:
                st = str(item.get("status", "")).lower()
                cnt = item.get("count", 0)
                if st == "active":
                    active_count = cnt
                elif st == "converted":
                    converted_count = cnt
                elif st == "lost":
                    lost_count = cnt
                elif st == "total":
                    total_count = cnt

        if total_count == 0:
            total_count = active_count + converted_count + lost_count

        try:
            enq_resp = await self._execute_tool("get_enquiries", {}, billerq_token, billerq_api_url, billerq_user_role)
            enq_wrapper = enq_resp.get("data", {}) if isinstance(enq_resp, dict) else {}
            items = []
            if isinstance(enq_wrapper, dict):
                items = enq_wrapper.get("data", [])
            elif isinstance(enq_wrapper, list):
                items = enq_wrapper
        except Exception:
            items = []

        target_status = status_filter if status_filter else "active"
        target_items = [i for i in items if str(i.get("status", "")).lower() == target_status.lower()]
        if not target_items and not status_filter:
            target_items = items

        lines = []
        status_label = target_status.upper()
        emoji = "🟢" if status_label == "ACTIVE" else "🟠" if status_label == "CONVERTED" else "🔴"
        lines.append(f"{emoji} **{status_label} ENQUIRIES** (Top 5)")

        if not target_items:
            lines.append(f"- No {target_status} enquiries found.")
        else:
            for item in target_items[:5]:
                name = item.get("name") or "Unknown"
                sub = item.get("subject") or "N/A"
                status = item.get("status") or "N/A"
                mobile = item.get("mobile") or "N/A"
                lines.append(f"• **{name}**\n  - **Subject:** {sub}\n  - **Status:** {status.upper()}\n  - **Mobile:** {mobile}")

        list_total = len(target_items)
        if target_status == "active" and active_count > 0:
            list_total = active_count
        elif target_status == "converted" and converted_count > 0:
            list_total = converted_count
        elif target_status == "lost" and lost_count > 0:
            list_total = lost_count

        if list_total > 5:
            lines.append("\nFor the remaining, click the link below.")

        lines.append("\n---")
        lines.append("\n📊 **Enquiry Summary:**")
        lines.append(f"- **Active Enquiries:** {active_count} 🟢")
        lines.append(f"- **Converted Enquiries:** {converted_count} 🟠")
        lines.append(f"- **Lost Enquiries:** {lost_count} 🔴")
        lines.append(f"- **Total Enquiries:** {total_count}")

        return "\n".join(lines)

    async def _get_lead_dashboard_response(self, billerq_token, billerq_api_url, billerq_user_role, status_filter=None):
        try:
            counts_resp = await self._execute_tool("get_lead_count", {}, billerq_token, billerq_api_url, billerq_user_role)
            counts_data = counts_resp.get("data") if isinstance(counts_resp, dict) else {}
        except Exception:
            counts_data = {}
        
        active_count = 0
        converted_count = 0
        lost_count = 0
        total_count = 0
        if isinstance(counts_data, dict):
            active_count = counts_data.get("active", 0)
            converted_count = counts_data.get("converted", 0)
            lost_count = counts_data.get("lost", 0)
            total_count = counts_data.get("total", 0)

        if total_count == 0:
            total_count = active_count + converted_count + lost_count

        try:
            lead_resp = await self._execute_tool("get_leads", {}, billerq_token, billerq_api_url, billerq_user_role)
            lead_wrapper = lead_resp.get("data", {}) if isinstance(lead_resp, dict) else {}
            items = []
            if isinstance(lead_wrapper, dict):
                items = lead_wrapper.get("data", [])
            elif isinstance(lead_wrapper, list):
                items = lead_wrapper
        except Exception:
            items = []

        target_status = status_filter if status_filter else "active"
        target_items = [i for i in items if str(i.get("status", "")).lower() == target_status.lower()]
        if not target_items and not status_filter:
            target_items = items

        lines = []
        status_label = target_status.upper()
        emoji = "🟢" if status_label == "ACTIVE" else "🟠" if status_label == "CONVERTED" else "🔴"
        lines.append(f"{emoji} **{status_label} LEADS** (Top 5)")

        if not target_items:
            lines.append(f"- No {target_status} leads found.")
        else:
            for item in target_items[:5]:
                name = item.get("name") or "Unknown"
                status = item.get("status") or "N/A"
                mobile = item.get("mobile") or "N/A"
                lines.append(f"• **{name}**\n  - **Status:** {status.upper()}\n  - **Mobile:** {mobile}")

        list_total = len(target_items)
        if target_status == "active" and active_count > 0:
            list_total = active_count
        elif target_status == "converted" and converted_count > 0:
            list_total = converted_count
        elif target_status == "lost" and lost_count > 0:
            list_total = lost_count

        if list_total > 5:
            lines.append("\nFor the remaining, click the link below.")

        lines.append("\n---")
        lines.append("\n📊 **Leads Summary:**")
        lines.append(f"- **Active Leads:** {active_count} 🟢")
        lines.append(f"- **Converted Leads:** {converted_count} 🟠")
        lines.append(f"- **Lost Leads:** {lost_count} 🔴")
        lines.append(f"- **Total Leads:** {total_count}")

        return "\n".join(lines)

    async def _execute_tool(self, name: str, arguments: dict, billerq_token: str, billerq_api_url: str = "", billerq_user_role: int | None = None) -> dict:
        """Executes the given BillerQ tool function."""
        from api.client import api_client
        api_client._request_token_override = billerq_token if billerq_token else None
        api_client._request_user_role_override = billerq_user_role

        original_base_url = api_client.base_url
        if billerq_api_url:
            api_client.base_url = billerq_api_url.rstrip("/")
            logger.info("Overriding API client base URL with: %s", api_client.base_url)

        func = TOOL_MAP.get(name)
        if not func:
            from api.registry import API_REGISTRY
            if name in API_REGISTRY:
                logger.info("Tool '%s' not found in TOOL_MAP. Executing dynamically via API_REGISTRY.", name)
                try:
                    return await api_client.get(name, params=arguments)
                except Exception as e:
                    logger.exception("Dynamic GET request failed for key %s", name)
                    return {"error": f"Dynamic endpoint call failed: {str(e)}"}
            return {"error": f"Tool '{name}' is not supported."}

        try:
            # Cast common integer parameters
            casted_args = {}
            for k, v in arguments.items():
                if k in ("customer_id", "subscription_id", "payment_id", "page") and v is not None:
                    try:
                        casted_args[k] = int(v)
                    except (ValueError, TypeError):
                        casted_args[k] = v
                else:
                    casted_args[k] = v

            # Filter arguments to match function signature and prevent TypeErrors
            import inspect
            sig = inspect.signature(func)
            has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not has_kwargs:
                valid_args = {k: v for k, v in casted_args.items() if k in sig.parameters}
            else:
                valid_args = casted_args

            # Check and supply fallback values for missing required positional parameters
            for name_param, param in sig.parameters.items():
                if param.default == inspect.Parameter.empty and param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                    if name_param not in valid_args:
                        if name_param == "query":
                            valid_args["query"] = ""
                        elif name_param in ("customer_id", "subscription_id", "payment_id", "invoice_id"):
                            valid_args[name_param] = None
                        elif name_param == "area_name":
                            valid_args["area_name"] = ""
                        else:
                            valid_args[name_param] = ""

            # If search_customer has an empty query, redirect to get_all_customers
            if name == "search_customer" and (not valid_args.get("query")):
                logger.info("Empty search query. Redirecting search_customer to get_all_customers.")
                func = TOOL_MAP["get_all_customers"]
                sig = inspect.signature(func)
                valid_args = {"page": 1}
                name = "get_all_customers"

            logger.info("Calling function %s with arguments: %s (original: %s)", name, valid_args, casted_args)
            result = await func(**valid_args)
            return result
        except Exception as e:
            logger.exception("Error running tool function %s", name)

            demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
            if demo_mode:
                customer_id = casted_args.get("customer_id") or 5
                if name == "get_customer_profile":
                    return {
                        "id": customer_id,
                        "name": "Bob Wilson" if customer_id == 5 else "Joy P",
                        "status": "Active",
                        "mobile": "9876543210",
                        "area_name": "DEVARGATHA",
                        "subscriber_id": "SUB10045",
                        "outstanding_balance": 5000 if customer_id == 5 else 0,
                        "package_name": "Basic HD Pack",
                        "price": 450
                    }
                elif name == "get_payment_history":
                    return {
                        "customer_id": customer_id,
                        "payments": [
                            {"id": 101, "amount": 450, "payment_date": "2026-05-10", "payment_mode": "Online"},
                            {"id": 102, "amount": 450, "payment_date": "2026-04-10", "payment_mode": "Cash"},
                            {"id": 103, "amount": 450, "payment_date": "2026-03-10", "payment_mode": "Cash"}
                        ]
                    }
                elif name == "get_subscription":
                    return {
                        "customer_id": customer_id,
                        "subscription_id": 9901,
                        "package_name": "Basic HD Pack",
                        "status": "Active",
                        "start_date": "2026-01-01",
                        "end_date": "2026-12-31"
                    }
                elif name == "get_customer_stb":
                    return {
                        "customer_id": customer_id,
                        "stb_no": "STB7720911",
                        "card_no": "VC8810293",
                        "status": "Active",
                        "brand": "Skyworth"
                    }

            # Fallback to general demo data if in demo mode and tool corresponds to demo intent
            from agent.executor import _get_demo_data
            demo_intent_map = {
                "get_customer_status_count": "ACTIVE_CUSTOMERS",
                "get_recent_payments": "RECENT_PAYMENTS",
                "get_unpaid_customers": "UNPAID_CUSTOMERS",
                "get_overdues": "OVERDUE",
                "get_overdue_list": "OVERDUE",
                "get_complaints": "COMPLAINTS",
                "get_complaint_status_count": "COMPLAINTS",
                "get_dashboard_data": "ANALYTICS",
                "get_connection_data": "ANALYTICS",
            }

            intent = demo_intent_map.get(name)
            if demo_mode and intent:
                logger.info("Demo mode fallback active for tool %s: returning mock data", name)
                return _get_demo_data(intent)

            return {"error": str(e)}
        finally:
            api_client._request_token_override = None
            api_client._request_user_role_override = None
            api_client.base_url = original_base_url
