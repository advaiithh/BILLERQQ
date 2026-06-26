import logging
import json
import re
import os
from datetime import datetime

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
)
from tools.subscription import (
    get_subscription,
    get_single_subscription,
    get_subscription_history,
    get_pending_subscriptions,
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
)
from tools.complaints import (
    get_complaints,
    get_complaint_status_count,
    get_problem_types,
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
}

ROUTER_SYSTEM_PROMPT_TEMPLATE = """You are the API Router for BillerQ AI Assistant.
Your task is to analyze the user's message and determine the single most appropriate BillerQ API tool to run.
You must also extract arguments for that tool and the customer name/identifier if specified.

Today's Date: {current_date}

## Available Tools:
1. `get_customer_status_count` - For active/inactive customer counts and percentages.
2. `get_recent_payments` - To get the most recent payments made.
3. `get_unpaid_customers` - To get customers with unpaid/outstanding balances.
4. `get_overdue_list` - To get a list of overdue payments/collections.
5. `get_overdues` - To get summary counts of overdue payments.
6. `get_complaints` - To get lists of customer complaints.
7. `get_complaint_status_count` - To get counts of complaint statuses.
8. `get_dashboard_data` - To get general dashboard metrics, revenue summaries, overall performance, daily collection (today's collection), monthly collection (this month's collection), total outstanding dues, and total wallet amount.
9. `get_connection_data` - To get connection statistics (active/inactive).
10. `get_package_report` - To get package summary report/stats.
11. `get_wallet_report` - To get wallet balance report/stats.
12. `get_tax_report` - To get tax report/stats.
13. `get_subscription_report` - To get subscription reports.
14. `get_addon_report` - To get customer add-on reports.
15. `get_agent_collection_report` - To get collection details by agents.
16. `get_income_summary` - To get income summaries/details (do NOT use for daily/monthly collection metrics, use get_dashboard_data instead).
17. `get_expense_summary` - To get expense summaries/details.
18. `get_customer_profile` - To get detailed profile/personal info of a specific customer. (Requires a customer name).
19. `get_payment_history` - To get payment records of a specific customer. (Requires a customer name).
20. `get_subscription` - To get active subscriptions of a specific customer. (Requires a customer name).
21. `get_customer_stb` - To get Set-Top Box (STB) details of a specific customer. (Requires a customer name).
22. `search_customer` - To search/list customers, or if the intent is a general list/search of customer names.
23. `get_invoices` - To get all invoices/orders in the system or filter invoices/orders for a specific customer.

If no tool is needed (e.g. general greeting, chit-chat, simple question that doesn't need database access), select "none".

## Rules for Response:
1. Output ONLY a valid JSON object. Do not include markdown code blocks, explanation, or other text outside of the JSON.
2. The JSON schema must be:
{{
  "tool": "tool_name_or_none",
  "arguments": {{
    "arg_name": "arg_value"
  }},
  "customer_name": "name_or_null"
}}
3. If the query concerns a specific customer, ALWAYS populate "customer_name" with their name, phone number, or subscriber ID.
4. Example outputs:
- User: "how many active customers" -> {{"tool": "get_customer_status_count", "arguments": {{}}, "customer_name": null}}
- User: "details of Joy P" -> {{"tool": "get_customer_profile", "arguments": {{}}, "customer_name": "Joy P"}}
- User: "payments of 9876543210" -> {{"tool": "get_payment_history", "arguments": {{}}, "customer_name": "9876543210"}}
- User: "show me recent payments" -> {{"tool": "get_recent_payments", "arguments": {{}}, "customer_name": null}}
- User: "hello there!" -> {{"tool": "none", "arguments": {{}}, "customer_name": null}}
"""

