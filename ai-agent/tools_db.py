"""
Database-driven tools and execution layer.
"""
import re
import logging
from database import run_query
from schema_docs import TABLE_COLUMNS, TABLES_WITH_COMPANY_ID

logger = logging.getLogger("billerq-db-tools")

# ---------------------------------------------------------------------
# 1. TOOL DEFINITIONS — sent to Grok / Bedrock
# ---------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_customers",
        "description": (
            "Look up customers by name, phone, subscriber_id, area, or "
            "status. Returns basic customer profile info. Use this first "
            "to resolve a customer's internal numeric id from a name or "
            "phone number before calling other tools that need customer_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full or partial name"},
                "phone": {"type": "string"},
                "subscriber_id": {"type": "string", "description": "Human-readable subscriber ID shown in the UI"},
                "customer_id": {"type": "integer", "description": "Internal numeric id, if already known"},
                "area": {"type": "string", "description": "Area name to filter by"},
                "status": {"type": "string", "description": "e.g. active, inactive"},
            },
        },
    },
    {
        "name": "get_billing",
        "description": (
            "Get invoices (orders) or subscriptions for a customer or "
            "company-wide. 'Invoice' in the UI = the 'orders' table. "
            "Use type='invoice' for billing/payment questions, "
            "type='subscription' for plan/package questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["invoice", "subscription"]},
                "customer_id": {"type": "integer"},
                "payment_status": {
                    "type": "string",
                    "description": "e.g. paid, unpaid, pending — matches orders.payment_status",
                },
                "status": {
                    "type": "string",
                    "description": "e.g. active, cancelled — matches orders.status or customer_subscriptions.status",
                },
                "limit": {"type": "integer", "description": "Max rows to return, default 20"},
            },
            "required": ["type"],
        },
    },
    {
        "name": "get_complaints",
        "description": "Get complaints, filterable by customer, area, problem type, or status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
                "area": {"type": "string"},
                "problem_type": {"type": "string"},
                "status": {"type": "string", "description": "e.g. open, resolved, in_progress"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_leads",
        "description": (
            "Get sales pipeline data: enquiries, leads, or follow-ups. "
            "Use source='enquiry' for raw enquiries, source='lead' for "
            "qualified leads, source='followup' for follow-up records."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "enum": ["enquiry", "lead", "followup"]},
                "status": {"type": "string"},
                "assigned_to": {"type": "integer", "description": "staff user id"},
                "limit": {"type": "integer"},
            },
            "required": ["source"],
        },
    },
    {
        "name": "get_wallet_balance",
        "description": "Get a customer's wallet balance (computed from wallet ledger entries) and recent transactions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer"},
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_reports",
        "description": (
            "Get financial reports: payment collection (money actually "
            "received), unpaid/payment due (money still owed), income, "
            "expenses, or tax collected. 'Collections' questions should "
            "use report_name='payment_collection'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "report_name": {
                    "type": "string",
                    "enum": [
                        "payment_collection", "payment_due", "unpaid_customer",
                        "income_summary", "expense_summary", "tax_report",
                    ],
                },
                "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD"},
                "limit": {"type": "integer"},
            },
            "required": ["report_name"],
        },
    },
    {
        "name": "get_communication_logs",
        "description": "Get SMS or WhatsApp message logs sent to customers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string", "enum": ["sms", "whatsapp"]},
                "customer_id": {"type": "integer"},
                "sent_status": {"type": "string", "description": "e.g. sent, failed, pending"},
                "limit": {"type": "integer"},
            },
            "required": ["channel"],
        },
    },
    {
        "name": "get_banking",
        "description": "Get bank/UPI accounts configured for the company, including balances.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
        },
    },
    {
        "name": "get_products",
        "description": (
            "Get packages (subscription plans), addons, or items "
            "(inventory/products) offered by the company."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["package", "addon", "item"]},
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["type"],
        },
    },
    {
        "name": "get_staff",
        "description": "Get staff/user accounts and their roles.",
        "input_schema": {
            "type": "object",
            "properties": {
                "role_name": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_settings",
        "description": (
            "Get company configuration: service areas, tax classes/rates, "
            "or payment methods."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["area", "tax_class", "payment_method"]},
                "limit": {"type": "integer"},
            },
            "required": ["type"],
        },
    },
    {
        "name": "get_schema",
        "description": (
            "Look up real table and column names in the BillerQ database. "
            "Call with no table_name to get the full list of table names. "
            "Call with a table_name to see its exact columns and types. "
            "ALWAYS call this before writing a query_data SQL query for "
            "anything the other tools don't already cover — never guess "
            "column names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {"type": "string", "description": "Optional. Omit to list all tables."},
            },
        },
    },
    {
        "name": "query_data",
        "description": (
            "Run a read-only SQL SELECT query for ANY question the other "
            "tools don't cover — comparisons across time periods, custom "
            "aggregations, multi-table joins, historical/year-over-year "
            "analysis, anything unpredictable. Use standard MySQL syntax. "
            "Call get_schema first to confirm real table/column names. "
            "CRITICAL: every table you reference that has a company_id "
            "column MUST be filtered with company_id = {the current "
            "company_id, given to you in the system prompt} in the WHERE "
            "clause — queries missing this will be rejected. Only SELECT "
            "statements are allowed; no INSERT/UPDATE/DELETE/DROP, no "
            "multiple statements, no comments."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single SELECT statement."},
            },
            "required": ["sql"],
        },
    },
]

