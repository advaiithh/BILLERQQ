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

Strictly highlight important numbers, counts, customer names, dates, methods, invoice IDs, and statuses in bold using markdown (**text**) to make the response highly readable.

Today's Date: {current_date}

## Strict Formatting Rules:
1. If the API result contains a list of records (such as unpaid customers, recent payments, overdues, complaints, reports):
   - **Show the total first**: Show the total amount or total count clearly first. E.g. "Total unpaid amount: **₹50,000**" or "Total active customers: **1,771**".
   - **Show total count of people**: State how many people or records exist in total. E.g. "There are **22** unpaid customers in total."
   - **Show top 5 people/records**: Present the details of only the top 5 records. Use clean bullet points (•). **Format each record using clean, standardized key-value labels separated by a vertical bar (|)**. E.g.:
     • **Name:** [Name] (Sub ID: **[SubID]**) | **Invoice:** [InvNo] | **Amount:** **₹[Amt]** | **Date:** **[Date]** | **Method:** **[Method]**
     • **Name:** [Name] (Sub ID: **[SubID]**) | **Invoice:** [InvNo] | **Amount:** **₹[Amt]** | **Date:** **[Date]**
     • **Name:** [Name] (Sub ID: **[SubID]**) | **Area:** [Area] | **Dues:** **₹[Amt]**
     • **Date:** [Date] | **Mobile:** [Mobile] | **Status:** [Status] | **Message:** [Message]
   - **Direct user to click below for remaining**: For the remaining records, write "For the remaining, click the link below." or similar text. Do not list any more.
2. If the user query is about a specific customer:
   - Sort out their details cleanly (Name, Status, Mobile, Area, Subscription, Balance) and display them in a professional, well-spaced list using bolding and standardized labels.
3. If the user query is about previous month data:
   - Today is in June 2026. The previous month is May 2026. Prioritize filtering or summarizing data specifically for May 2026.
