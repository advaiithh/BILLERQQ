import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List

logger = logging.getLogger("billerq-templates")

def format_curr(val):
    try:
        if isinstance(val, (int, float)):
            return f"{val:,.2f}"
        cleaned = str(val).replace(",", "").strip()
        return f"{float(cleaned):,.2f}"
    except (ValueError, TypeError):
        return str(val)

async def build_template_response(
    tool_name: str,
    tool_args: dict,
    tool_result: Any,
    message: str,
    resolved_cust_name: Optional[str] = None,
    resolved_cust_id: Optional[int] = None,
    resolved_agent_id: Optional[int] = None,
    billerq_token: str = "",
    billerq_api_url: str = "",
    billerq_user_role: Optional[int] = None,
    agent = None
) -> Optional[str]:
    """Generates structured response text from tool results using Python templates.
    
    If the response is successfully generated via Python templates, returns the response text.
    If formatting requires LLM reasoning (or is not template-supported), returns None.
    """
    msg_lower = message.lower().strip()
    
    # Check for guide response first
    if tool_name == "show_guide" and agent:
        category = tool_args.get("category", "billerq")
        if hasattr(agent, "_get_guide_response"):
            return agent._get_guide_response(category)

    if not isinstance(tool_result, dict):
        return None
        
    if "error" in tool_result:
        # Let the Formatter LLM handle formatting of API errors dynamically
        return None

    customer_name_query = tool_args.get("customer_name") or tool_args.get("name")
    
    # 1. get_customer_status_count
    if tool_name == "get_customer_status_count":
        if any(k in msg_lower for k in ["how many", "count", "number of", "total"]):
            c_data = tool_result.get("data") if isinstance(tool_result, dict) else []
            active_count = 0
            inactive_count = 0
            total_count = 0
            if isinstance(c_data, list):
                active_count = next((c.get("count") for c in c_data if c.get("status") == "Active"), 0)
                inactive_count = next((c.get("count") for c in c_data if c.get("status") == "Inactive"), 0)
                total_count = next((c.get("count") for c in c_data if c.get("status") == "Total"), 0)
            
            archived_count = 0
            if agent:
                try:
                    archived_resp = await agent._execute_tool("get_archived_customers", {}, billerq_token, billerq_api_url, billerq_user_role)
                    archived_raw = archived_resp.get("data", []) if isinstance(archived_resp, dict) else []
                    if isinstance(archived_raw, dict):
                        archived_count = archived_raw.get("total", len(archived_raw.get("data", [])))
                    elif isinstance(archived_raw, list):
                        archived_count = len(archived_raw)
                except Exception:
                    pass
                    
            return (
                f"📊 **Customer Metrics & Counts Summary:**\n"
                f"• **Total Customers:** **{total_count:,}**\n"
                f"• **Active Customers:** **{active_count:,}** 🟢\n"
                f"• **Inactive Customers:** **{inactive_count:,}** 🔴\n"
                f"• **Archived Customers:** **{archived_count:,}** ⚠️"
            )
        else:
            status_f = "inactive" if "inactive" in msg_lower else "archived" if "archived" in msg_lower else "active"
            if agent and hasattr(agent, "_get_customer_dashboard_response"):
                return await agent._get_customer_dashboard_response(billerq_token, billerq_api_url, billerq_user_role, status_f)

    # 2. get_connection_data
    elif tool_name == "get_connection_data":
        conn_data = tool_result.get("data", {})
        if conn_data:
            if customer_name_query == "this_month_due":
                month_meter = conn_data.get("collection_this_month_meter", {})
                return f"📉 **Dues Summary (This Month)**\n• Total dues: **₹{month_meter.get('dues', '0.00')}**\n• Total invoiced: **₹{month_meter.get('total_amount', '0.00')}**"
            elif customer_name_query == "this_month_collection":
                month_meter = conn_data.get("collection_this_month_meter", {})
                return f"💰 **Collection Summary (This Month)**\n• Total collected: **₹{month_meter.get('collection', '0.00')}**\n• Progress: **{month_meter.get('percentage', '0')}%** collected"
            elif any(k in msg_lower for k in ["agent", "agents", "collected by", "collections by", "leaderboard"]) or (customer_name_query and customer_name_query not in ("agent_collection_all", "this_month_due", "this_month_collection")):
                agent_list = conn_data.get("agent_collection", [])
                
                specific_agent = None
                if customer_name_query and customer_name_query not in ("agent_collection_all",):
                    for ag in agent_list:
                        norm_query = re.sub(r"[^a-zA-Z0-9]", "", customer_name_query.lower())
                        norm_agent_name = re.sub(r"[^a-zA-Z0-9]", "", str(ag.get("name", "")).lower())
                        if norm_query and norm_agent_name and (norm_query in norm_agent_name or norm_agent_name in norm_query):
                            specific_agent = ag
                            break
                            
                if specific_agent:
                    return (
                        f"👤 **Collection Details for Agent:** **{specific_agent.get('name')}**\n"
                        f"• Collected Today: **₹{specific_agent.get('today', '0.00')}**\n"
                        f"• Collected This Month: **₹{specific_agent.get('income', '0.00')}**\n"
                        f"• Progress/Status: **{specific_agent.get('time', 'N/A')}** (**{specific_agent.get('progress', 'N/A')}**)"
                    )
                elif not agent_list:
                    return "No agent collection data available."
                else:
                    def get_income(ag):
                        try:
                            return float(str(ag.get("income", 0)).replace(",", "").strip())
                        except Exception:
                            return 0.0
                    sorted_agents = sorted(agent_list, key=get_income, reverse=True)
                    total_agent_collection = sum(get_income(ag) for ag in sorted_agents)
                    
                    lines = [
                        f"💰 **Total Agent Collection (This Month):** **₹{format_curr(total_agent_collection)}**",
                        "\n**Collections by Agent (This Month):**"
                    ]
                    for ag in sorted_agents:
                        aname = ag.get('name') or f"Agent #{ag.get('agent_id')}"
                        lines.append(f"• **{aname}**: **₹{ag.get('income', '0.00')}** (Today: **₹{ag.get('today', '0.00')}**)")
                    return "\n".join(lines)
            else:
                total_conn = conn_data.get("total_connections") or conn_data.get("total", 0)
                active_conn = conn_data.get("active_connections") or conn_data.get("active", 0)
                inactive_conn = conn_data.get("inactive_connections") or conn_data.get("inactive", 0)
                return f"📊 **Connection Statistics**\n• Total Connections: **{total_conn}**\n• Active Connections: **{active_conn}**\n• Inactive Connections: **{inactive_conn}**"

    # 3. get_payment_due_data
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
            return "No customers with due payments found."
        else:
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
                lines.append(
                    f"👤 **{cname.strip()}** (ID: `{sub_id}`)\n"
                    f"• **Dues:** **₹{bal}** 🔴\n"
                    f"• **Area:** {area}\n"
                )
            
            lines.append("\n📊 **Dues Metrics Summary:**")
            lines.append(f"- **Unpaid Customers Listed:** {min(5, total_count)} 🔴")
            lines.append(f"- **Total Outstanding Due:** **₹{format_curr(total_due)}**")
            if total_count > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 4. get_recurring_data
    elif tool_name == "get_recurring_data":
        c_data = tool_result.get("data", {})
        items = []
        total = 0
        if isinstance(c_data, dict):
            items = c_data.get("data", [])
            total = c_data.get("total", len(items))
        elif isinstance(c_data, list):
            items = c_data
            total = len(items)
        
        filter_name = resolved_cust_name or customer_name_query
        if filter_name:
            filter_name_lower = str(filter_name).lower().strip()
            filter_name_norm = re.sub(r'\s+', '', filter_name_lower)
            is_digit = filter_name_lower.isdigit()
            filtered = []
            for item in items:
                cust_val = str(item.get("customer_name") or item.get("customer") or "").lower()
                sub_val = str(item.get("subscriber_id") or "").lower()
                cust_norm = re.sub(r'\s+', '', cust_val)
                sub_norm = re.sub(r'\s+', '', sub_val)
                if filter_name_norm in cust_norm or filter_name_norm in sub_norm:
                    filtered.append(item)
                elif is_digit and filter_name_lower in str(item.get("id", "")):
                    filtered.append(item)
            items = filtered
            total = len(items)
        
        if not items:
            if filter_name:
                return f"No recurring invoice profiles found for '{filter_name}'."
            else:
                return "No recurring invoice profiles found."
        else:
            lines = [f"📊 **Recurring Invoices List ({total} total):**", ""]
            for item in items[:5]:
                cust = item.get("customer_name") or item.get("customer") or "Unknown"
                sub_id = item.get("subscriber_id") or "N/A"
                pkg = item.get("package_name") or "N/A"
                start = item.get("start_date") or "N/A"
                billing_type = item.get("type") or "Master"
                lines.append(
                    f"👤 **{cust.strip()}** (ID: `{sub_id}`)\n"
                    f"• **Package:** {pkg}\n"
                    f"• **Billing Type:** {billing_type}\n"
                    f"• **Start Date:** {start}\n"
                )
            
            lines.append("\n📊 **Recurring Metrics Summary:**")
            lines.append(f"- **Recurring Profiles Listed:** {min(5, total)}")
            lines.append(f"- **Total Recurring Profiles:** {total}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 5. get_recent_payments
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
            return "No recent payments found in the system."
        else:
            lines = [
                f"💳 **Recent Payments Summary** (Total: {total:,} payments)\n",
                "Here are the top 5 recent payments:\n"
            ]
            for item in items[:5]:
                cname = item.get("name") or item.get("customer_name") or "Unknown Customer"
                sub_id = item.get("subscriber_id") or "N/A"
                amount = item.get("amount") or item.get("paid_amount") or 0
                date = item.get("payment_date") or item.get("created_at") or "N/A"
                method = item.get("payment_method") or item.get("method") or "N/A"
                inv = item.get("invoice_no") or "N/A"
                lines.append(
                    f"💰 **Payment by {cname.strip()}** (ID: `{sub_id}`)\n"
                    f"• **Invoice:** #{inv}\n"
                    f"• **Amount:** ₹{format_curr(amount)} 🟢\n"
                    f"• **Method:** {method}\n"
                    f"• **Date:** {date}\n"
                )
            
            total_sum = 0.0
            for item in items:
                try:
                    total_sum += float(str(item.get("amount") or item.get("paid_amount") or 0).replace(",", "").strip())
                except Exception:
                    pass
            lines.append("\n📊 **Payments Metrics Summary:**")
            lines.append(f"- **Total Collected Amount:** **₹{format_curr(total_sum)}** 🟢")
            lines.append(f"- **Total Transactions:** {total}")
            if total > 5:
                remaining = total - 5
                lines.append(f"---\n💡 *For the remaining {remaining:,} payments, click the redirection button below.*")
            return "\n".join(lines)

    # 6. get_unpaid_customers
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
                return "No unpaid customers found in the system."
            else:
                if any(k in msg_lower for k in ["most balance", "highest dues", "most unpaid", "highest balance", "maximum dues"]):
                    top_cust = customers[0]
                    cname = top_cust.get("customer_name") or top_cust.get("name") or "Unknown Customer"
                    area = top_cust.get("area_name") or top_cust.get("billing_area") or top_cust.get("area") or "N/A"
                    balance = top_cust.get("dues") or top_cust.get("balance") or top_cust.get("unpaid_amount") or 0
                    return f"The customer with the highest dues/balance is **{cname.strip()}** (**{area}**) with an unpaid balance of **₹{format_curr(balance)}**."
                else:
                    lines = [
                        f"📉 **Total Unpaid Amount:** **₹{format_curr(total_amount)}**",
                        f"There are **{total_count}** unpaid customers in total.",
                        "\n**Here are the top 5 unpaid customers:**"
                    ]
                    for c in customers[:5]:
                        cname = c.get("customer_name") or c.get("name") or "Unknown Customer"
                        sub_id = c.get("subscriber_id") or "N/A"
                        area = c.get("area_name") or c.get("billing_area") or c.get("area") or "N/A"
                        balance = c.get("dues") or c.get("balance") or c.get("unpaid_amount") or 0
                        lines.append(
                            f"👤 **{cname.strip()}** (ID: `{sub_id}`)\n"
                            f"• **Unpaid Balance:** **₹{format_curr(balance)}** 🔴\n"
                            f"• **Area:** {area}\n"
                        )
                    
                    lines.append("\n📊 **Unpaid Metrics Summary:**")
                    lines.append(f"- **Unpaid Customers Listed:** {min(5, total_count)} 🔴")
                    lines.append(f"- **Total Outstanding Balance:** **₹{format_curr(total_amount)}**")
                    if len(customers) > 5:
                        lines.append("\nFor the remaining, click the link below.")
                    return "\n".join(lines)

    # 7. overdues / overdue_list
    elif tool_name in ("get_overdues", "get_overdue_list", "overdues", "overdue_list"):
        overdue_data = tool_result.get("data", {})
        if isinstance(overdue_data, dict):
            count = overdue_data.get("count") or overdue_data.get("total") or len(overdue_data.get("data", []))
            items = overdue_data.get("data", [])
            if not items:
                return "No overdue payments found."
            else:
                lines = [
                    f"Total overdue cases: {count}",
                    "\nHere are the top overdue cases:"
                ]
                for item in items[:5]:
                    cname = item.get("name") or "Unknown"
                    date = item.get("next_followup_date") or item.get("next_followup") or "N/A"
                    assigned = item.get("assigned_to") or "Unassigned"
                    lines.append(f"• **{cname}**\n  - **Next Follow-up:** {date}\n  - **Assigned to:** {assigned}")
                if count > 5:
                    lines.append("\nFor the remaining, click the link below.")
                return "\n".join(lines)

    # 8. get_complaint_status_count / get_complaints (dashboard delegation)
    elif tool_name in ("get_complaint_status_count", "get_complaints") and agent:
        status_f = tool_args.get("status") or ("open" if "open" in msg_lower else "in progress" if "progress" in msg_lower else "closed" if ("closed" in msg_lower or "resolved" in msg_lower) else None)
        cust_f = resolved_cust_name or customer_name_query
        
        prob_f = None
        if "billing" in msg_lower:
            prob_f = "billing"
        elif "technical" in msg_lower:
            prob_f = "technical"
        elif "signal" in msg_lower:
            prob_f = "signal"
        elif "internet" in msg_lower:
            prob_f = "internet"
            
        area_f = None
        area_match = re.search(r"\b(?:area|place|location|in|at)\s+([a-zA-Z0-9\s]+)", msg_lower)
        if area_match:
            candidate_area = area_match.group(1).strip()
            if candidate_area and candidate_area not in ["customer", "agent", "user", "complaint", "list", "show"]:
                area_f = candidate_area
                
        if tool_name == "get_complaint_status_count" and hasattr(agent, "_get_complaints_dashboard_response"):
            return await agent._get_complaints_dashboard_response(billerq_token, billerq_api_url, billerq_user_role, status_filter=status_f)
        elif tool_name == "get_complaints" and hasattr(agent, "_get_complaints_dashboard_response"):
            return await agent._get_complaints_dashboard_response(
                billerq_token, billerq_api_url, billerq_user_role,
                status_filter=status_f,
                customer_name_filter=cust_f,
                problem_type_filter=prob_f,
                area_filter=area_f
            )

    # 9. get_dashboard_data
    elif tool_name == "get_dashboard_data":
        data = tool_result.get("data", {})
        if isinstance(data, dict):
            comp = data.get("complaints", {})
            subs = data.get("subscriptions", {})
            pay = data.get("payment_collection", {})
            cond = data.get("check_condition", {})
            
            total_customers = cond.get('customers', 0)
            if agent:
                try:
                    sc_resp = await agent._execute_tool("get_customer_status_count", {}, billerq_token, billerq_api_url, billerq_user_role)
                    sc_data = sc_resp.get("data", []) if isinstance(sc_resp, dict) else []
                    for sc_item in sc_data:
                        if sc_item.get("status") == "Total":
                            total_customers = sc_item.get("count", total_customers)
                except Exception:
                    pass

            if "this month" in msg_lower and "collection" in msg_lower:
                return f"Total collection for this month: ₹{pay.get('this_month', '0.00')}"
            elif "today" in msg_lower and "collection" in msg_lower:
                return f"Total collection for today: ₹{pay.get('today', '0.00')}"
            elif "outstanding" in msg_lower or "dues" in msg_lower:
                return f"Total outstanding dues: ₹{pay.get('dues', '0.00')}"
            elif "wallet" in msg_lower:
                return f"Total wallet balance: ₹{pay.get('wallet_amount', '0.00')}"
            else:
                lines = [
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
                    f"- **Expiring in 5 Days:** {subs.get('in_five_days', 0)}",
                    "",
                    "🛠️ **Complaints Status:**",
                    f"- **Unresolved Complaints:** {comp.get('un_resolved', 0)} 🔴",
                    f"- **In Process:** {comp.get('in_process', 0)} 🟠",
                    f"- **Resolved:** {comp.get('resolved', 0)} 🟢"
                ]
                return "\n".join(lines)

    # 10. get_customer_profile
    elif tool_name == "get_customer_profile" and resolved_cust_name:
        data = tool_result.get("data", {})
        if isinstance(data, dict):
            det = data.get("customer_details", {})
            wallet_val = data.get('wallet_money', '0.00')
            open_inv = data.get('open_invoice_amount', '0.00')
            overdue = data.get('overdue_invoice_amount', '0.00')
            
            requested_details = []
            if "wallet" in msg_lower:
                requested_details.append(f"- **Wallet Balance:** **₹{wallet_val}**")
            if "dues" in msg_lower or "balance" in msg_lower:
                requested_details.append(f"- **Open Invoices:** **₹{open_inv}**\n- **Overdue Invoices:** **₹{overdue}**")
            if any(k in msg_lower for k in ["phone", "number", "mobile", "contact"]):
                requested_details.append(f"- **Mobile Number:** **{det.get('mobile', 'N/A')}**")
            if any(k in msg_lower for k in ["place", "area", "location"]):
                requested_details.append(f"- **Area/Place:** **{data.get('area', 'N/A')}**")
            if "address" in msg_lower:
                requested_details.append(f"- **Address:** **{data.get('address', 'N/A')}**")
            if any(k in msg_lower for k in ["subscriber", "sub id", "sub_id", "customer id", "customer_id", "subscriber id"]):
                requested_details.append(f"- **Subscriber ID:** **{det.get('subscriber_id', 'N/A')}**")
            if any(k in msg_lower for k in ["joined", "join date"]):
                requested_details.append(f"- **Join Date:** **{data.get('join_date', 'N/A')}**")
            if "paid" in msg_lower:
                requested_details.append(f"- **Total Paid Amount:** **₹{data.get('paid_amount', '0.00')}**")
            if any(k in msg_lower for k in ["connection", "connections", "stb"]):
                requested_details.append(f"- **Connections:** **{data.get('connections', 0)}** ({', '.join(det.get('connections', []))})")
                
            if requested_details:
                return f"👤 **Customer Profile for {resolved_cust_name.title()}:**\n" + "\n".join(requested_details)
            else:
                status_str = "ACTIVE" if int(data.get("connections", 0)) > 0 else "INACTIVE"
                lines = [
                    f"👤 **Customer Profile: {data.get('customer_name', resolved_cust_name).title()}**",
                    f"- **Subscriber ID:** **{det.get('subscriber_id', 'N/A')}**",
                    f"- **Status:** {status_str}",
                    f"- **Mobile:** {det.get('mobile', 'N/A')}",
                    f"- **Area:** {data.get('area', 'N/A')}",
                    f"- **Joined:** {data.get('join_date', 'N/A')}",
                    f"- **Address:** {data.get('address', 'N/A')}",
                    "",
                    "💳 **Account Summary:**",
                    f"- **Total Paid:** **₹{data.get('paid_amount', '0.00')}**",
                    f"- **Open Invoices:** **₹{open_inv}**",
                    f"- **Overdue Invoices:** **₹{overdue}**",
                    f"- **Wallet Balance:** **₹{wallet_val}**",
                    f"- **Connections:** **{data.get('connections', 0)}** ({', '.join(det.get('connections', []))})"
                ]
                return "\n".join(lines)

    # 11. get_subscription
    elif tool_name == "get_subscription" and resolved_cust_name:
        data_wrapper = tool_result.get("data", {})
        items = []
        if isinstance(data_wrapper, dict):
            items = data_wrapper.get("data", [])
        elif isinstance(data_wrapper, list):
            items = data_wrapper
            
        if not items:
            return f"No subscriptions found for {resolved_cust_name}."
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
            return "\n".join(lines)

    # 12. search_customer / get_all_customers
    elif tool_name in ("search_customer", "get_all_customers"):
        if tool_name == "get_all_customers" and customer_name_query == "latest":
            c_data = tool_result.get("data", {})
            customers = c_data.get("data", []) if isinstance(c_data, dict) else []
            if not customers:
                return "No customers found in the system."
            else:
                top = customers[0]
                return (
                    f"Latest added customer details:\n"
                    f"• **{top.get('name', 'N/A')}**\n"
                    f"  - **Subscriber ID:** **{top.get('subscriber_id', 'N/A')}**\n"
                    f"  - **Join Date:** {top.get('join_date', 'N/A')}\n"
                    f"  - **Status:** {top.get('status', 'N/A').upper()}\n"
                    f"  - **Mobile:** {top.get('mobile', 'N/A')}\n"
                    f"  - **Area:** {top.get('area_name', 'N/A')}"
                )
        
        # Let's check status filter count listings
        status_f = tool_args.get("status")
        if tool_name == "get_all_customers" and (status_f or "inactive_list" in str(customer_name_query) or "active_list" in str(customer_name_query)):
            if not status_f:
                if "inactive_list" in str(customer_name_query) or "inactive" in msg_lower:
                    status_f = "inactive"
                elif "active_list" in str(customer_name_query) or "active" in msg_lower:
                    status_f = "active"
            if agent and hasattr(agent, "_get_customer_dashboard_response"):
                return await agent._get_customer_dashboard_response(billerq_token, billerq_api_url, billerq_user_role, status_f)

        raw_data = tool_result.get("data", []) if isinstance(tool_result, dict) else []
        if isinstance(raw_data, dict):
            data = raw_data.get("data", [])
            total_count = raw_data.get("total", len(data))
        else:
            data = raw_data
            total_count = len(data)
            
        if isinstance(data, list):
            if not data:
                return "No customers found in the system." if tool_name == "get_all_customers" else "No customers found matching your search query."
            else:
                header = f"👥 **Customer Search Results** (Found {len(data)} matching):" if tool_name == "search_customer" else f"👥 **All Customers List** (Found {total_count:,} in total):"
                lines = [header, "Here are the top results:\n"]
                for item in data[:5]:
                    name = item.get("name") or item.get("customer_name") or "Unknown"
                    sub_id = item.get("subscriber_id") or "N/A"
                    status = (item.get("status") or "N/A").upper()
                    mobile = item.get("mobile") or "N/A"
                    area = item.get("area_name") or item.get("area") or "N/A"
                    status_emoji = "🟢" if status == "ACTIVE" else "🔴" if status in ("INACTIVE", "BLOCKED") else "⚠️"
                    lines.append(
                        f"👤 **{name.strip()}** (ID: `{sub_id}`)\n"
                        f"• **Status:** {status} {status_emoji}\n"
                        f"• **Mobile:** {mobile}\n"
                        f"• **Area:** {area}\n"
                    )
                if total_count > 5 or len(data) > 5:
                    remaining = total_count - 5
                    lines.append(f"---\n💡 *For the remaining {remaining:,} customers, click the redirection button below.*")
                return "\n".join(lines)

    # 13. get_invoices
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
        
        status_filter = tool_args.get("payment_status")
        original_total = total
        if status_filter:
            items = [item for item in items if str(item.get("payment_status", "")).lower() == status_filter.lower() or str(item.get("order_status", "")).lower() == status_filter.lower()]
        total = original_total if original_total is not None else len(items)
        
        if not items:
            if resolved_cust_name:
                return f"No invoices found for customer {resolved_cust_name}."
            else:
                return "No invoices found in the system."
        else:
            header = f"📄 **Invoices for {resolved_cust_name}:**" if resolved_cust_name else f"📄 **Invoices Summary** (Total: {total:,})\n"
            lines = [header, "Here are the recent invoices:\n"]
            for item in items[:5]:
                inv_no = item.get("invoice_no") or item.get("id") or "N/A"
                pref = item.get("invoice_prefix") or "INV"
                cname = item.get("customer_name") or resolved_cust_name or "Unknown Customer"
                sub_id = item.get("subscriber_id") or "N/A"
                amount = item.get("amount") or item.get("balance") or "0.00"
                date = item.get("invoice_date") or item.get("created_date") or "N/A"
                status = (item.get("payment_status") or item.get("order_status") or "N/A").upper()
                status_emoji = "🟢" if status == "PAID" else "🔴" if status in ("UNPAID", "PENDING") else "⚠️"
                lines.append(
                    f"🧾 **Invoice #{pref}{inv_no}** — **{cname}** (ID: `{sub_id}`)\n"
                    f"• **Amount:** ₹{format_curr(amount)}\n"
                    f"• **Status:** {status} {status_emoji}\n"
                    f"• **Date:** {date}\n"
                )
            paid_cnt = sum(1 for x in items if str(x.get("payment_status") or x.get("order_status", "")).lower() == "paid")
            unpaid_cnt = sum(1 for x in items if str(x.get("payment_status") or x.get("order_status", "")).lower() in ("unpaid", "pending") or not x.get("payment_status"))
            overdue_cnt = sum(1 for x in items if str(x.get("payment_status") or x.get("order_status", "")).lower() == "overdue")
            
            lines.append("\n📊 **Invoices Metrics Summary:**")
            lines.append(f"- **Paid Invoices:** {paid_cnt} 🟢")
            lines.append(f"- **Unpaid/Pending Invoices:** {unpaid_cnt} 🔴")
            if overdue_cnt > 0:
                lines.append(f"- **Overdue Invoices:** {overdue_cnt} ⚠️")
            lines.append(f"- **Total Listed:** {len(items)}")
            if total > 5 or len(items) > 5:
                remaining = total - 5
                lines.append(f"---\n💡 *For the remaining {remaining:,} invoices, click the redirection button below.*")
            return "\n".join(lines)

    # 14. get_income_summary
    elif tool_name == "get_income_summary":
        data = tool_result.get("data", [])
        requested_month = tool_args.get("month")
        if not requested_month:
            requested_month = datetime.now().strftime("%b")
        if isinstance(data, list):
            total = 0.0
            row_details = []
            for row in data:
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
            lines = [f"Total collection for {full_month_name} 2026: ₹{format_curr(total)}"]
            if row_details:
                lines.append("\nBreakdown by category:")
                lines.extend(row_details)
            return "\n".join(lines)
        else:
            return "No income summary data available."

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
            return "No cancelled invoices found in the system."
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
            return "\n".join(lines)

    # 16. get_archived_customers
    elif tool_name == "get_archived_customers":
        if agent and hasattr(agent, "_get_customer_dashboard_response"):
            return await agent._get_customer_dashboard_response(billerq_token, billerq_api_url, billerq_user_role, "archived")

    # 17. get_pending_subscriptions
    elif tool_name == "get_pending_subscriptions":
        c_data = tool_result.get("data", {})
        items = []
        total = 0
        if isinstance(c_data, dict):
            items = c_data.get("data", [])
            total = c_data.get("total", len(items))
        if not items:
            return "No pending subscriptions found."
        else:
            lines = [f"Total pending subscriptions: {total}", "Here are the recent pending subscriptions:"]
            for item in items[:5]:
                lines.append(f"• **{item.get('customer_name')}** (Sub ID: **{item.get('subscriber_id')}**)\n  - **Plan:** {item.get('package_name')}\n  - **Order Status:** {item.get('order_status', '').upper()}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 18. get_online_payments
    elif tool_name == "get_online_payments":
        c_data = tool_result.get("data", {})
        items = []
        total = 0
        if isinstance(c_data, dict):
            items = c_data.get("data", [])
            total = c_data.get("total", len(items))
        if not items:
            return "No online payments found."
        else:
            lines = [f"Total online payments: {total}", "Here are the recent online payments:"]
            for item in items[:5]:
                lines.append(f"• **{item.get('customer_name')}**\n  - **Amount:** **₹{item.get('paid_amount')}**\n  - **Date:** **{item.get('paid_date')}**\n  - **Invoice:** #{item.get('invoice_no')}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 19. get_customer_payment_report
    elif tool_name == "get_customer_payment_report":
        payment_obj = tool_result.get("payment", {}) if isinstance(tool_result, dict) else {}
        payment_data = []
        if isinstance(payment_obj, dict):
            payment_data = payment_obj.get("data", [])
        elif isinstance(payment_obj, list):
            payment_data = payment_obj

        if not payment_data:
            return "No customer payment report data found."
        else:
            lines = [f"Customer Payment Report Summary (Loaded {len(payment_data)} items):"]
            for item in payment_data[:5]:
                lines.append(f"• **{item.get('name') or item.get('customer_name') or 'N/A'}**\n  - **Paid Amount:** **₹{item.get('paid_amount')}**\n  - **Date:** **{item.get('payment_date') or item.get('created_at') or 'N/A'}**\n  - **Method:** **{item.get('payment_method') or 'N/A'}**")
            return "\n".join(lines)

    # 20. get_package_report
    elif tool_name == "get_package_report":
        rep_data = tool_result.get("data", {})
        pkgs = rep_data.get("packages", {})
        pkgs_list = pkgs.get("data", []) if isinstance(pkgs, dict) else pkgs
        total_amount = rep_data.get("total_amount", 0.0)
        if not pkgs_list:
            return "No packages reported."
        else:
            requested_pkgs = []
            for item in pkgs_list:
                pkg_name = str(item.get("package_name", "")).lower()
                if pkg_name and re.search(rf"\b{re.escape(pkg_name)}\b", msg_lower):
                    requested_pkgs.append(item)
            
            if requested_pkgs:
                lines = [f"Package stats breakdown for {', '.join(p.get('package_name') for p in requested_pkgs)}:"]
                for item in requested_pkgs:
                    lines.append(f"• {item.get('package_name')}: {item.get('invoice_count', 0)} active packages (Unit Price: ₹{item.get('unit_price')})")
                return "\n".join(lines)
            else:
                lines = [f"Total package subscriptions value: ₹{format_curr(total_amount)}", "Package stats breakdown:"]
                for item in pkgs_list[:10]:
                    lines.append(f"• {item.get('package_name')}: {item.get('invoice_count', 0)} active (Unit Price: ₹{item.get('unit_price')})")
                if len(pkgs_list) > 10:
                    lines.append("\nFor the remaining, click the link below.")
                return "\n".join(lines)

    # 21. get_wallet_report
    elif tool_name == "get_wallet_report":
        rep_data = tool_result.get("data", {})
        wallets_list = rep_data.get("wallets", {}).get("data", []) if isinstance(rep_data.get("wallets"), dict) else rep_data.get("wallets", [])
        total_amount = rep_data.get("total_amount", 0.0)
        if not wallets_list:
            return "No wallet stats reported."
        else:
            lines = [f"Total customer wallet value: ₹{format_curr(total_amount)}", "Customer wallet balances:"]
            for item in wallets_list[:5]:
                lines.append(f"• **{item.get('customer_name')}** (Sub ID: **{item.get('subscriber_id')}**)\n  - **Wallet balance:** **₹{item.get('wallet_money')}**\n  - **Area:** {item.get('area_name') or 'N/A'}")
            if len(wallets_list) > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 22. get_tax_report
    elif tool_name == "get_tax_report":
        rep_data = tool_result.get("data", {})
        tax_list = rep_data.get("taxes", {}).get("data", []) if isinstance(rep_data.get("taxes"), dict) else rep_data.get("taxes", [])
        total_amount = rep_data.get("total_amount", 0.0)
        if not tax_list:
            return "No tax stats reported."
        else:
            lines = [f"Total tax amount collected: ₹{format_curr(total_amount)}", "Tax stats breakdown:"]
            for item in tax_list[:5]:
                lines.append(f"• **Invoice #{item.get('invoice_prefix')}{item.get('invoice_number')}** — **{item.get('customer_name')}**\n  - **Tax Rate:** {item.get('tax_class') or 'N/A'}\n  - **Tax Value:** **₹{item.get('tax_value')}**")
            if len(tax_list) > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 23. get_addon_report
    elif tool_name == "get_addon_report":
        rep_data = tool_result.get("data", {})
        addons = rep_data.get("addons", {})
        addons_list = addons.get("data", []) if isinstance(addons, dict) else addons
        total_amount = rep_data.get("total_amount", 0.0)
        if not addons_list:
            return "No add-on stats reported."
        else:
            lines = [f"Total add-ons subscriptions value: ₹{format_curr(total_amount)}", "Add-on stats breakdown:"]
            for item in addons_list[:5]:
                lines.append(f"• {item.get('addon_name')}: {item.get('invoice_count', 0)} active add-ons (Unit Price: ₹{item.get('unit_price')})")
            if len(addons_list) > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 24. get_subscription_report
    elif tool_name == "get_subscription_report":
        rep_data = tool_result.get("data", {})
        subs = rep_data.get("subscriptions", {})
        subs_list = subs.get("data", []) if isinstance(subs, dict) else subs
        total_amount = rep_data.get("total_amount", 0.0)
        if not subs_list:
            return "No subscription stats reported."
        else:
            lines = [f"Total subscription report value: ₹{format_curr(total_amount)}", "Subscription stats breakdown:"]
            for item in subs_list[:5]:
                lines.append(f"• {item.get('package_name') or 'N/A'}: {item.get('invoice_count', 0)} active subscriptions (Unit Price: ₹{item.get('unit_price')})")
            if len(subs_list) > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 25. get_agent_collection_report
    elif tool_name == "get_agent_collection_report":
        rep_data = tool_result.get("data", [])
        if not rep_data:
            return "No agent collection report data found."
        else:
            lines = ["Agent Collection Report Summary:"]
            for item in rep_data[:5]:
                aname = item.get("name") or f"Agent #{item.get('agent_id')}"
                lines.append(f"• **{aname}**\n  - **Income/Collected:** **₹{item.get('income', '0.00')}**\n  - **Collected Today:** **₹{item.get('today', '0.00')}**\n  - **Last Collection Status:** {item.get('time', 'N/A')} ({item.get('progress', 'N/A')})")
            return "\n".join(lines)

    # 26. get_expense_summary
    elif tool_name == "get_expense_summary":
        data = tool_result.get("data", [])
        requested_month = tool_args.get("month")
        if not requested_month:
            requested_month = datetime.now().strftime("%b")
        if isinstance(data, list):
            total = 0.0
            row_details = []
            for row in data:
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
            lines = [f"Total expenses for {full_month_name} 2026: ₹{format_curr(total)}"]
            if row_details:
                lines.append("\nBreakdown by category:")
                lines.extend(row_details)
            return "\n".join(lines)
        else:
            return "No expense summary data available."

    # 27. get_customer_stb
    elif tool_name == "get_customer_stb" and resolved_cust_name:
        stb_data = tool_result.get("data", {})
        items = []
        if isinstance(stb_data, dict):
            items = stb_data.get("data", [])
        elif isinstance(stb_data, list):
            items = stb_data
            
        if not items:
            return f"No STBs/Modems registered for {resolved_cust_name}."
        else:
            lines = [f"STB/Modem Details for {resolved_cust_name}:"]
            for item in items:
                stb_no = item.get("stb_no") or "Unknown"
                status = item.get("status") or "N/A"
                card = item.get("card_no") or "N/A"
                provider = item.get("cas_provider") or "N/A"
                lines.append(f"• **STB Number:** {stb_no}\n  - **Status:** {status.upper()}\n  - **Card Number:** {card}\n  - **CAS Provider:** {provider}")
            return "\n".join(lines)

    # 28. get_stb_status_count / get_stbs
    elif tool_name == "get_stb_status_count":
        c_data = tool_result.get("data", [])
        if not c_data:
            return "No STB status data found."
        else:
            lines = ["📊 **STB Status Breakdown:**"]
            for item in c_data:
                status = item.get("status", "Unknown").upper()
                count = item.get("count", 0)
                status_emoji = "🟢" if status == "ACTIVE" else "🔴" if status in ("INACTIVE", "SUSPENDED") else "⚠️"
                lines.append(f"• **{status}**: **{count}** {status_emoji}")
            return "\n".join(lines)

    elif tool_name == "get_stbs":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No STBs found."
        else:
            lines = [f"📊 **STBs List ({total} total):**"]
            for item in items[:5]:
                lines.append(f"• **STB Number:** {item.get('stb_no') or 'N/A'}\n  - **Status:** {(item.get('status') or 'N/A').upper()}\n  - **CAS Provider:** {item.get('cas_provider') or 'N/A'}\n  - **Customer:** {item.get('customer_name') or 'N/A'}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    # 29. List lookups: packages, areas, staff, roles, items, message settings, providers, categories, tax classes, wallets
    elif tool_name == "get_packages":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No service packages/plans found."
        else:
            lines = [f"📦 **Service Packages ({total} total):**"]
            for item in items[:10]:
                lines.append(f"• **{item.get('name')}** — ₹{item.get('price')} (Duration: {item.get('duration_count')} {item.get('duration_type')})")
            if total > 10:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_areas":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No billing areas/locations found."
        else:
            lines = [f"🗺️ **Billing Areas ({total} total):**"]
            for item in items[:10]:
                lines.append(f"• **{item.get('name')}** (Code: {item.get('code') or 'N/A'})")
            if total > 10:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_staff":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No staff members found."
        else:
            lines = [f"👥 **Staff Members ({total} total):**"]
            for item in items[:5]:
                lines.append(f"• **{item.get('name')}** ({item.get('role_name') or 'No Role'})\n  - **Email:** {item.get('email') or 'N/A'} | **Mobile:** {item.get('mobile') or 'N/A'}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_roles":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No roles found."
        else:
            lines = [f"🛡️ **System Roles ({total} total):**"]
            for item in items[:10]:
                lines.append(f"• **{item.get('name')}** (Display: {item.get('display_name') or 'N/A'})")
            if total > 10:
                return "\n".join(lines) + "\nFor the remaining, click the link below."
            return "\n".join(lines)

    elif tool_name == "get_items":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No inventory items found."
        else:
            lines = [f"📦 **Inventory Items ({total} total):**"]
            for item in items[:5]:
                lines.append(f"• **{item.get('name')}**\n  - **Type:** {item.get('type') or 'N/A'} | **Price:** ₹{item.get('price', '0.00')} | **Tax:** {item.get('tax_class') or 'N/A'}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_message_settings":
        c_data = tool_result.get("data", {})
        if not c_data:
            return "No SMS/WhatsApp message settings found."
        else:
            return (
                f"💬 **SMS & WhatsApp Credit Status:**\n"
                f"• **SMS Gateway:** {c_data.get('sms_gateway') or 'Not Configured'}\n"
                f"• **SMS Balance/Credit:** **{c_data.get('sms_balance') or '0'}**\n"
                f"• **WhatsApp Balance:** **{c_data.get('whatsapp_balance') or '0'}**\n"
                f"• **WhatsApp Status:** {c_data.get('whatsapp_status') or 'Disabled'}"
            )

    elif tool_name == "get_providers":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No CAS/ISP providers found."
        else:
            lines = [f"📡 **CAS/ISP Providers ({total} total):**"]
            for item in items[:10]:
                lines.append(f"• **{item.get('name')}** (Type: {item.get('type') or 'CAS'})")
            if total > 10:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_categories":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No settings categories found."
        else:
            lines = [f"🏷️ **Settings Categories ({total} total):**"]
            for item in items[:10]:
                lines.append(f"• **{item.get('name')}**")
            if total > 10:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_tax_classes":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No tax classes found."
        else:
            lines = [f"💸 **Tax Classes & Rates ({total} total):**"]
            for item in items[:10]:
                lines.append(f"• **{item.get('name')}** — **{item.get('rate')}%**")
            if total > 10:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_wallets":
        c_data = tool_result.get("data", {})
        items = c_data.get("data", []) if isinstance(c_data, dict) else c_data
        total = c_data.get("total", len(items)) if isinstance(c_data, dict) else len(items)
        if not items:
            return "No wallets found."
        else:
            lines = [f"💳 **Wallets List ({total} total):**"]
            for item in items[:5]:
                lines.append(f"• **{item.get('customer_name') or 'Unknown'}**\n  - **Balance:** **₹{item.get('wallet_money') or '0.00'}**\n  - **Last Updated:** {item.get('updated_at') or 'N/A'}")
            if total > 5:
                lines.append("\nFor the remaining, click the link below.")
            return "\n".join(lines)

    elif tool_name == "get_both_subscription_addon":
        c_data = tool_result.get("data", {})
        subs = c_data.get("subscriptions", [])
        addons = c_data.get("addons", [])
        lines = ["📦 **Active Subscriptions & Add-ons Summary:**", "\n**Subscriptions:**"]
        if not subs:
            lines.append("No active subscriptions.")
        for item in subs[:5]:
            lines.append(f"• {item.get('package_name')} (Expiry: {item.get('recurring_date') or 'N/A'})")
        lines.append("\n**Add-ons:**")
        if not addons:
            lines.append("No active add-ons.")
        for item in addons[:5]:
            lines.append(f"• {item.get('addon_name')} (Expiry: {item.get('recurring_date') or 'N/A'})")
        return "\n".join(lines)

    return None