# ---------------------------------------------------------------------
# 2. SQL SECURITY CHECK
# ---------------------------------------------------------------------

def validate_sql_query(sql: str, company_id: int) -> str:
    """
    Validates SQL input to prevent write actions and ensure tenant isolation.
    """
    sql_lower = sql.lower()

    # Reject non-SELECT queries
    forbidden = ["insert", "update", "delete", "drop", "alter", "truncate", "replace", "create", "grant", "revoke"]
    for verb in forbidden:
        if re.search(r"\b" + verb + r"\b", sql_lower):
            raise ValueError(f"Command '{verb.upper()}' is not allowed in read-only queries.")

    if not sql_lower.strip().startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")

    # Find referenced tables in SQL and verify company_id constraint
    referenced_tables = []
    for table in TABLES_WITH_COMPANY_ID:
        if re.search(r"\b" + re.escape(table) + r"\b", sql_lower):
            referenced_tables.append(table)

    if referenced_tables:
        expected_pattern = rf"company_id\s*=\s*(?:{company_id}|:company_id|:cid|'{company_id}'|\"{company_id}\")"
        if not re.search(expected_pattern, sql_lower):
            raise ValueError(
                f"Security Validation Failed: The query references table(s) {referenced_tables} which contain multi-tenant data, "
                f"but is missing the filter 'company_id = {company_id}' in the WHERE clause. Please add this filter."
            )

    return sql

# ---------------------------------------------------------------------
# 3. TOOL EXECUTION LOGIC
# ---------------------------------------------------------------------

