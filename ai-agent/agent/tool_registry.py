import json
from typing import List, Dict, Any

TOOL_REGISTRY = {
    "customers": [
        {
            "name": "get_all_customers",
            "description": "List all customers or filter by active/inactive status.",
            "args": ["status", "page_length"]
        },
        {
            "name": "search_customer",
            "description": "Search for a customer by name, mobile number, or subscriber ID.",
            "args": ["query"]
        },
        {
            "name": "get_customer_profile",
            "description": "Get detailed profile information, billing details, and address for a specific customer ID.",
            "args": ["customer_id"]
        },
        {
            "name": "get_customer_status_count",
            "description": "Get active, inactive, and total customer counts.",
            "args": []
        },
        {
            "name": "get_customer_stb",
            "description": "Get the set-top box or modem details for a specific customer.",
            "args": ["customer_id"]
        },
        {
            "name": "get_wallets",
            "description": "List customer wallet balances.",
            "args": []
        },
        {
            "name": "get_areas",
            "description": "List all billing areas and locations.",
            "args": []
        }
    ],
    "payments": [
        {
            "name": "get_payment_history",
            "description": "Get payment history or payment receipts for a specific customer ID.",
            "args": ["customer_id", "from_date", "to_date"]
        },
        {
            "name": "get_recent_payments",
            "description": "Get a list of recently collected payments across all customers.",
            "args": ["limit"]
        },
        {
            "name": "get_unpaid_customers",
            "description": "List unpaid customers with outstanding balances.",
            "args": ["sort_by_balance"]
        },
        {
            "name": "get_payment_due_data",
            "description": "Get a list of customer accounts with overdue/due payments.",
            "args": []
        },
        {
            "name": "get_overdues",
            "description": "Get overdue payment logs and follow-up history.",
            "args": []
        },
        {
            "name": "get_invoices",
            "description": "List or filter invoices by status (PAID/UNPAID/PENDING/OVERDUE) and customer ID.",
            "args": ["customer_id", "payment_status"]
        },
        {
            "name": "get_cancelled_invoices",
            "description": "List cancelled invoices in the system.",
            "args": []
        },
        {
            "name": "get_income_summary",
            "description": "Get monthly income/payment collection summaries by category for a specific month or year. Use this for past/previous years (e.g. 2025, last year).",
            "args": ["month", "year"]
        },
        {
            "name": "get_expense_summary",
            "description": "Get monthly expenses summaries by category for a specific month or year.",
            "args": ["month", "year"]
        },
        {
            "name": "get_dashboard_data",
            "description": "Get dashboard counts for the CURRENT day or CURRENT month only (total customers, active STBs, payment collections today/this month, outstanding dues). Cannot get data for last year or past years.",
            "args": []
        },
        {
            "name": "get_connection_data",
            "description": "Get connection counts, monthly collection progress, or agent collection collections.",
            "args": ["customer_name"]
        },
        {
            "name": "get_agent_collection_report",
            "description": "Get payment collection report for staff agents.",
            "args": ["start_date", "end_date"]
        }
    ],
    "subscriptions": [
        {
            "name": "get_subscription",
            "description": "Get active package subscriptions for a specific customer ID.",
            "args": ["customer_id"]
        },
        {
            "name": "get_pending_subscriptions",
            "description": "List pending or unactivated subscription orders.",
            "args": []
        },
        {
            "name": "get_recurring_data",
            "description": "List recurring invoice/subscription profiles.",
            "args": ["customer_name"]
        },
        {
            "name": "get_packages",
            "description": "List all service packages and subscription plans.",
            "args": []
        },
        {
            "name": "get_items",
            "description": "List inventory and hardware items.",
            "args": []
        },
        {
            "name": "get_all_addons",
            "description": "List all active package add-ons.",
            "args": []
        }
    ],
    "complaints": [
        {
            "name": "get_complaints",
            "description": "List, count, or filter complaints by status (open/progress/closed), customer, area, or problem type.",
            "args": ["status", "customer_name", "problem_type", "area_name"]
        },
        {
            "name": "get_complaint_status_count",
            "description": "Get status-wise breakdown count of complaints.",
            "args": []
        },
        {
            "name": "get_problem_types",
            "description": "List all types of problems (e.g. billing, connection, signal, device).",
            "args": []
        }
    ],
    "leads": [
        {
            "name": "get_enquiries",
            "description": "List customer enquiries.",
            "args": []
        },
        {
            "name": "get_leads",
            "description": "List customer leads.",
            "args": []
        },
        {
            "name": "get_followups",
            "description": "List scheduled followups for leads.",
            "args": []
        }
    ],
    "admin_and_staff": [
        {
            "name": "get_staff",
            "description": "List all system staff members and agents.",
            "args": []
        },
        {
            "name": "get_roles",
            "description": "List staff roles and permissions.",
            "args": []
        },
        {
            "name": "get_message_settings",
            "description": "Get SMS and WhatsApp credit balance and gateway configuration.",
            "args": []
        },
        {
            "name": "get_providers",
            "description": "List CAS and ISP providers.",
            "args": []
        },
        {
            "name": "get_categories",
            "description": "List categories.",
            "args": []
        },
        {
            "name": "get_tax_classes",
            "description": "List tax classes and percentage rates.",
            "args": []
        }
    ]
}

def select_modules(message: str) -> List[str]:
    """Identifies the relevant tool modules based on keywords in the user query."""
    text = message.lower().strip()
    modules = []

    # Complaints
    if any(word in text for word in ["complaint", "issue", "ticket", "problem", "fault", "not working", "broken"]):
        modules.append("complaints")
        
    # Payments & Collections & Finances
    if any(word in text for word in ["payment", "collection", "paid", "invoice", "due", "overdue", "outstanding", "balance", "income", "expense", "revenue", "billing", "bill"]):
        modules.append("payments")
        
    # Subscriptions & Packages
    if any(word in text for word in ["subscription", "package", "plan", "addon", "add-on", "recurring", "renew"]):
        modules.append("subscriptions")
        
    # Leads & Enquiries
    if any(word in text for word in ["lead", "enquiry", "enquiries", "followup", "follow-up"]):
        modules.append("leads")
        
    # Staff / Admin
    if any(word in text for word in ["staff", "role", "agent list", "message settings", "sms", "whatsapp", "credit", "provider", "tax class", "tax rate"]):
        modules.append("admin_and_staff")

    # Customers
    if any(word in text for word in ["customer", "subscriber", "client", "wallet", "area", "place"]):
        modules.append("customers")

    # If no specific modules matched, fallback to returning the main modules
    if not modules:
        return ["customers", "payments", "subscriptions", "complaints"]

    return list(set(modules))

def get_selected_tools(message: str) -> List[Dict[str, Any]]:
    """Retrieves a compacted flat list of relevant tools for the prompt."""
    selected_modules = select_modules(message)
    tools = []
    for mod in selected_modules:
        tools.extend(TOOL_REGISTRY[mod])
    return tools