FORMATTER_SYSTEM_PROMPT_TEMPLATE = """You are the Response Formatter for BillerQ AI Assistant.
Your task is to take the user's original query, the name of the executed API tool, and the raw API result, and generate a perfect summary.

Today's Date: {current_date}

## Strict Formatting Rules:
1. If the API result contains a list of records (such as unpaid customers, recent payments, overdues, complaints, reports):
   - **Show the total first**: Show the total amount or total count clearly first. E.g. "Total unpaid amount: ₹50,000" or "Total active customers: 1,771".
   - **Show total count of people**: State how many people or records exist in total. E.g. "There are 22 unpaid customers in total."
   - **Show top 5 people/records**: Present the details (name, amount/status/date/area) of only the top 5 records. Use clean bullet points (•).
   - **Direct user to click below for remaining**: For the remaining records, write "For the remaining, click the link below." or similar text. Do not list any more.
2. If the user query is about a specific customer:
   - Sort out their details cleanly (Name, Status, Mobile, Area, Subscription, Balance) and display them in a professional, well-spaced list.
3. If the user query is about previous month data:
   - Today is in June 2026. The previous month is May 2026. Prioritize filtering or summarizing data specifically for May 2026.
4. Output only clean plain text. Do NOT use markdown code fences, headers (like # or ##), or bold/italic markers (like ** or *) as the chat widget does not render them. Use newlines and bullet points (•) for structure.
5. Use ₹ symbol for Indian Rupee currency values.
6. Keep the tone friendly, helpful, and professional. Do not reference raw IDs, API keys, or technical jargon.
7. If no tool was run or the result is an error, answer the user's query directly or explain the error helpfully in conversational language.
8. **Keep response extremely short**: To optimize processing speed, the response MUST be brief and direct. Avoid conversational filler, introductory pleasantries, or concluding remarks. Get straight to the numbers and requested data points.
"""