def execute_tool(name: str, arguments: dict, company_id: int) -> dict:
    """
    Dispatches tool execution to the database connection layer.
    """
    logger.info("Executing DB Tool: %s with args: %s, company_id: %d", name, arguments, company_id)
    try:
        if name == "get_schema":
            table_name = arguments.get("table_name")
            if table_name:
                if table_name in TABLE_COLUMNS:
                    return {table_name: TABLE_COLUMNS[table_name]}
                return {"error": f"Table '{table_name}' does not exist in schema."}
            return {"tables": list(TABLE_COLUMNS.keys())}

        elif name == "query_data":
            sql = arguments.get("sql", "")
            # Validate SQL
            validate_sql_query(sql, company_id)
            # Run SQL
            rows = run_query(sql, {})
            return {"rows": rows}

        elif name == "get_customers":
            # Build customers lookup query
            query = "SELECT c.id, c.subscriber_id, c.first_name, c.last_name, c.mobile, c.status, a.name as area_name FROM customers c LEFT JOIN areas a ON c.area_id = a.id WHERE c.company_id = :cid"
            params = {"cid": company_id}
            
            customer_id = arguments.get("customer_id")
            if customer_id:
                query += " AND c.id = :customer_id"
                params["customer_id"] = customer_id
                
            sub_id = arguments.get("subscriber_id")
            if sub_id:
                query += " AND c.subscriber_id = :sub_id"
                params["sub_id"] = sub_id
                
            name = arguments.get("name")
            if name:
                query += " AND (c.first_name LIKE :name OR c.last_name LIKE :name OR c.billing_name LIKE :name)"
                params["name"] = f"%{name}%"
                
            phone = arguments.get("phone")
            if phone:
                query += " AND c.mobile = :phone"
                params["phone"] = phone
                
            area = arguments.get("area")
            if area:
                query += " AND a.name LIKE :area"
                params["area"] = f"%{area}%"
                
            status = arguments.get("status")
            if status:
                query += " AND c.status = :status"
                params["status"] = status
                
            query += " LIMIT 20"
            rows = run_query(query, params)
            return {"customers": rows}

        elif name == "get_billing":
            b_type = arguments.get("type")
            customer_id = arguments.get("customer_id")
            status = arguments.get("status")
            limit = arguments.get("limit", 20)
            
            if b_type == "invoice":
                query = "SELECT * FROM orders WHERE company_id = :cid"
                params = {"cid": company_id}
                if customer_id:
                    query += " AND customer_id = :customer_id"
                    params["customer_id"] = customer_id
                pay_status = arguments.get("payment_status")
                if pay_status:
                    query += " AND payment_status = :pay_status"
                    params["pay_status"] = pay_status
                if status:
                    query += " AND status = :status"
                    params["status"] = status
                query += " ORDER BY invoice_date DESC LIMIT :limit"
                params["limit"] = limit
                rows = run_query(query, params)
                return {"invoices": rows}
                
            elif b_type == "subscription":
                query = "SELECT * FROM customer_subscriptions WHERE company_id = :cid"
                params = {"cid": company_id}
                if customer_id:
                    query += " AND customer_id = :customer_id"
                    params["customer_id"] = customer_id
                if status:
                    query += " AND status = :status"
                    params["status"] = status
                query += " ORDER BY created_at DESC LIMIT :limit"
                params["limit"] = limit
                rows = run_query(query, params)
                return {"subscriptions": rows}

        elif name == "get_complaints":
            query = "SELECT c.*, a.name as area_name FROM complaints c LEFT JOIN areas a ON c.area_id = a.id WHERE c.company_id = :cid"
            params = {"cid": company_id}
            
            customer_id = arguments.get("customer_id")
            if customer_id:
                query += " AND c.customer_id = :customer_id"
                params["customer_id"] = customer_id
            area = arguments.get("area")
            if area:
                query += " AND a.name LIKE :area"
                params["area"] = f"%{area}%"
            prob_type = arguments.get("problem_type")
            if prob_type:
                query += " AND c.problem_type = :prob_type"
                params["prob_type"] = prob_type
            status = arguments.get("status")
            if status:
                query += " AND c.status = :status"
                params["status"] = status
                
            limit = arguments.get("limit", 20)
            query += " ORDER BY c.created_at DESC LIMIT :limit"
            params["limit"] = limit
            rows = run_query(query, params)
            return {"complaints": rows}

        elif name == "get_leads":
            source = arguments.get("source")
            status = arguments.get("status")
            assigned_to = arguments.get("assigned_to")
            limit = arguments.get("limit", 20)
            
            if source == "enquiry":
                query = "SELECT * FROM enquiries WHERE company_id = :cid"
                params = {"cid": company_id}
                if status:
                    query += " AND status = :status"
                    params["status"] = status
                if assigned_to:
                    query += " AND assigned_to = :assigned_to"
                    params["assigned_to"] = assigned_to
                query += " ORDER BY created_at DESC LIMIT :limit"
                params["limit"] = limit
                return {"enquiries": run_query(query, params)}
                
            elif source == "lead":
                query = "SELECT * FROM leads WHERE company_id = :cid"
                params = {"cid": company_id}
                if status:
                    query += " AND stage = :status"
                    params["status"] = status
                if assigned_to:
                    query += " AND assigned_to = :assigned_to"
                    params["assigned_to"] = assigned_to
                query += " ORDER BY created_at DESC LIMIT :limit"
                params["limit"] = limit
                return {"leads": run_query(query, params)}
                
            elif source == "followup":
                query = "SELECT * FROM followups WHERE company_id = :cid"
                params = {"cid": company_id}
                if status:
                    query += " AND status = :status"
                    params["status"] = status
                query += " ORDER BY created_at DESC LIMIT :limit"
                params["limit"] = limit
                return {"followups": run_query(query, params)}

        elif name == "get_wallet_balance":
            customer_id = arguments.get("customer_id")
            # Balance
            bal_query = "SELECT SUM(amount) as balance FROM wallets WHERE customer_id = :customer_id AND company_id = :cid"
            bal_rows = run_query(bal_query, {"customer_id": customer_id, "cid": company_id})
            balance = bal_rows[0].get("balance") if bal_rows else 0.0
            
            # History
            hist_query = "SELECT * FROM wallets WHERE customer_id = :customer_id AND company_id = :cid ORDER BY paid_at DESC LIMIT 5"
            history = run_query(hist_query, {"customer_id": customer_id, "cid": company_id})
            return {"customer_id": customer_id, "wallet_balance": balance or 0.0, "recent_wallet_transactions": history}

        elif name == "get_reports":
            rep_name = arguments.get("report_name")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")
            limit = arguments.get("limit", 20)
            
            params = {"cid": company_id}
            if rep_name == "payment_collection":
                query = "SELECT * FROM payments WHERE company_id = :cid"
                if date_from:
                    query += " AND txn_date >= :date_from"
                    params["date_from"] = date_from
                if date_to:
                    query += " AND txn_date <= :date_to"
                    params["date_to"] = date_to
                query += " ORDER BY txn_date DESC LIMIT :limit"
                params["limit"] = limit
                return {"payment_collection": run_query(query, params)}
                
            elif rep_name in ("payment_due", "unpaid_customer"):
                query = "SELECT * FROM orders WHERE company_id = :cid AND payment_status != 'paid'"
                if date_from:
                    query += " AND invoice_date >= :date_from"
                    params["date_from"] = date_from
                if date_to:
                    query += " AND invoice_date <= :date_to"
                    params["date_to"] = date_to
                query += " ORDER BY invoice_date DESC LIMIT :limit"
                params["limit"] = limit
                return {"unpaid_invoices": run_query(query, params)}
                
            elif rep_name == "income_summary":
                query = "SELECT * FROM incomes WHERE company_id = :cid"
                if date_from:
                    query += " AND bill_date >= :date_from"
                    params["date_from"] = date_from
                if date_to:
                    query += " AND bill_date <= :date_to"
                    params["date_to"] = date_to
                query += " ORDER BY bill_date DESC LIMIT :limit"
                params["limit"] = limit
                return {"income_summary": run_query(query, params)}
                
            elif rep_name == "expense_summary":
                query = "SELECT * FROM expenses WHERE company_id = :cid"
                if date_from:
                    query += " AND bill_date >= :date_from"
                    params["date_from"] = date_from
                if date_to:
                    query += " AND bill_date <= :date_to"
                    params["date_to"] = date_to
                query += " ORDER BY bill_date DESC LIMIT :limit"
                params["limit"] = limit
                return {"expense_summary": run_query(query, params)}
                
            elif rep_name == "tax_report":
                query = "SELECT * FROM order_item_taxes WHERE company_id = :cid"
                query += " ORDER BY created_at DESC LIMIT :limit"
                params["limit"] = limit
                return {"tax_records": run_query(query, params)}

        elif name == "get_communication_logs":
            channel = arguments.get("channel")
            customer_id = arguments.get("customer_id")
            sent_status = arguments.get("sent_status")
            limit = arguments.get("limit", 20)
            
            table = "sms_logs" if channel == "sms" else "whatsapp_logs"
            query = f"SELECT * FROM {table} WHERE company_id = :cid"
            params = {"cid": company_id}
            
            if customer_id:
                query += " AND customer_id = :customer_id"
                params["customer_id"] = customer_id
            if sent_status:
                query += " AND sent_status = :sent_status"
                params["sent_status"] = sent_status
                
            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit
            return {f"{channel}_logs": run_query(query, params)}

        elif name == "get_banking":
            status = arguments.get("status")
            query = "SELECT * FROM accounts WHERE company_id = :cid"
            params = {"cid": company_id}
            if status:
                query += " AND status = :status"
                params["status"] = status
            return {"bank_accounts": run_query(query, params)}

        elif name == "get_products":
            p_type = arguments.get("type")
            status = arguments.get("status")
            limit = arguments.get("limit", 20)
            
            table_map = {"package": "packages", "addon": "add_ons", "item": "items"}
            table = table_map.get(p_type, "packages")
            
            query = f"SELECT * FROM {table} WHERE company_id = :cid"
            params = {"cid": company_id}
            if status:
                query += " AND status = :status"
                params["status"] = status
            query += " LIMIT :limit"
            params["limit"] = limit
            return {f"{p_type}s": run_query(query, params)}

        elif name == "get_staff":
            role_name = arguments.get("role_name")
            status = arguments.get("status")
            limit = arguments.get("limit", 20)
            
            query = "SELECT u.id, u.first_name, u.last_name, u.email, u.status, r.name as role_name FROM users u LEFT JOIN roles r ON u.role_id = r.id WHERE u.company_id = :cid"
            params = {"cid": company_id}
            
            if role_name:
                query += " AND r.name = :role_name"
                params["role_name"] = role_name
            if status:
                query += " AND u.status = :status"
                params["status"] = status
                
            query += " LIMIT :limit"
            params["limit"] = limit
            return {"staff": run_query(query, params)}

        elif name == "get_settings":
            s_type = arguments.get("type")
            limit = arguments.get("limit", 20)
            
            params = {"cid": company_id, "limit": limit}
            if s_type == "area":
                return {"areas": run_query("SELECT * FROM areas WHERE company_id = :cid LIMIT :limit", params)}
            elif s_type == "tax_class":
                return {"tax_classes": run_query("SELECT * FROM tax_groups WHERE company_id = :cid LIMIT :limit", params)}
            elif s_type == "payment_method":
                return {"payment_methods": run_query("SELECT * FROM payment_methods WHERE company_id = :cid LIMIT :limit", params)}

        return {"error": f"Tool '{name}' is not supported."}
    except RuntimeError:
        # Database connectivity failure — re-raise so app.py can fall back to REST agent
        raise
    except Exception as e:
        logger.exception("Error executing database tool %s", name)
        return {"error": f"Tool execution failed: {str(e)}"}