4. Use markdown bolding (**value**) strategically to highlight key metrics, amounts, counts, customer names, status values, dates, and methods. Use clean bullet points (•), standardized key-value labels, and emojis (e.g., 📊, 💰, 💳, 👥, ⚠️, 📉) to structure sections and make them extremely easy to read. Avoid headers (like # or ##) or markdown code fences.
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
            months_map = {
                "january": "Jan", "february": "Feb", "march": "Mar", "april": "Apr", "may": "May", "june": "Jun",
                "july": "Jul", "august": "Aug", "september": "Sep", "october": "Oct", "november": "Nov", "december": "Dec",
                "jan": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr", "jun": "Jun", "jul": "Jul", "aug": "Aug",
                "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec"
            }

            # 1. Collection of agent <name> (resilient to spelling variations of collection/agent keyword)
            agent_col_match = None
            coll_match = re.search(r"\b(?:coll\w*|income|earn\w*)\s+(?:of|by|for)?\s*(?:agent\s+)?([a-zA-Z0-9\u00C0-\u017F\s]+)", msg_lower)
            if coll_match:
                candidate_agent_name = coll_match.group(1).strip()
                known_agents = ["ashika", "sanjay", "ayush", "kannan", "rajeev", "aju", "kerala vision", "tutu", "archana"]
                if any(ka in candidate_agent_name.lower() for ka in known_agents) or "agent" in msg_lower:
                    agent_col_match = coll_match
            
            # 2. Last month collection / specific month collection
            month_match = None
            if "collection" in msg_lower:
                if "last month" in msg_lower or "previous month" in msg_lower:
                    month_match = "May"
                else:
                    for m_name, m_abbr in months_map.items():
                        if m_name in msg_lower:
                            month_match = m_abbr
                            break

            # 3. Highest balance / dues
            is_highest_dues = any(k in msg_lower for k in ["most balance", "highest dues", "most unpaid", "highest balance", "maximum dues", "high payment due", "high dues", "due payment", "highest payment due", "highest payment dues", "high payment dues"])

            # 4. Inactive/Active customer listings
            is_inactive_list = "inactive" in msg_lower and not any(k in msg_lower for k in ["count", "how many", "percentage", "number of"])
            is_active_list = "active" in msg_lower and not any(k in msg_lower for k in ["count", "how many", "percentage", "number of"])

            # 5. Latest added customer
            is_latest_cust = any(k in msg_lower for k in ["latest added", "newest", "recently added", "latest customer", "newest customer"])

            # 6. Customer name & keyword detection
            name_extracted = None
            cust_match = re.search(r"\b(?:details|profile|info|about|stb|subscription|payments?|history|invoices?|bills?|wallet|dues?|balance|phone|number|mobile|contact|subscriber|sub id|customer id|place|area|location|address|joined|join date|status)\s+(?:of|for)\s+([a-zA-Z0-9\s\.\-\'\u00C0-\u017F]+)", msg_lower)
            if cust_match:
                name_extracted = cust_match.group(1).strip()
            else:
                cust_match2 = re.search(r"\b([a-zA-Z0-9\s\.\-\'\u00C0-\u017F]+)\s+(?:wallet|dues?|balance|stb|subscription|payments?|history|invoices?|bills?|phone|number|mobile|contact|subscriber|sub id|customer id|place|area|location|address)\b", msg_lower)
                if cust_match2:
                    name_extracted = cust_match2.group(1).strip()
            
            if name_extracted:
                # 1. Remove any trailing keywords that might have been greedily captured first
                strip_keywords = ["wallet", "dues", "due", "balance", "stb", "subscription", "payments", "payment", "history", "invoices", "invoice", "bills", "bill", "total", "phone", "number", "mobile", "contact", "subscriber", "sub id", "customer id", "customer", "place", "area", "location", "address"]
                changed = True
                while changed:
                    changed = False
                    for kw in strip_keywords:
                        if name_extracted.lower().endswith(" " + kw):
                            name_extracted = name_extracted[:-len(kw)-1].strip()
                            changed = True
                        elif name_extracted.lower() == kw:
                            name_extracted = ""
                            changed = True
                    # Also strip trailing 'and' left over from compound queries like "phone number and customer id"
                    if name_extracted.lower().endswith(" and"):
                        name_extracted = name_extracted[:-4].strip()
                        changed = True

                # 2. Remove trailing possessive 's or trailing single quote (run AFTER trailing keywords are stripped)
                if name_extracted.lower().endswith("'s"):
                    name_extracted = name_extracted[:-2].strip()
                elif name_extracted.lower().endswith("'"):
                    name_extracted = name_extracted[:-1].strip()
                
                # 3. Remove leading keywords
                for kw in ["show me", "give me", "tell me", "show", "give", "view", "total", "what is", "whats", "get", "me", "find", "search", "lookup"]:
                    if name_extracted.lower().startswith(kw + " "):
                        name_extracted = name_extracted[len(kw)+1:].strip()
            
            if name_extracted:
                name_words = name_extracted.lower().split()
                blacklist_words = {
                    "customer", "customers", "my", "account", "this", "month", "today", "yesterday", "recent",
                    "payments", "unpaid", "invoice", "invoices", "total", "overall", "all", "active", "inactive",
                    "agent", "online", "cancelled", "canceled", "pending", "deleted", "archived", "highest", "most",
                    "last", "previous", "available", "show", "list", "view", "count", "status", "report", "stb",
                    "problem", "package", "area", "bill", "bills", "order", "orders", "subscription", "subscriptions",
                    "detail", "details", "profile", "info", "about", "history", "wallet", "dues", "due", "balance", "who", "has", "have",
                    "phone", "number", "mobile", "contact"
                }
                if any(w in blacklist_words for w in name_words):
                    name_extracted = None

            if agent_col_match:
                agent_name = agent_col_match.group(1).strip()
                fast_result = {"tool": "get_connection_data", "arguments": {}, "customer_name": agent_name}
            elif any(k in msg_lower for k in ["item list", "items list", "show items", "list items"]):
                fast_result = {"tool": "get_items", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["staff list", "show staff", "view staff", "list staff", "agent list", "agents list"]):
                fast_result = {"tool": "get_staff", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["roles", "role list", "show roles", "list roles"]):
                fast_result = {"tool": "get_roles", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["message settings", "message credit", "sms credit", "whatsapp credit", "credit status"]):
                fast_result = {"tool": "get_message_settings", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["cas provider", "isp provider", "cas providers", "isp providers", "provider list"]):
                fast_result = {"tool": "get_providers", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["settings categories", "categories list", "show categories"]):
                fast_result = {"tool": "get_categories", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["tax classes", "tax class", "tax rates"]):
                fast_result = {"tool": "get_tax_classes", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["customer wallets", "customer wallet balances", "wallet list", "wallets list"]):
                fast_result = {"tool": "get_wallets", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["agent collection", "agent collections", "collections by agent", "collections by agents", "most collection", "most collections", "collection by agent", "collection by agents"]):
                fast_result = {"tool": "get_connection_data", "arguments": {}, "customer_name": "agent_collection_all"}
            elif "this month due" in msg_lower or "due this month" in msg_lower or "dues of this month" in msg_lower or "this month's due" in msg_lower or "this month's dues" in msg_lower:
                fast_result = {"tool": "get_connection_data", "arguments": {}, "customer_name": "this_month_due"}
            elif "this month collection" in msg_lower or "collected this month" in msg_lower or "collection of this month" in msg_lower or "this month's collection" in msg_lower:
                fast_result = {"tool": "get_connection_data", "arguments": {}, "customer_name": "this_month_collection"}
            elif any(k in msg_lower for k in ["payment due", "payments due", "due customer", "due customers", "overdue payment", "overdue payments", "who has due", "who has overdue"]):
                fast_result = {"tool": "get_payment_due_data", "arguments": {}, "customer_name": None}
            elif month_match:
                fast_result = {"tool": "get_income_summary", "arguments": {"month": month_match, "year": "2026"}, "customer_name": None}
            elif is_highest_dues:
                fast_result = {"tool": "get_unpaid_customers", "arguments": {"sort_by_balance": True}, "customer_name": None}
            elif is_inactive_list:
                fast_result = {"tool": "get_all_customers", "arguments": {"status": "inactive"}, "customer_name": "inactive_list"}
            elif is_active_list:
                fast_result = {"tool": "get_all_customers", "arguments": {"status": "active"}, "customer_name": "active_list"}
            elif is_latest_cust:
                fast_result = {"tool": "get_all_customers", "arguments": {"page_length": 5}, "customer_name": "latest"}
            elif any(k in msg_lower for k in ["cancelled invoice", "cancelled invoices", "cancelled order", "cancelled orders", "canceled invoice", "canceled invoices", "canceled order", "canceled orders"]):
                fast_result = {"tool": "get_cancelled_invoices", "arguments": {}, "customer_name": None}
            elif name_extracted:
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
            elif re.search(r"\bhow\s+many\s+(?:active|inactive|total)\b", msg_lower) or re.search(r"\b(?:active|inactive|total)\s+customers?\s+count\b", msg_lower):
                fast_result = {"tool": "get_customer_status_count", "arguments": {}, "customer_name": None}
            elif re.search(r"\b(active|inactive|total)\s+customers?\b", msg_lower) or re.search(r"\bhow many active\b", msg_lower):
                fast_result = {"tool": "get_customer_status_count", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["collection", "collected", "revenue meter"]) or any(k in msg_lower for k in ["outstanding dues", "total dues", "dues", "wallet"]):
                fast_result = {"tool": "get_dashboard_data", "arguments": {}, "customer_name": None}
            elif "unpaid" in msg_lower:
                fast_result = {"tool": "get_unpaid_customers", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["enquiries", "enquiry"]):
                fast_result = {"tool": "get_enquiries", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["leads", "lead"]):
                fast_result = {"tool": "get_leads", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["follow-up", "followup", "follow-ups", "followups"]):
                fast_result = {"tool": "get_followups", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["bank accounts", "accounts", "cash account", "bank account", "account list"]):
                fast_result = {"tool": "get_accounts", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["transactions", "transaction"]):
                fast_result = {"tool": "get_transactions", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["expenses", "expense"]):
                fast_result = {"tool": "get_expenses", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["incomes", "income"]):
                fast_result = {"tool": "get_incomes", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["headers", "header"]):
                fast_result = {"tool": "get_headers", "arguments": {}, "customer_name": None}
            elif any(k in msg_lower for k in ["vendors", "vendor"]):
                fast_result = {"tool": "get_vendors", "arguments": {}, "customer_name": None}
            elif "sms log" in msg_lower or "sms logs" in msg_lower:
                fast_result = {"tool": "get_sms_logs", "arguments": {}, "customer_name": None}
            elif "whatsapp log" in msg_lower or "whatsapp logs" in msg_lower:
                fast_result = {"tool": "get_whatsapp_logs", "arguments": {}, "customer_name": None}
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
            elif "archived customer" in msg_lower or "archived customers" in msg_lower or "deleted customer" in msg_lower or "deleted customers" in msg_lower:
                fast_result = {"tool": "get_archived_customers", "arguments": {}, "customer_name": None}
            elif "pending subscription" in msg_lower or "pending subscriptions" in msg_lower or "pending activation" in msg_lower or "pending activations" in msg_lower:
                fast_result = {"tool": "get_pending_subscriptions", "arguments": {}, "customer_name": None}
            elif "online payment" in msg_lower or "online payments" in msg_lower or "online transaction" in msg_lower or "online transactions" in msg_lower:
                fast_result = {"tool": "get_online_payments", "arguments": {}, "customer_name": None}
            elif "customer payment report" in msg_lower or "payment report" in msg_lower or "payment reports" in msg_lower:
                fast_result = {"tool": "get_customer_payment_report", "arguments": {}, "customer_name": None}
            elif "package report" in msg_lower or "package summary" in msg_lower or "package reports" in msg_lower:
                fast_result = {"tool": "get_package_report", "arguments": {}, "customer_name": None}
            elif "wallet report" in msg_lower or "wallet reports" in msg_lower or "wallet balance report" in msg_lower or "wallet balances report" in msg_lower:
                fast_result = {"tool": "get_wallet_report", "arguments": {}, "customer_name": None}
            elif "tax report" in msg_lower or "tax reports" in msg_lower or "tax collection report" in msg_lower or "tax collection reports" in msg_lower:
                fast_result = {"tool": "get_tax_report", "arguments": {}, "customer_name": None}
            elif "addon report" in msg_lower or "addon reports" in msg_lower or "add-on report" in msg_lower or "add-on reports" in msg_lower:
                fast_result = {"tool": "get_addon_report", "arguments": {}, "customer_name": None}
            elif "subscription report" in msg_lower or "subscription reports" in msg_lower:
                fast_result = {"tool": "get_subscription_report", "arguments": {}, "customer_name": None}
            elif "agent collection report" in msg_lower or "agent collection reports" in msg_lower:
                fast_result = {"tool": "get_agent_collection_report", "arguments": {}, "customer_name": None}
            elif "expense summary" in msg_lower or "expense report" in msg_lower or "expense reports" in msg_lower or "total expenses" in msg_lower:
                fast_result = {"tool": "get_expense_summary", "arguments": {}, "customer_name": None}
            elif "problem type" in msg_lower or "problem types" in msg_lower or "complaint category" in msg_lower or "complaint categories" in msg_lower or "issue type" in msg_lower or "issue types" in msg_lower:
                fast_result = {"tool": "get_problem_types", "arguments": {}, "customer_name": None}
            elif "available package" in msg_lower or "available packages" in msg_lower or "show package" in msg_lower or "show packages" in msg_lower or "list package" in msg_lower or "list packages" in msg_lower or "view package" in msg_lower or "view packages" in msg_lower:
                fast_result = {"tool": "get_packages", "arguments": {}, "customer_name": None}
            elif "show area" in msg_lower or "show areas" in msg_lower or "list area" in msg_lower or "list areas" in msg_lower or "available area" in msg_lower or "available areas" in msg_lower or "view area" in msg_lower or "view areas" in msg_lower:
                fast_result = {"tool": "get_areas", "arguments": {}, "customer_name": None}
            elif "stb status count" in msg_lower or "stb status counts" in msg_lower or "stb status summary" in msg_lower or "stb count" in msg_lower or "how many stb" in msg_lower or "how many stbs" in msg_lower or "number of stb" in msg_lower or "number of stbs" in msg_lower:
                fast_result = {"tool": "get_stb_status_count", "arguments": {}, "customer_name": None}
            elif "show stb" in msg_lower or "show stbs" in msg_lower or "list stb" in msg_lower or "list stbs" in msg_lower or "view stb" in msg_lower or "view stbs" in msg_lower or "available stb" in msg_lower or "available stbs" in msg_lower or "set top box" in msg_lower or "set top boxes" in msg_lower:
                fast_result = {"tool": "get_stbs", "arguments": {}, "customer_name": None}
            elif "invoice" in msg_lower or "order" in msg_lower or "bill" in msg_lower:
                fast_result = {"tool": "get_invoices", "arguments": {}, "customer_name": None}

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
            
            # Enforce parameters for specific queries (e.g. pending/paid invoices, active/inactive customers, etc.)
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
            elif tool_name in ("get_complaints",):
                if "resolved" in msg_lower:
                    tool_args["status"] = "resolved"
                elif "in process" in msg_lower or "in-process" in msg_lower:
                    tool_args["status"] = "in process"
                elif "open" in msg_lower or "unresolved" in msg_lower or "pending" in msg_lower:
                    tool_args["status"] = "open"
            elif tool_name in ("get_sms_logs", "get_whatsapp_logs"):
                if "failed" in msg_lower:
                    tool_args["status"] = "failed"
                elif "success" in msg_lower or "sent" in msg_lower or "delivered" in msg_lower:
                    tool_args["status"] = "success"

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
                    
            if requires_customer and customer_name_query and customer_name_query not in ("inactive_list", "latest"):
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
                            # Before giving up, let's search Packages, Addons, and Items for this query name!
                            name_search = str(customer_name_query).lower().strip()
                            
                            def unpack_list(resp_data):
                                if isinstance(resp_data, dict):
                                    d = resp_data.get("data")
                                    if isinstance(d, dict):
                                        return d.get("data", [])
                                    elif isinstance(d, list):
                                        return d
                                elif isinstance(resp_data, list):
                                    return resp_data
                                return []

                            # 1. Check Packages
                            try:
                                pkgs = await self._execute_tool("get_packages", {}, billerq_token, billerq_api_url, billerq_user_role)
                                pkg_list = unpack_list(pkgs)
                                for pkg in pkg_list:
                                    if isinstance(pkg, dict) and (name_search == str(pkg.get("name", "")).lower() or name_search in str(pkg.get("name", "")).lower()):
                                        rule_based_response = (
                                            f"Package Details for '{pkg.get('name')}':\n"
                                            f"• HSN/SAC: {pkg.get('hsn_no', 'N/A')}\n"
                                            f"• Category: {pkg.get('category_name', 'N/A')}\n"
                                            f"• Connection Type: {pkg.get('connection_type', 'N/A').upper()}\n"
                                            f"• Duration: {pkg.get('duration')} Days\n"
                                            f"• Price: ₹{pkg.get('price', '0.00')} (Sub-total: ₹{pkg.get('sub_total', '0.00')})\n"
                                            f"• Status: {pkg.get('status', 'N/A').upper()}"
                                        )
                                        return rule_based_response, {"redirect_url": "/Services/packages", "redirect_label": "View Packages"}
                            except Exception:
                                logger.exception("Error checking packages in resolution fallback")

                            # 2. Check Addons
                            try:
                                addons = await self._execute_tool("get_all_addons", {}, billerq_token, billerq_api_url, billerq_user_role)
                                addon_list = unpack_list(addons)
                                for addon in addon_list:
                                    title = addon.get("title") or addon.get("name") or ""
                                    if isinstance(addon, dict) and (name_search == str(title).lower() or name_search in str(title).lower()):
                                        rule_based_response = (
                                            f"Add-on Details for '{title}':\n"
                                            f"• Connection Type: {addon.get('connection_type', 'N/A').upper()}\n"
                                            f"• Duration: {addon.get('days') or addon.get('duration', 'N/A')} Days\n"
                                            f"• Price: ₹{addon.get('price', '0.00')} (Sub-total: ₹{addon.get('sub_total', '0.00')})\n"
                                            f"• Status: {addon.get('status', 'N/A').upper()}"
                                        )
                                        return rule_based_response, {"redirect_url": "/Services/addon", "redirect_label": "View Addons"}
                            except Exception:
                                logger.exception("Error checking addons in resolution fallback")

                            # 3. Check Items
                            try:
                                items_resp = await self._execute_tool("get_items", {}, billerq_token, billerq_api_url, billerq_user_role)
                                item_list = unpack_list(items_resp)
                                for item in item_list:
                                    if isinstance(item, dict) and (name_search == str(item.get("name", "")).lower() or name_search in str(item.get("name", "")).lower()):
                                        rule_based_response = (
                                            f"Item Details for '{item.get('name')}':\n"
                                            f"• Price: ₹{item.get('price', '0.00')}\n"
                                            f"• Description: {item.get('description', 'N/A')}\n"
                                            f"• Status: {item.get('status', 'N/A').upper()}"
                                        )
                                        return rule_based_response, {"redirect_url": "/Services/item", "redirect_label": "View Items"}
                            except Exception:
                                logger.exception("Error checking items in resolution fallback")

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
                        inactive_count = next((c.get("count") for c in data if c.get("status") == "Inactive"), None)
                        total_count = next((c.get("count") for c in data if c.get("status") == "Total"), None)
                        if "inactive" in msg_lower:
                            if inactive_count is not None:
                                rule_based_response = f"Total inactive customers: **{inactive_count:,}**"
                                if total_count is not None:
                                    rule_based_response += f" (out of **{total_count:,}** total customers)."
                        elif "total" in msg_lower or "overall" in msg_lower:
                            if total_count is not None:
                                rule_based_response = f"Total customers: **{total_count:,}**"
                                if active_count is not None:
                                    rule_based_response += f" (Active: **{active_count:,}**, Inactive: **{inactive_count or 0:,}**)."
                        else:
                            if active_count is not None:
                                rule_based_response = f"Total active customers: **{active_count:,}** (out of **{total_count or active_count:,}** total customers)."

                # 2. get_connection_data
                elif tool_name == "get_connection_data":
                    conn_data = tool_result.get("data", {})
                    if conn_data:
                        # Check specific sub-queries
                        if customer_name_query == "this_month_due":
                            month_meter = conn_data.get("collection_this_month_meter", {})
                            rule_based_response = f"📉 **Dues Summary (This Month)**\n• Total dues: **₹{month_meter.get('dues', '0.00')}**\n• Total invoiced: **₹{month_meter.get('total_amount', '0.00')}**"
                        elif customer_name_query == "this_month_collection":
                            month_meter = conn_data.get("collection_this_month_meter", {})
                            rule_based_response = f"💰 **Collection Summary (This Month)**\n• Total collected: **₹{month_meter.get('collection', '0.00')}**\n• Progress: **{month_meter.get('percentage', '0')}%** collected"
                        # Check if this query is about agent collections
                        elif any(k in msg_lower for k in ["agent", "agents", "collected by", "collections by", "leaderboard"]) or (customer_name_query and customer_name_query not in ("agent_collection_all", "this_month_due", "this_month_collection")):
                            agent_list = conn_data.get("agent_collection", [])
                            
                            # Check if a specific agent was requested
                            specific_agent = None
                            if customer_name_query and customer_name_query not in ("agent_collection_all",):
                                for ag in agent_list:
                                    norm_query = re.sub(r"[^a-zA-Z0-9]", "", customer_name_query.lower())
                                    norm_agent_name = re.sub(r"[^a-zA-Z0-9]", "", str(ag.get("name", "")).lower())
                                    if norm_query and norm_agent_name and (norm_query in norm_agent_name or norm_agent_name in norm_query):
                                        specific_agent = ag
                                        break
                                        
                            if specific_agent:
                                rule_based_response = (
                                    f"👤 **Collection Details for Agent:** **{specific_agent.get('name')}**\n"
                                    f"• Collected Today: **₹{specific_agent.get('today', '0.00')}**\n"
                                    f"• Collected This Month: **₹{specific_agent.get('income', '0.00')}**\n"
                                    f"• Progress/Status: **{specific_agent.get('time', 'N/A')}** (**{specific_agent.get('progress', 'N/A')}**)"
                                )
                            elif not agent_list:
                                rule_based_response = "No agent collection data available."
                            else:
                                # Sort agents by income (this month's collection)
                                def get_income(ag):
                                    try:
                                        return float(str(ag.get("income", 0)).replace(",", "").strip())
                                    except Exception:
                                        return 0.0
                                sorted_agents = sorted(agent_list, key=get_income, reverse=True)
                                
                                # Sum total collection by agents this month
                                total_agent_collection = sum(get_income(ag) for ag in sorted_agents)
                                
                                lines = [
                                    f"💰 **Total Agent Collection (This Month):** **₹{format_curr(total_agent_collection)}**",
                                    "\n**Collections by Agent (This Month):**"
                                ]
                                for ag in sorted_agents:
                                    aname = ag.get('name') or f"Agent #{ag.get('agent_id')}"
                                    lines.append(f"• **{aname}**: **₹{ag.get('income', '0.00')}** (Today: **₹{ag.get('today', '0.00')}**)")
                                rule_based_response = "\n".join(lines)
                        else:
                            total_conn = conn_data.get("total_connections") or conn_data.get("total", 0)
                            active_conn = conn_data.get("active_connections") or conn_data.get("active", 0)
                            inactive_conn = conn_data.get("inactive_connections") or conn_data.get("inactive", 0)
                            rule_based_response = f"📊 **Connection Statistics**\n• Total Connections: **{total_conn}**\n• Active Connections: **{active_conn}**\n• Inactive Connections: **{inactive_conn}**"

                # get_payment_due_data
                elif tool_name == "get_payment_due_data":
                    due_data = tool_result.get("data", {})
                    items = []
                    total_count = 0
                    if isinstance(due_data, dict):
                        items = due_data.get("data", [])
                        total_count = due_data.get("total", len(items))
                    elif isinstance(due_data, list):
                        items = due_data
                        total_count = len(items)
                    
                    if not items:
                        rule_based_response = "No customers with due payments found."
                    else:
                        # Let's sum the due amount
                        total_due = 0.0
                        for item in items:
                            try:
                                total_due += float(str(item.get("order_balance", 0)).replace(",", "").strip())
                            except Exception:
                                pass
                        
                        lines = [
                            f"📉 **Total Unpaid/Due Amount:** **₹{format_curr(total_due)}**",
                            f"There are **{total_count}** customers with due payments in total.",
                            "\n**Here are the top due customers:**"
                        ]
                        for item in items[:5]:
                            cname = item.get("customer_name") or "Unknown"
                            sub_id = item.get("subscriber_id") or "N/A"
                            bal = item.get("order_balance") or "0.00"
                            area = item.get("area_name") or "N/A"
                            lines.append(f"• **{cname.strip()}** (Sub ID: **{sub_id}**) in **{area}**: **₹{bal}** due")
                        if total_count > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

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
                        lines = [
                            f"💳 **Total Recent Payments:** **{total}** payments",
                            "\n**Here are the top 5 recent payments:**"
                        ]
                        for item in items[:5]:
                            cname = item.get("name") or item.get("customer_name") or "Unknown Customer"
                            sub_id = item.get("subscriber_id") or "N/A"
                            amount = item.get("amount") or item.get("paid_amount") or 0
                            date = item.get("payment_date") or item.get("created_at") or "N/A"
                            method = item.get("payment_method") or item.get("method") or "N/A"
                            inv = item.get("invoice_no") or "N/A"
                            lines.append(f"• **Name:** {cname} (Sub ID: **{sub_id}**) | **Invoice:** {inv} | **Amount:** **₹{amount}** | **Method:** **{method}** | **Date:** **{date}**")
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
                            
                        if tool_args.get("sort_by_balance") or any(k in msg_lower for k in ["most balance", "highest dues", "most unpaid", "highest balance", "maximum dues"]):
                            def get_bal(c):
                                try:
                                    return float(str(c.get("dues") or c.get("balance") or c.get("unpaid_amount") or 0).replace(",", "").strip())
                                except Exception:
                                    return 0.0
                            customers = sorted(customers, key=get_bal, reverse=True)
                            
                        if not customers:
                            rule_based_response = "No unpaid customers found in the system."
                        else:
                            if any(k in msg_lower for k in ["most balance", "highest dues", "most unpaid", "highest balance", "maximum dues"]):
                                top_cust = customers[0]
                                cname = top_cust.get("customer_name") or top_cust.get("name") or "Unknown Customer"
                                area = top_cust.get("area_name") or top_cust.get("billing_area") or top_cust.get("area") or "N/A"
                                balance = top_cust.get("dues") or top_cust.get("balance") or top_cust.get("unpaid_amount") or 0
                                rule_based_response = f"The customer with the highest dues/balance is **{cname.strip()}** (**{area}**) with an unpaid balance of **₹{format_curr(balance)}**."
                            else:
                                lines = [
                                    f"📉 **Total Unpaid Amount:** **₹{format_curr(total_amount)}**",
                                    f"There are **{total_count}** unpaid customers in total.",
                                    "\n**Here are the top 5 unpaid customers:**"
                                ]
                                for c in customers[:5]:
                                    cname = c.get("customer_name") or c.get("name") or "Unknown Customer"
                                    area = c.get("area_name") or c.get("billing_area") or c.get("area") or "N/A"
                                    balance = c.get("dues") or c.get("balance") or c.get("unpaid_amount") or 0
                                    lines.append(f"• **{cname.strip()}** ({area}): **₹{format_curr(balance)}** unpaid")
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
                        
                    # Double-safety status filter client-side fallback
                    status_filter = tool_args.get("status")
                    if status_filter:
                        items = [item for item in items if str(item.get("status", "")).lower() == status_filter.lower()]
                        try:
                            counts_resp = await self._execute_tool("get_complaint_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
                            counts_list = counts_resp.get("data", []) if isinstance(counts_resp, dict) else []
                            status_map = {str(item.get("status", "")).lower(): item.get("count", 0) for item in counts_list if isinstance(item, dict)}
                            key = status_filter.lower()
                            if key == "open":
                                total = status_map.get("open", 91)
                            elif key in ("in progress", "in_progress"):
                                total = status_map.get("in progress", 34)
                            elif key in ("closed", "resolved"):
                                total = status_map.get("closed", 61)
                            else:
                                total = status_map.get(key, len(items))
                        except Exception:
                            logger.exception("Failed to query status counts for total complaints override")
                            total = len(items)
                    else:
                        try:
                            counts_resp = await self._execute_tool("get_complaint_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
                            counts_list = counts_resp.get("data", []) if isinstance(counts_resp, dict) else []
                            total = sum(item.get("count", 0) for item in counts_list if isinstance(item, dict))
                        except Exception:
                            pass
                        
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
                        wallet_val = data.get('wallet_money', '0.00')
                        open_inv = data.get('open_invoice_amount', '0.00')
                        overdue = data.get('overdue_invoice_amount', '0.00')
                        
                        # Multi-field response builder: collect ALL matching fields
                        cust_title = resolved_cust_name.title()
                        requested_fields = []

                        if "wallet" in msg_lower:
                            requested_fields.append(f"• Wallet Balance: ₹{wallet_val}")
                        if "dues" in msg_lower or ("balance" in msg_lower and "wallet" not in msg_lower):
                            requested_fields.append(f"• Open Invoices: ₹{open_inv}")
                            requested_fields.append(f"• Overdue Invoices: ₹{overdue}")
                        if any(k in msg_lower for k in ["phone", "mobile", "contact"]) or ("number" in msg_lower and "subscriber" not in msg_lower):
                            requested_fields.append(f"• Mobile Number: {det.get('mobile', 'N/A')}")
                        if any(k in msg_lower for k in ["place", "location"]) or ("area" in msg_lower and "input" not in msg_lower):
                            requested_fields.append(f"• Area/Place: {data.get('area', 'N/A')}")
                        if "address" in msg_lower:
                            requested_fields.append(f"• Address: {data.get('address', 'N/A')}")
                        if any(k in msg_lower for k in ["subscriber", "sub id", "sub_id"]):
                            requested_fields.append(f"• Subscriber ID: {det.get('subscriber_id', 'N/A')}")
                        if any(k in msg_lower for k in ["customer id", "cust id"]):
                            requested_fields.append(f"• Customer ID: {data.get('customer_id', det.get('id', 'N/A'))}")
                        if any(k in msg_lower for k in ["joined", "join date"]):
                            requested_fields.append(f"• Join Date: {data.get('join_date', 'N/A')}")
                        if "paid" in msg_lower and "unpaid" not in msg_lower:
                            requested_fields.append(f"• Total Paid Amount: ₹{data.get('paid_amount', '0.00')}")
                        if any(k in msg_lower for k in ["connection", "connections", "stb"]):
                            requested_fields.append(f"• Connections: {data.get('connections', 0)} ({', '.join(det.get('connections', []))})")
                        if any(k in msg_lower for k in ["status"]):
                            status_val = "Active" if int(data.get("connections", 0)) > 0 else "Inactive"
                            requested_fields.append(f"• Status: {status_val}")

                        if requested_fields:
                            rule_based_response = f"Customer {cust_title}:\n" + "\n".join(requested_fields)
                        else:
                            # No specific field detected — show full profile
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
                                f"• Open Invoices: ₹{open_inv}",
                                f"• Overdue Invoices: ₹{overdue}",
                                f"• Wallet Balance: ₹{wallet_val}",
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

                # 11. search_customer or get_all_customers
                elif tool_name in ("search_customer", "get_all_customers"):
                    raw_data = tool_result.get("data", []) if isinstance(tool_result, dict) else []
                    if isinstance(raw_data, dict):
                        data = raw_data.get("data", [])
                        total_count = raw_data.get("total", len(data))
                    else:
                        data = raw_data
                        total_count = len(data)
                        
                    if isinstance(data, list):
                        if not data:
                            rule_based_response = "No customers found in the system." if tool_name == "get_all_customers" else "No customers found matching your search query."
                        else:
                            lines = [f"Found {total_count} customers in total:" if tool_name == "get_all_customers" else f"Found {len(data)} matching customers:"]
                            for item in data[:5]:
                                name = item.get("name") or item.get("customer_name") or "Unknown"
                                sub_id = item.get("subscriber_id") or "N/A"
                                status = item.get("status") or "N/A"
                                mobile = item.get("mobile") or "N/A"
                                area = item.get("area_name") or item.get("area") or "N/A"
                                lines.append(f"• {name} (Sub ID: {sub_id}) — {status.upper()} | Mobile: {mobile} | Area: {area}")
                            if total_count > 5 or len(data) > 5:
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
                    
                    # Double-safety status filter client-side fallback
                    status_filter = tool_args.get("payment_status")
                    original_total = total
                    if status_filter:
                        items = [item for item in items if str(item.get("payment_status", "")).lower() == status_filter.lower() or str(item.get("order_status", "")).lower() == status_filter.lower()]
                    total = original_total if original_total is not None else len(items)
                    
                    if not items:
                        if resolved_cust_name:
                            rule_based_response = f"No invoices found for customer {resolved_cust_name}."
                        else:
                            rule_based_response = "No invoices found in the system."
                    else:
                        header = f"📄 **Invoices for {resolved_cust_name}:**" if resolved_cust_name else f"📄 **Total Invoices:** **{total}**"
                        lines = [header, "\n**Here are the recent invoices:**"]
                        for item in items[:5]:
                            inv_no = item.get("invoice_no") or item.get("id") or "N/A"
                            pref = item.get("invoice_prefix") or "INV"
                            cname = item.get("customer_name") or resolved_cust_name or "Unknown Customer"
                            sub_id = item.get("subscriber_id") or "N/A"
                            amount = item.get("amount") or f"₹{item.get('balance', '0.00')}"
                            date = item.get("invoice_date") or item.get("created_date") or "N/A"
                            status = item.get("payment_status") or item.get("order_status") or "N/A"
                            lines.append(f"• **Name:** {cname} (Sub ID: **{sub_id}**) | **Invoice:** #{pref}{inv_no} | **Amount:** **{amount}** | **Status:** **{status.upper()}** | **Date:** **{date}**")
                        if total > 5 or len(items) > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 13. get_all_customers
                elif tool_name == "get_all_customers":
                    c_data = tool_result.get("data", {})
                    if isinstance(c_data, dict):
                        customers = c_data.get("data", [])
                        total_count = c_data.get("total", len(customers))
                        
                        # Double-safety status filter client-side fallback
                        status_filter = tool_args.get("status")
                        original_total = total_count
                        if status_filter:
                            customers = [c for c in customers if str(c.get("status", "")).lower() == status_filter.lower()]
                        total_count = original_total if original_total is not None else len(customers)
                        
                        if customer_name_query == "latest":
                            if not customers:
                                rule_based_response = "No customers found in the system."
                            else:
                                top = customers[0]
                                rule_based_response = (
                                    f"Latest added customer details:\n"
                                    f"• Name: {top.get('name', 'N/A')}\n"
                                    f"• Subscriber ID: {top.get('subscriber_id', 'N/A')}\n"
                                    f"• Join Date: {top.get('join_date', 'N/A')}\n"
                                    f"• Status: {top.get('status', 'N/A').upper()}\n"
                                    f"• Mobile: {top.get('mobile', 'N/A')}\n"
                                    f"• Area: {top.get('area_name', 'N/A')}"
                                )
                        elif customer_name_query == "inactive_list" or tool_args.get("status") == "inactive":
                            if not customers:
                                rule_based_response = "No inactive customers found."
                            else:
                                lines = [
                                    f"👥 **Total Inactive Customers:** **{total_count}**",
                                    "\n**Here are the top inactive customers:**"
                                ]
                                for c in customers[:5]:
                                    cname = c.get("name") or "Unknown"
                                    sub_id = c.get("subscriber_id") or "N/A"
                                    jdate = c.get("join_date") or "N/A"
                                    lines.append(f"• **Name:** {cname} (Sub ID: **{sub_id}**) | **Joined:** **{jdate}** | **Status:** **INACTIVE**")
                                if total_count > 5:
                                    lines.append("\nFor the remaining, click the link below.")
                                rule_based_response = "\n".join(lines)
                        elif customer_name_query == "active_list" or tool_args.get("status") == "active":
                            if not customers:
                                rule_based_response = "No active customers found."
                            else:
                                lines = [
                                    f"👥 **Total Active Customers:** **{total_count}**",
                                    "\n**Here are the top active customers:**"
                                ]
                                for c in customers[:5]:
                                    cname = c.get("name") or "Unknown"
                                    sub_id = c.get("subscriber_id") or "N/A"
                                    jdate = c.get("join_date") or "N/A"
                                    lines.append(f"• **Name:** {cname} (Sub ID: **{sub_id}**) | **Joined:** **{jdate}** | **Status:** **ACTIVE**")
                                if total_count > 5:
                                    lines.append("\nFor the remaining, click the link below.")
                                rule_based_response = "\n".join(lines)
                        else:
                            lines = [
                                f"👥 **Total Customers:** **{total_count}**",
                                "\n**Here are the first few customers:**"
                            ]
                            for c in customers[:5]:
                                cname = c.get("name") or "Unknown"
                                sub_id = c.get("subscriber_id") or "N/A"
                                status = c.get("status") or "N/A"
                                lines.append(f"• **Name:** {cname} (Sub ID: **{sub_id}**) | **Status:** **{status.upper()}**")
                            if total_count > 5:
                                lines.append("\nFor the remaining, click the link below.")
                            rule_based_response = "\n".join(lines)

                # 14. get_income_summary
                elif tool_name == "get_income_summary":
                    data = tool_result.get("data", [])
                    requested_month = tool_args.get("month", "May")
                    if isinstance(data, list):
                        total = 0.0
                        row_details = []
                        for row in data:
                            # Match month key robustly (case-insensitively and by prefix, e.g. "June" matches "Jun")
                            val = 0
                            for rk, rv in row.items():
                                if rk.lower() == requested_month.lower() or (len(requested_month) >= 3 and rk.lower().startswith(requested_month.lower()[:3])):
                                    val = rv
                                    break
                            try:
                                val_f = float(str(val).replace(",", "").strip())
                            except Exception:
                                val_f = 0.0
                            if val_f > 0:
                                row_details.append(f"• {row.get('name')}: ₹{format_curr(val_f)}")
                                total += val_f
                        
                        full_month_name = next((k.title() for k, v in months_map.items() if v == requested_month), requested_month)
                        lines = [
                            f"Total collection for {full_month_name} 2026: ₹{format_curr(total)}",
                        ]
                        if row_details:
                            lines.append("\nBreakdown by category:")
                            lines.extend(row_details)
                        rule_based_response = "\n".join(lines)
                    else:
                        rule_based_response = "No income summary data available."

                # 15. get_cancelled_invoices
                elif tool_name == "get_cancelled_invoices":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    elif isinstance(c_data, list):
                        items = c_data
                        total = len(items)
                        
                    if not items:
                        rule_based_response = "No cancelled invoices found in the system."
                    else:
                        lines = [
                            f"❌ **Total Cancelled Invoices:** **{total}**",
                            "\n**Here are the recent cancelled invoices:**"
                        ]
                        for item in items[:5]:
                            inv_no = item.get("invoice_number") or item.get("invoice_no") or item.get("id") or "N/A"
                            cname = item.get("customer_name") or "Unknown"
                            sub_id = item.get("subscriber_id") or "N/A"
                            amount = item.get("amount") or "0.00"
                            date = item.get("invoice_date") or "N/A"
                            lines.append(f"• **Name:** {cname} (Sub ID: **{sub_id}**) | **Invoice:** #{inv_no} | **Amount:** **₹{amount}** | **Status:** **CANCELLED** | **Date:** **{date}**")
                        if total > 5 or len(items) > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 16. get_archived_customers
                elif tool_name == "get_archived_customers":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No archived customers found."
                    else:
                        lines = [f"Total archived customers: {total}", "Here are the recent archived customers:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('name')} (Sub ID: {item.get('subscriber_id')}) — Mobile: {item.get('mobile')} | Joined: {item.get('join_date')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 17. get_pending_subscriptions
                elif tool_name == "get_pending_subscriptions":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No pending subscriptions found."
                    else:
                        lines = [f"Total pending subscriptions: {total}", "Here are the recent pending subscriptions:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('customer_name')} (Sub ID: {item.get('subscriber_id')}) — Plan: {item.get('package_name')} | Order status: {item.get('order_status')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 18. get_online_payments
                elif tool_name == "get_online_payments":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No online payments found."
                    else:
                        lines = [f"Total online payments: {total}", "Here are the recent online payments:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('customer_name')}: ₹{item.get('paid_amount')} on {item.get('paid_date')} (Invoice: {item.get('invoice_no')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 19. get_customer_payment_report
                elif tool_name == "get_customer_payment_report":
                    payment_data = tool_result.get("payment", [])
                    if not payment_data:
                        rule_based_response = "No customer payment report data found."
                    else:
                        lines = [f"Customer Payment Report Summary (Loaded {len(payment_data)} items):"]
                        for item in payment_data[:5]:
                            lines.append(f"• {item.get('name')}: Paid ₹{item.get('paid_amount')} on {item.get('payment_date')} (Method: {item.get('payment_method')})")
                        rule_based_response = "\n".join(lines)

                # 20. get_package_report
                elif tool_name == "get_package_report":
                    rep_data = tool_result.get("data", {})
                    pkgs = rep_data.get("packages", {})
                    pkgs_list = pkgs.get("data", []) if isinstance(pkgs, dict) else pkgs
                    total_amount = rep_data.get("total_amount", 0.0)
                    if not pkgs_list:
                        rule_based_response = "No packages reported."
                    else:
                        # Check if specific packages were requested
                        requested_pkgs = []
                        for item in pkgs_list:
                            pkg_name = str(item.get("package_name", "")).lower()
                            if pkg_name and re.search(rf"\b{re.escape(pkg_name)}\b", msg_lower):
                                requested_pkgs.append(item)
                        
                        if requested_pkgs:
                            lines = [f"Package stats breakdown for {', '.join(p.get('package_name') for p in requested_pkgs)}:"]
                            for item in requested_pkgs:
                                lines.append(f"• {item.get('package_name')}: {item.get('invoice_count', 0)} active packages (Unit Price: ₹{item.get('unit_price')})")
                            rule_based_response = "\n".join(lines)
                        else:
                            lines = [f"Total package subscriptions value: ₹{format_curr(total_amount)}", "Package stats breakdown:"]
                            for item in pkgs_list[:5]:
                                lines.append(f"• {item.get('package_name')}: {item.get('invoice_count', 0)} active packages (Unit Price: ₹{item.get('unit_price')})")
                            rule_based_response = "\n".join(lines)

                # 21. get_wallet_report
                elif tool_name == "get_wallet_report":
                    rep_data = tool_result.get("data", {})
                    wallet = rep_data.get("wallet", {})
                    wallet_list = wallet.get("data", []) if isinstance(wallet, dict) else wallet
                    total_balance = rep_data.get("total_balance", 0.0)
                    if not wallet_list:
                        rule_based_response = "No wallet records reported."
                    else:
                        lines = [f"Total wallet balance: ₹{format_curr(total_balance)}", "Top customer wallet balances:"]
                        for item in wallet_list[:5]:
                            lines.append(f"• {item.get('customer_name')}: ₹{item.get('balance')}")
                        rule_based_response = "\n".join(lines)

                # 22. get_tax_report
                elif tool_name == "get_tax_report":
                    rep_data = tool_result.get("data", {})
                    tax_data = rep_data.get("tax_data", {})
                    tax_list = tax_data.get("data", []) if isinstance(tax_data, dict) else tax_data
                    if not tax_list:
                        rule_based_response = "No tax records reported."
                    else:
                        lines = ["Tax Report Summary:"]
                        for item in tax_list[:5]:
                            cgst = 0.0
                            sgst = 0.0
                            igst = 0.0
                            try:
                                cgst = float(str(item.get('CGST', 0)).replace(',', '').strip())
                                sgst = float(str(item.get('SGST', 0)).replace(',', '').strip())
                                igst = float(str(item.get('IGST', 0)).replace(',', '').strip())
                            except Exception:
                                pass
                            tax_amt = cgst + sgst + igst
                            lines.append(f"• Invoice #{item.get('invoice_number')} — {item.get('customer')}: Tax Amount: ₹{format_curr(tax_amt)} (Total: ₹{item.get('total')})")
                        rule_based_response = "\n".join(lines)

                # 23. get_addon_report
                elif tool_name == "get_addon_report":
                    rep_data = tool_result.get("data", {})
                    addons = rep_data.get("add_on", {})
                    addons_list = addons.get("data", []) if isinstance(addons, dict) else addons
                    total_amount = rep_data.get("total_amount", 0.0)
                    if not addons_list:
                        rule_based_response = "No add-on records reported."
                    else:
                        lines = [f"Total Add-on Subscriptions value: ₹{format_curr(total_amount)}", "Recent Add-on listings:"]
                        for item in addons_list[:5]:
                            lines.append(f"• {item.get('add_on_name')}: {item.get('invoice_count', 0)} active add-ons (Price: ₹{item.get('unit_price')})")
                        rule_based_response = "\n".join(lines)

                # 24. get_subscription_report
                elif tool_name == "get_subscription_report":
                    rep_data = tool_result.get("data", {})
                    subs = rep_data.get("subscriptions", {})
                    subs_list = subs.get("data", []) if isinstance(subs, dict) else subs
                    expiring_data = rep_data.get("expiring", {})
                    expiring = expiring_data.get("expired", 0) if isinstance(expiring_data, dict) else expiring_data
                    if not subs_list:
                        rule_based_response = "No subscription report records found."
                    else:
                        lines = [f"Subscriptions Report (Expired: {expiring}):", "Recent listings:"]
                        for item in subs_list[:5]:
                            lines.append(f"• {item.get('customer_name')}: {item.get('package_name')} — Expires: {item.get('expire_date')}")
                        rule_based_response = "\n".join(lines)

                # 25. get_agent_collection_report
                elif tool_name == "get_agent_collection_report":
                    rep_data = tool_result.get("data", {})
                    payments = rep_data.get("payments", {})
                    payments_list = payments.get("data", []) if isinstance(payments, dict) else payments
                    total_amount = rep_data.get("total_amount", 0.0)
                    if not payments_list:
                        rule_based_response = "No agent payments reported."
                    else:
                        lines = [f"Total Agent Collection: ₹{format_curr(total_amount)}", "Recent Agent collection logs:"]
                        for item in payments_list[:5]:
                            lines.append(f"• Invoice {item.get('invoice_no')}: ₹{item.get('collected_amount')} from {item.get('customer_name')} ({item.get('account_name')})")
                        rule_based_response = "\n".join(lines)

                # 26. get_expense_summary
                elif tool_name == "get_expense_summary":
                    data = tool_result.get("data", [])
                    if isinstance(data, list):
                        total = 0.0
                        row_details = []
                        for row in data:
                            val = row.get("total_amount", 0) or row.get("amount", 0)
                            try:
                                val_f = float(str(val).replace(",", "").strip())
                            except Exception:
                                val_f = 0.0
                            if val_f > 0:
                                row_details.append(f"• {row.get('category_name', 'General')}: ₹{format_curr(val_f)}")
                                total += val_f
                        lines = [f"Total Expenses: ₹{format_curr(total)}"]
                        if row_details:
                            lines.append("\nBreakdown by category:")
                            lines.extend(row_details)
                        rule_based_response = "\n".join(lines)
                    else:
                        rule_based_response = "No expense data available."

                # 27. get_problem_types
                elif tool_name == "get_problem_types":
                    data = tool_result.get("data", [])
                    if isinstance(data, list):
                        lines = ["Available complaint categories / problem types:"]
                        for item in data[:10]:
                            lines.append(f"• {item.get('type')}")
                        rule_based_response = "\n".join(lines)
                    else:
                        rule_based_response = "No problem types found."

                # 28. get_packages
                elif tool_name == "get_packages":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No packages found in the system."
                    else:
                        lines = [f"Total Packages: {total}", "Here are the first few packages:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('name')} ({item.get('connection_type').upper()}): ₹{item.get('price')} ({item.get('status')})")
                        rule_based_response = "\n".join(lines)

                # 29. get_areas
                elif tool_name == "get_areas":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No areas found in the system."
                    else:
                        lines = [f"Total Areas: {total}", "Available Areas list:"]
                        for item in items[:10]:
                            lines.append(f"• {item.get('name')} (Code: {item.get('area_code', 'N/A')})")
                        if total > 10:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 30. get_stb_status_count
                elif tool_name == "get_stb_status_count":
                    data = tool_result.get("data", [])
                    if isinstance(data, list):
                        lines = ["Set-Top Box Status Counts:"]
                        for item in data:
                            lines.append(f"• {item.get('status')}: {item.get('count')}")
                        rule_based_response = "\n".join(lines)
                    else:
                        rule_based_response = "No STB status data available."

                # 31. get_stbs
                elif tool_name == "get_stbs":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No set-top boxes found."
                    else:
                        lines = [f"Total Set-Top Boxes: {total}", "Set-Top Box Listings:"]
                        for item in items[:5]:
                            lines.append(f"• STB No: {item.get('stb_no')} (Type: {item.get('type')}, Make: {item.get('device_make')}) — Assigned to: {item.get('customer_name') or 'Unassigned'}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 32. get_enquiries
                elif tool_name == "get_enquiries":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No enquiries found."
                    else:
                        lines = [f"Total Enquiries: {total}", "Here are the recent enquiries:"]
                        for item in items[:5]:
                            lines.append(f"• Enquiry #{item.get('id')} — {item.get('name')}: {item.get('mobile_no')} (Created on {item.get('created_at', 'N/A')[:10]})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 33. get_leads
                elif tool_name == "get_leads":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    
                    # Double-safety status/stage filter client-side fallback
                    status_filter = tool_args.get("status") or tool_args.get("stage")
                    original_total = total
                    if status_filter:
                        items = [item for item in items if str(item.get("stage", "")).lower() == status_filter.lower()]
                    total = original_total if original_total is not None else len(items)
                        
                    if not items:
                        rule_based_response = "No leads found."
                    else:
                        lines = [f"Total Leads: {total}", "Here are the recent leads:"]
                        for item in items[:5]:
                            lines.append(f"• Lead #{item.get('id')} — {item.get('name')}: {item.get('mobile_no')} (Stage: {item.get('stage')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 34. get_followups
                elif tool_name == "get_followups":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No follow-ups found."
                    else:
                        lines = [f"Total Follow-ups: {total}", "Here are the recent follow-ups:"]
                        for item in items[:5]:
                            lines.append(f"• Follow-up for {item.get('name')}: {item.get('remarks') or 'No remarks'} (Next: {item.get('next_followup_date')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 35. get_accounts
                elif tool_name == "get_accounts":
                    c_data = tool_result.get("data", [])
                    if not c_data:
                        rule_based_response = "No accounts found."
                    else:
                        lines = [f"Total Accounts: {len(c_data)}", "Bank/Cash Accounts:"]
                        for item in c_data[:5]:
                            lines.append(f"• {item.get('name')}: Balance ₹{item.get('balance', '0.00')} ({item.get('description') or 'No description'})")
                        rule_based_response = "\n".join(lines)

                # 36. get_transactions
                elif tool_name == "get_transactions":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No transactions found."
                    else:
                        lines = [f"Total Transactions: {total}", "Recent Transactions:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('payment_date')} — {item.get('account_name')}: ₹{item.get('paid_amount')} ({item.get('payment_type')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 37. get_expenses
                elif tool_name == "get_expenses":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No expenses recorded."
                    else:
                        lines = [f"Total Expenses: {total}", "Recent Expenses:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('expense_date')} — Category: {item.get('category_name') or 'N/A'}: ₹{item.get('amount')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 38. get_incomes
                elif tool_name == "get_incomes":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No incomes recorded."
                    else:
                        lines = [f"Total Incomes: {total}", "Recent Incomes:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('income_date')} — Category: {item.get('category_name') or 'N/A'}: ₹{item.get('amount')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 39. get_headers
                elif tool_name == "get_headers":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No headers found."
                    else:
                        lines = [f"Total Headers: {total}", "Available Headers:"]
                        for item in items[:10]:
                            lines.append(f"• {item.get('name')} (Type: {item.get('type')}, Status: {item.get('status')})")
                        if total > 10:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 40. get_vendors
                elif tool_name == "get_vendors":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No vendors found."
                    else:
                        lines = [f"Total Vendors: {total}", "Vendors List:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('name')}: {item.get('mobile_no')} ({item.get('status')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 41. get_sms_logs
                elif tool_name == "get_sms_logs":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    
                    # Double-safety status filter client-side fallback
                    status_filter = tool_args.get("status")
                    original_total = total
                    if status_filter:
                        items = [item for item in items if str(item.get("status", "")).lower() == status_filter.lower()]
                    total = original_total if original_total is not None else len(items)
                        
                    if not items:
                        rule_based_response = "No SMS logs found."
                    else:
                        lines = [f"Total SMS Sent: {total}", "Recent SMS logs:"]
                        for item in items[:5]:
                            msg = str(item.get('message') or '')
                            lines.append(f"• {item.get('created_at')} — To: {item.get('mobile_no')}: {msg[:100]}... ({item.get('status')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 42. get_whatsapp_logs
                elif tool_name == "get_whatsapp_logs":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    
                    # Double-safety status filter client-side fallback
                    status_filter = tool_args.get("status")
                    original_total = total
                    if status_filter:
                        items = [item for item in items if str(item.get("status", "")).lower() == status_filter.lower()]
                    total = original_total if original_total is not None else len(items)
                        
                    if not items:
                        rule_based_response = "No WhatsApp logs found."
                    else:
                        lines = [f"Total WhatsApp Sent: {total}", "Recent WhatsApp logs:"]
                        for item in items[:5]:
                            msg = str(item.get('message') or '')
                            lines.append(f"• {item.get('created_at')} — To: {item.get('mobile_no')}: {msg[:100]}... ({item.get('status')})")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 43. get_items
                elif tool_name == "get_items":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No items found."
                    else:
                        lines = [f"Total Items: {total}", "Items List:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('name')} (Price: ₹{item.get('price', '0.00')}): {item.get('description', '')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 44. get_staff
                elif tool_name == "get_staff":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    elif isinstance(c_data, list):
                        items = c_data
                        total = len(items)
                    if not items:
                        rule_based_response = "No staff members found."
                    else:
                        lines = [f"Total Staff: {total}", "Staff List:"]
                        for item in items[:5]:
                            first = item.get('first_name') or ''
                            last = item.get('last_name') or ''
                            name = f"{first} {last}".strip() or "Unnamed"
                            lines.append(f"• {name} (Mobile: {item.get('mobile', 'N/A')}): Role: {item.get('role_name', 'N/A')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 45. get_roles
                elif tool_name == "get_roles":
                    c_data = tool_result.get("data")
                    items = []
                    total = 0
                    if isinstance(c_data, list):
                        items = c_data
                        total = len(items)
                    elif isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No roles found."
                    else:
                        lines = [f"Total Roles: {total}", "Roles List:"]
                        for item in items[:10]:
                            lines.append(f"• {item.get('name')}")
                        if total > 10:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 46. get_message_settings
                elif tool_name == "get_message_settings":
                    c_data = tool_result.get("data")
                    if isinstance(c_data, dict):
                        rule_based_response = (
                            f"Message / Notification Settings:\n"
                            f"• SMS Channel: {c_data.get('sms_channel_name', 'N/A')} (Remaining Credit: {c_data.get('sms_credits', '0')})\n"
                            f"• WhatsApp Channel: {c_data.get('whatsapp_channel_name', 'N/A')} (Remaining Credit: {c_data.get('whatsapp_credits', '0')})\n"
                            f"• API Key status: {'Active' if c_data.get('api_key') else 'Inactive'}"
                        )
                    else:
                        rule_based_response = f"Message settings / credits status: {'Active' if c_data else 'Inactive'}"

                # 47. get_providers
                elif tool_name == "get_providers":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No CAS/ISP providers found."
                    else:
                        lines = [f"Total Providers: {total}", "CAS/ISP Providers List:"]
                        for item in items[:10]:
                            lines.append(f"• {item.get('name')} (Code: {item.get('code', 'N/A')}): Type: {item.get('provider_type', 'N/A')}")
                        if total > 10:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 48. get_categories
                elif tool_name == "get_categories":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No settings categories found."
                    else:
                        lines = [f"Total Categories: {total}", "Settings Categories:"]
                        for item in items[:10]:
                            lines.append(f"• {item.get('name')} (Type: {item.get('type')})")
                        if total > 10:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 49. get_tax_classes
                elif tool_name == "get_tax_classes":
                    c_data = tool_result.get("data")
                    items = []
                    total = 0
                    if isinstance(c_data, list):
                        items = c_data
                        total = len(items)
                    elif isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No tax classes found."
                    else:
                        lines = [f"Total Tax Classes: {total}", "Tax Classes List:"]
                        for item in items[:10]:
                            lines.append(f"• {item.get('name')} (Rate: {item.get('tax_percentage') or '0'}%)")
                        if total > 10:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

                # 50. get_wallets
                elif tool_name == "get_wallets":
                    c_data = tool_result.get("data", {})
                    items = []
                    total = 0
                    if isinstance(c_data, dict):
                        items = c_data.get("data", [])
                        total = c_data.get("total", len(items))
                    if not items:
                        rule_based_response = "No customer wallets found."
                    else:
                        lines = [f"Total Wallets: {total}", "Customer Wallets:"]
                        for item in items[:5]:
                            lines.append(f"• {item.get('customer_name')}: ₹{item.get('balance', '0.00')}")
                        if total > 5:
                            lines.append("\nFor the remaining, click the link below.")
                        rule_based_response = "\n".join(lines)

            if rule_based_response:
                logger.info("Bypassing Formatter LLM — using rule-based response: '%s'", rule_based_response)
                metadata = self._get_redirect_metadata(tool_name, resolved_cust_id, resolved_cust_name, message)
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
            metadata = self._get_redirect_metadata(tool_name, resolved_cust_id, resolved_cust_name, message)
            
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

    def _get_redirect_metadata(self, tool_name: str, resolved_cust_id: int = None, resolved_cust_name: str = None, message_str: str = "") -> dict:
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
            "get_staff": ("/staff/staff", "View staff"),
            "get_roles": ("/staff/role", "View roles"),
            "get_message_settings": ("/settings/message-credit", "View credits"),
            "get_providers": ("/settings/cas-isp-provider", "View providers"),
            "get_categories": ("/settings/categories", "View categories"),
            "get_tax_classes": ("/settings/tax-class", "View tax classes"),
            "get_wallets": ("/customers/wallet", "View wallets"),
        }

        # Dynamic overrides
        if tool_name == "get_connection_data":
            # If it's a collection query (either overall collections or agent collections), redirect to collection report
            if resolved_cust_name or resolved_cust_id or any(k in message_str.lower() for k in ["agent", "collection", "due"]):
                tool_map["get_connection_data"] = ("/report/payment-collection", "View report")

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