class BillerQAgent:
    """Agent running a structured pipeline using OllamaProvider (Mistral:7b)."""

    def __init__(self, llm):
        self.llm = llm

    async def run(self, message: str, context: dict = None, billerq_token: str = "", billerq_api_url: str = "", billerq_user_role: int | None = None) -> tuple[str, dict]:
        """Runs the agent pipeline to answer a user query.

        Steps:
            1. Analyze user message via Router LLM to select tool and target customer.
            2. Automatically resolve customer name/ID if needed.
            3. Run the selected tool.
            4. Format and summarize the raw data via Formatter LLM.
        """
        current_date = datetime.now().strftime("%d %B %Y")
        
        def format_curr(val):
            try:
                if isinstance(val, (int, float)):
                    return f"{val:,.2f}"
                cleaned = str(val).replace(",", "").strip()
                return f"{float(cleaned):,.2f}"
            except (ValueError, TypeError):
                return str(val)
        
        from api.client import api_client
        original_base_url = api_client.base_url
        api_client._request_token_override = billerq_token if billerq_token else None
        api_client._request_user_role_override = billerq_user_role
        if billerq_api_url:
            api_client.base_url = billerq_api_url.rstrip("/")
            logger.info("Overriding API client base URL for run context with: %s", api_client.base_url)

        try:
            # -------------------------------------------------------------
            # Step 1: Route/Select Tool
            # -------------------------------------------------------------
            msg_lower = message.lower().strip()
            fast_result = None

            # Fast routing rules
            if re.search(r"\b(active|inactive|total)\s+customers?\b", msg_lower) or re.search(r"\bhow many active\b", msg_lower):
                fast_result = {"tool": "get_customer_status_count", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["collection", "collected", "revenue meter"]) or any(k in msg_lower for k in ["outstanding dues", "total dues", "dues", "wallet"]):
                fast_result = {"tool": "get_dashboard_data", "arguments": {}, "customer_name": None}
            elif "unpaid" in msg_lower:
                fast_result = {"tool": "get_unpaid_customers", "arguments": {}, "customer_name": None}
            elif "connection" in msg_lower:
                fast_result = {"tool": "get_connection_data", "arguments": {}, "customer_name": None}
            elif "recent payment" in msg_lower or "recent transactions" in msg_lower or "last payments" in msg_lower:
                fast_result = {"tool": "get_recent_payments", "arguments": {}, "customer_name": None}
            elif "overdue list" in msg_lower or "overdue cases" in msg_lower or "overdue follow" in msg_lower:
                fast_result = {"tool": "get_overdue_list", "arguments": {}, "customer_name": None}
            elif "complaint status" in msg_lower or "complaints count" in msg_lower:
                fast_result = {"tool": "get_complaint_status_count", "arguments": {}, "customer_name": None}
            elif "complaint" in msg_lower:
                fast_result = {"tool": "get_complaints", "arguments": {}, "customer_name": None}
            elif "invoice" in msg_lower or "order" in msg_lower or "bill" in msg_lower:
                fast_result = {"tool": "get_invoices", "arguments": {}, "customer_name": None}
            else:
                # Customer name profile patterns: "details of Joy P", "payments of Joy P", etc.
                cust_match = re.search(r"\b(?:details|profile|info|about|stb|subscription|payments?|history|invoices?|bills?)\s+(?:of|for)\s+([a-zA-Z0-9\s\.\-\u00C0-\u017F]+)", msg_lower)
                if cust_match:
                    name_extracted = cust_match.group(1).strip()
                    if name_extracted and name_extracted not in ["customer", "customers", "my account", "this month", "today", "yesterday", "recent payments", "unpaid customers", "recent invoices", "invoices"]:
                        tool = "get_customer_profile"
                        if "payment" in msg_lower or "history" in msg_lower:
                            tool = "get_payment_history"
                        elif "stb" in msg_lower:
                            tool = "get_customer_stb"
                        elif "sub" in msg_lower:
                            tool = "get_subscription"
                        elif "invoice" in msg_lower or "bill" in msg_lower:
                            tool = "get_invoices"
                        fast_result = {"tool": tool, "arguments": {}, "customer_name": name_extracted}

            if fast_result:
                logger.info("Fast routed query (bypassed LLM): %s", fast_result)
                router_result = fast_result
            else:
                router_system_prompt = ROUTER_SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)
                
                # Build prompt with history
                router_messages = [
                    {"role": "system", "content": router_system_prompt}
                ]
                
                if context and context.get("history"):
                    for turn in context["history"][-3:]:
                        router_messages.append({"role": "user", "content": turn.get("user", "")})
                        router_messages.append({"role": "assistant", "content": turn.get("assistant", "")})
                        
                router_messages.append({"role": "user", "content": message})
                
                logger.info("Routing query via LLM: '%s'", message[:100])
                
                # Call LLM to route
                try:
                    router_raw = await self.llm.chat(router_messages, temperature=0.1, num_predict=100)
                    logger.info("Router LLM response: %s", router_raw)
                    router_result = self._parse_router_response(router_raw)
                except Exception as e:
                    logger.exception("Router call failed")
                    router_result = {"tool": "none", "arguments": {}, "customer_name": None}
                
            tool_name = router_result.get("tool", "none")
            tool_args = router_result.get("arguments", {})
            customer_name_query = router_result.get("customer_name")
            
            logger.info("Routed tool: %s, args: %s, customer_name: %s", tool_name, tool_args, customer_name_query)

            # -------------------------------------------------------------
            # Step 2: Customer Resolution
            # -------------------------------------------------------------
            resolved_cust_id = None
            resolved_cust_name = None
            
            # If the tool is a customer tool, or customer_name_query is present
            requires_customer = tool_name in (
                "get_customer_profile",
                "get_payment_history",
                "get_subscription",
                "get_customer_stb",
                "search_customer"
            )
            
            # Fallback to context customer if name not explicitly extracted but tool requires it
            if requires_customer and not customer_name_query:
                if context and context.get("last_customer_id"):
                    resolved_cust_id = context.get("last_customer_id")
                    resolved_cust_name = context.get("last_customer_name")
                    logger.info("Resolved customer from context: %s (ID: %s)", resolved_cust_name, resolved_cust_id)
                    
            if customer_name_query:
                from agent.resolver import resolver
                try:
                    res = await resolver.resolve_customer(str(customer_name_query))
                    if res.get("found"):
                        resolved_cust_id = res["customer_id"]
                        resolved_cust_name = res["customer_name"]
                    else:
                        # Ambiguous / multiple candidates matching name
                        if res.get("candidates"):
                            candidates = res["candidates"]
                            candidate_text = "I found multiple customers matching that query. Did you mean:\n"
                            for i, c in enumerate(candidates, 1):
                                name = c.get("name", "Unknown")
                                area = c.get("area", "")
                                mobile = c.get("mobile", "")
                                detail = f"• {name}"
                                if area:
                                    detail += f" ({area})"
                                if mobile:
                                    detail += f" — {mobile}"
                                candidate_text += f"{detail}\n"
                            
                            # Return candidates list directly with redirect metadata
                            return candidate_text, {
                                "redirect_url": "/customers/customer",
                                "redirect_label": "View customers"
                            }
                        else:
                            # Not found
                            return f"I couldn't find any customer matching '{customer_name_query}'. Please verify the details or name.", {}
                except Exception as e:
                    logger.exception("Error in customer resolution")
                    
            # Bind customer_id to arguments if resolved
            if resolved_cust_id:
                tool_args["customer_id"] = resolved_cust_id
                # If the tool was just search_customer, promote it to get_customer_profile for richer details
                if tool_name == "search_customer":
                    tool_name = "get_customer_profile"

            # -------------------------------------------------------------
            # Step 3: Tool Execution
            # -------------------------------------------------------------
            tool_result = None
            if tool_name and tool_name != "none":
                logger.info("Executing tool: %s with args: %s", tool_name, tool_args)
                try:
                    tool_result = await self._execute_tool(tool_name, tool_args, billerq_token, billerq_api_url, billerq_user_role)
                except Exception as e:
                    logger.exception("Tool execution failed")
                    tool_result = {"error": f"Failed to execute tool: {str(e)}"}
                    
            logger.info("Tool execution complete. Result data size/type: %s", type(tool_result))

            # -------------------------------------------------------------
            # Step 4: Formatting & Summarization
            # -------------------------------------------------------------
            # Speed optimization: bypass Formatter LLM for simple queries, metrics, errors or empty data
            rule_based_response = None
            if isinstance(tool_result, dict):
                if "error" in tool_result:
                    err_msg = tool_result["error"]
                    if "Please login to proceed" in str(err_msg) or "403" in str(err_msg):
                        rule_based_response = "I'm sorry for the inconvenience, but it seems there was an issue with the API request. To view this information, please log in to your account first. Once you're logged in, feel free to ask again and I'll be happy to help!"
                    else:
                        rule_based_response = f"I'm sorry, but I encountered an issue while retrieving the data: {err_msg}. Please check your connection and try again."

                # 1. get_customer_status_count
                elif tool_name == "get_customer_status_count":
                    data = tool_result.get("data")
                    if isinstance(data, list):
                        active_count = next((c.get("count") for c in data if c.get("status") == "Active"), None)
                        total_count = next((c.get("count") for c in data if c.get("status") == "Total"), None)
                        if active_count is not None:
                            rule_based_response = f"Total active customers: {active_count:,}"
                            if total_count is not None:
                                rule_based_response += f" (out of {total_count:,} total customers)."

                # 2. get_connection_data
                elif tool_name == "get_connection_data":
                    conn_data = tool_result.get("data", {})
                    if conn_data:
                        total_conn = conn_data.get("total_connections") or conn_data.get("total", 0)
                        active_conn = conn_data.get("active_connections") or conn_data.get("active", 0)
                        inactive_conn = conn_data.get("inactive_connections") or conn_data.get("inactive", 0)
                        rule_based_response = f"Connection Statistics:\n• Total Connections: {total_conn}\n• Active Connections: {active_conn}\n• Inactive Connections: {inactive_conn}"

                # 3. get_recent_payments
                elif tool_name == "get_recent_payments":
                    data_wrapper = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(data_wrapper, dict):
                        items = data_wrapper.get("data", [])
                        total = data_wrapper.get("total", len(items))
                    elif isinstance(data_wrapper, list):
                        items = data_wrapper
                        total = len(items)
                    
                    if not items:
                        rule_based_response = "No recent payments found in the system."
                    else:
                        lines = [f"Total recent payments: {total}", "Here are the top 5 payments:"]
                        for item in items[:5]:
                            cust = item.get("customer") or {}
                            cname = item.get("name") or (cust.get("name") if isinstance(cust, dict) else None) or "Unknown Customer"
                            amount = item.get("amount") or item.get("paid_amount") or 0
                            date = item.get("payment_date") or item.get("created_at") or "N/A"
                            method = item.get("payment_method") or item.get("method") or "N/A"
                            lines.append(f"• {cname}: ₹{amount} paid via {method} on {date}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 4. get_unpaid_customers
                elif tool_name == "get_unpaid_customers":
                    unpaid_data = tool_result.get("data", {})
                    if isinstance(unpaid_data, dict):
                        total_amount = unpaid_data.get("total_amount", 0)
                        customers_raw = unpaid_data.get("customers", {})
                        if isinstance(customers_raw, dict):
                            customers = customers_raw.get("data", [])
                            total_count = customers_raw.get("total", len(customers))
                        elif isinstance(customers_raw, list):
                            customers = customers_raw
                            total_count = len(customers)
                        else:
                            customers = []
                            total_count = 0
                            
                        if not customers:
                            rule_based_response = "No unpaid customers found in the system."
                        else:
                            lines = [
                                f"Total unpaid amount: ₹{format_curr(total_amount)}",
                                f"There are {total_count} unpaid customers in total.",
                                "\nHere are the top 5 unpaid customers:"
                            ]
                            for c in customers[:5]:
                                cname = c.get("customer_name") or c.get("name") or "Unknown Customer"
                                area = c.get("area_name") or c.get("billing_area") or c.get("area") or "N/A"
                                balance = c.get("dues") or c.get("balance") or c.get("unpaid_amount") or 0
                                lines.append(f"• {cname} ({area}): ₹{format_curr(balance)} unpaid")
                            if len(customers) > 5:
                                lines.append("\nFor the remaining, click the link below.")
                            rule_based_response = "\n".join(lines)

                # 5. overdues or overdue_list
                elif tool_name in ("get_overdues", "get_overdue_list", "overdues", "overdue_list"):
                    overdue_data = tool_result.get("data", {})
                    if isinstance(overdue_data, dict):
                        count = overdue_data.get("count") or overdue_data.get("total") or len(overdue_data.get("data", []))
                        items = overdue_data.get("data", [])
                        if not items:
                            rule_based_response = "No overdue payments found."
                        else:
                            lines = [
                                f"Total overdue cases: {count}",
                                "\nHere are the top overdue cases:"
                            ]
                            for item in items[:5]:
                                cname = item.get("name") or "Unknown"
                                date = item.get("next_followup_date") or item.get("next_followup") or "N/A"
                                assigned = item.get("assigned_to") or "Unassigned"
                                lines.append(f"• {cname}: Next Follow-up on {date} (Assigned to: {assigned})")
                            if count > 5:
                                lines.append("\nFor the remaining, click the link below.")
                            rule_based_response = "\n".join(lines)

                # 6. complaint_status_count
                elif tool_name == "complaint_status_count":
                    data = tool_result.get("data")
                    if isinstance(data, list):
                        lines = ["Complaint Status Counts:"]
                        for item in data:
                            status = item.get("status")
                            count = item.get("count")
                            lines.append(f"• {status}: {count}")
                        rule_based_response = "\n".join(lines)

                # 7. get_complaints
                elif tool_name == "get_complaints":
                    data_wrapper = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(data_wrapper, dict):
                        items = data_wrapper.get("data", [])
                        total = data_wrapper.get("total") or len(items)
                    elif isinstance(data_wrapper, list):
                        items = data_wrapper
                        total = len(items)
                        
                    if not items:
                        rule_based_response = "No complaints found in the system."
                    else:
                        lines = [f"Total complaints: {total}", "\nHere are the top 5 complaints:"]
                        for item in items[:5]:
                            ptype = item.get("problem_type") or "General"
                            status = item.get("status") or "open"
                            date = item.get("start_date") or item.get("created_at") or "N/A"
                            lines.append(f"• Complaint #{item.get('complaint_no', item.get('id'))}: Type: {ptype}, Status: {status}, Date: {date}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 8. get_dashboard_data
                elif tool_name == "get_dashboard_data":
                    data = tool_result.get("data", {})
                    if isinstance(data, dict):
                        comp = data.get("complaints", {})
                        subs = data.get("subscriptions", {})
                        pay = data.get("payment_collection", {})
                        cond = data.get("check_condition", {})
                        
                        msg_lower = message.lower()
                        if "this month" in msg_lower and "collection" in msg_lower:
                            rule_based_response = f"Total collection for this month: ₹{pay.get('this_month', '0.00')}"
                        elif "today" in msg_lower and "collection" in msg_lower:
                            rule_based_response = f"Total collection for today: ₹{pay.get('today', '0.00')}"
                        elif "outstanding" in msg_lower or "dues" in msg_lower:
                            rule_based_response = f"Total outstanding dues: ₹{pay.get('dues', '0.00')}"
                        elif "wallet" in msg_lower:
                            rule_based_response = f"Total wallet balance: ₹{pay.get('wallet_amount', '0.00')}"
                        else:
                            lines = [
                                "Dashboard Overview:",
                                f"• Total Customers: {cond.get('customers', 0):,}",
                                f"• Active STBs: {cond.get('stb', 0):,}",
                                f"• Active Packages: {cond.get('packages', 0):,}",
                                "",
                                "Payments & Collection:",
                                f"• Collected Today: ₹{pay.get('today', '0.00')}",
                                f"• Collected This Month: ₹{pay.get('this_month', '0.00')}",
                                f"• Outstanding Dues: ₹{pay.get('dues', '0.00')}",
                                f"• Wallet Amount: ₹{pay.get('wallet_amount', '0.00')}",
                                "",
                                "Subscriptions Summary:",
                                f"• Total Active Subscriptions: {subs.get('totalSubscriptions', 0)}",
                                f"• Expired Subscriptions: {subs.get('expired', 0)}",
                                f"• Expiring Today: {subs.get('today', 0)}",
                                f"• Expiring in 5 Days: {subs.get('in_five_days', 0)}",
                                "",
                                "Complaints Status:",
                                f"• Unresolved Complaints: {comp.get('un_resolved', 0)}",
                                f"• In Process: {comp.get('in_process', 0)}",
                                f"• Resolved: {comp.get('resolved', 0)}"
                            ]
                            rule_based_response = "\n".join(lines)

                # 9. get_customer_profile
                elif tool_name == "get_customer_profile" and resolved_cust_name:
                    data = tool_result.get("data", {})
                    if isinstance(data, dict):
                        det = data.get("customer_details", {})
                        lines = [
                            f"Customer Profile: {data.get('customer_name', resolved_cust_name).title()}",
                            f"• Subscriber ID: {det.get('subscriber_id', 'N/A')}",
                            f"• Status: Active" if int(data.get("connections", 0)) > 0 else f"• Status: Inactive",
                            f"• Mobile: {det.get('mobile', 'N/A')}",
                            f"• Area: {data.get('area', 'N/A')}",
                            f"• Joined: {data.get('join_date', 'N/A')}",
                            f"• Address: {data.get('address', 'N/A')}",
                            "",
                            "Account Summary:",
                            f"• Total Paid: ₹{data.get('paid_amount', '0.00')}",
                            f"• Open Invoices: ₹{data.get('open_invoice_amount', '0.00')}",
                            f"• Overdue Invoices: ₹{data.get('overdue_invoice_amount', '0.00')}",
                            f"• Wallet Balance: ₹{data.get('wallet_money', '0.00')}",
                            f"• Connections: {data.get('connections', 0)} ({', '.join(det.get('connections', []))})"
                        ]
                        rule_based_response = "\n".join(lines)

                # 10. get_subscription
                elif tool_name == "get_subscription" and resolved_cust_name:
                    data_wrapper = tool_result.get("data", {})
                    items = []
                    if isinstance(data_wrapper, dict):
                        items = data_wrapper.get("data", [])
                    elif isinstance(data_wrapper, list):
                        items = data_wrapper
                        
                    if not items:
                        rule_based_response = f"No subscriptions found for {resolved_cust_name}."
                    else:
                        lines = [f"Subscriptions for {resolved_cust_name}:"]
                        for item in items:
                            pkg = item.get("package_name") or "Unknown Plan"
                            stb = item.get("stb_no") or "N/A"
                            status = item.get("status") or "active"
                            start = item.get("plan_date") or item.get("start_date") or "N/A"
                            end = item.get("recurring_date") or item.get("end_date") or "N/A"
                            inv = item.get("invoice_number") or "N/A"
                            lines.append(f"• Package: {pkg} ({status.upper()})\n  STB: {stb} | Plan Start: {start} | Recurring/End Date: {end}\n  Latest Invoice: {inv}")
                        rule_based_response = "\n".join(lines)

                # 11. search_customer
                elif tool_name == "search_customer":
                    data = tool_result.get("data", [])
                    if isinstance(data, list):
                        if not data:
                            rule_based_response = "No customers found matching your search query."
                        else:
                            lines = [f"Found {len(data)} matching customers:"]
                            for item in data[:5]:
                                name = item.get("customer_name") or "Unknown"
                                sub_id = item.get("subscriber_id") or "N/A"
                                stbs = [s.get("stb_no") for s in item.get("stb", []) if s.get("stb_no")]
                                lines.append(f"• Name: {name} (Sub ID: {sub_id})")
                                if stbs:
                                    lines.append(f"  STB No: {', '.join(stbs)}")
                            if len(data) > 5:
                                lines.append("\nFor the remaining, click the link below.")
                            rule_based_response = "\n".join(lines)

                # 12. get_invoices
                elif tool_name == "get_invoices":
                    data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(data, dict):
                        items = data.get("data", [])
                        total = data.get("total", len(items))
                    elif isinstance(data, list):
                        items = data
                        total = len(items)
                    
                    if not items:
                        if resolved_cust_name:
                            rule_based_response = f"No invoices found for customer {resolved_cust_name}."
                        else:
                            rule_based_response = "No invoices found in the system."
                    else:
                        header = f"Invoices for {resolved_cust_name}:" if resolved_cust_name else f"Total invoices: {total}"
                        lines = [header, "Here are the recent invoices:"]
                        for item in items[:5]:
                            inv_no = item.get("invoice_no") or item.get("id") or "N/A"
                            pref = item.get("invoice_prefix") or "INV"
                            cname = item.get("customer_name") or resolved_cust_name or "Unknown Customer"
                            sub_id = item.get("subscriber_id") or "N/A"
                            amount = item.get("amount") or f"₹{item.get('balance', '0.00')}"
                            date = item.get("invoice_date") or item.get("created_date") or "N/A"
                            status = item.get("payment_status") or item.get("order_status") or "N/A"
                            lines.append(f"• #{pref}{inv_no} — {cname} (Sub ID: {sub_id}): {amount} ({status.upper()}) on {date}")
                        if total > 5 or len(items) > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

            if rule_based_response:
                logger.info("Bypassing Formatter LLM — using rule-based response: '%s'", rule_based_response)
                metadata = self._get_redirect_metadata(tool_name, resolved_cust_id, resolved_cust_name)
                return rule_based_response, metadata

            formatter_system_prompt = FORMATTER_SYSTEM_PROMPT_TEMPLATE.format(current_date=current_date)
            
            # Prepare context data for formatting
            data_to_format = tool_result if tool_result is not None else {}
            
            # Keep lists from blowing up LLM context window
            from agent.formatter import sanitize_and_truncate_data
            truncated_data = sanitize_and_truncate_data(data_to_format, max_list_len=15)
            data_str = json.dumps(truncated_data, indent=2, default=str)
            if len(data_str) > 8000:
                data_str = data_str[:8000] + "\n... (data truncated for brevity)"
                
            formatter_user_prompt = (
                f"User's question: {message}\n"
                f"Executed tool: {tool_name}\n"
            )
            if resolved_cust_name:
                formatter_user_prompt += f"Customer Name: {resolved_cust_name} (ID: {resolved_cust_id})\n"
            formatter_user_prompt += f"\nRaw API data:\n{data_str}"
            
            formatter_messages = [
                {"role": "system", "content": formatter_system_prompt},
                {"role": "user", "content": formatter_user_prompt}
            ]
            
            try:
                logger.info("Formatting response via LLM...")
                final_text = await self.llm.chat(formatter_messages, temperature=0.3, num_predict=200)
                final_text = final_text.strip()
            except Exception as e:
                logger.exception("Formatter call failed")
                final_text = "I encountered an issue formatting the API response. Here is the raw information: " + data_str[:500]

            # Ensure that redirect button metadata matches the tool executed
            metadata = self._get_redirect_metadata(tool_name, resolved_cust_id, resolved_cust_name)
            
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

    def _get_redirect_metadata(self, tool_name: str, resolved_cust_id: int = None, resolved_cust_name: str = None) -> dict:
        """Constructs redirection metadata for the frontend."""
        metadata = {}
        if resolved_cust_id:
            metadata["customer_id"] = resolved_cust_id
        if resolved_cust_name:
            metadata["customer_name"] = resolved_cust_name

        if not tool_name or tool_name == "none":
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
            "get_recent_payments": ("/billing/invoice", "View invoices"),
            "get_package_report": ("/report/package-summary", "View report"),
            "get_wallet_report": ("/report/wallet-balance", "View report"),
            "get_tax_report": ("/report/tax-report", "View report"),
            "get_subscription_report": ("/report/package-summary", "View report"),
            "get_addon_report": ("/report/package-summary", "View report"),
            "get_agent_collection_report": ("/report/package-summary", "View report"),
            "get_income_summary": ("/dashboard/default", "Open analytics"),
            "get_expense_summary": ("/dashboard/default", "Open analytics"),
            "get_dashboard_data": ("/dashboard/default", "Open analytics"),
            "get_connection_data": ("/dashboard/default", "Open analytics"),
            "get_complaints": ("/complaints", "View complaints"),
            "get_complaint_status_count": ("/complaints", "View complaints"),
            "get_invoices": ("/billing/invoice", "View invoices"),
        }

        url_label = tool_map.get(tool_name)
        if url_label:
            metadata["redirect_url"] = url_label[0]
            metadata["redirect_label"] = url_label[1]

        return metadata

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
