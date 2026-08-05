# Dynamic learned routes mapping user queries to tool configurations
LEARNED_ROUTES = {
    "archived": {
        "tool": "get_archived_customers",
        "arguments": {},
        "customer_name": None
    },
    "show archived list": {
        "tool": "get_archived_customers",
        "arguments": {},
        "customer_name": None
    },
    "deleted customers": {
        "tool": "get_archived_customers",
        "arguments": {},
        "customer_name": None
    },
    "show me the details of jinto": {
        "tool": "get_customer_profile",
        "arguments": {},
        "customer_name": "Jinto"
    },
    "jinto joseph's phone number and customer id": {
        "tool": "search_customer",
        "arguments": {},
        "customer_name": "Jinto Joseph"
    },
    "customer id": {
        "tool": "search_customer",
        "arguments": {},
        "customer_name": "customer id"
    },
    "jinto joseph's subscriber id and phone number": {
        "tool": "search_customer",
        "arguments": {},
        "customer_name": "Jinto Joseph"
    },
    "show unresolved complaints": {
        "tool": "get_complaints",
        "arguments": {
            "status": "unresolved"
        },
        "customer_name": None
    },
    "give me the last yeat total collection": {
        "tool": "get_income_summary",
        "arguments": {
            "month": "December",
            "year": "2025"
        },
        "customer_name": None
    },
    "give me the total collection data": {
        "tool": "get_dashboard_data",
        "arguments": {},
        "customer_name": None
    },
    "collection details": {
        "tool": "get_dashboard_data",
        "arguments": {},
        "customer_name": None
    },
    "enquiry details": {
        "tool": "get_enquiries",
        "arguments": {},
        "customer_name": None
    },
    "show total wallet balance": {
        "tool": "get_wallets",
        "arguments": {},
        "customer_name": None
    },
    "show customer payment report": {
        "tool": "get_customer_payment_report",
        "arguments": {},
        "customer_name": None
    },
    "show active connections": {
        "tool": "get_connection_data",
        "arguments": {},
        "customer_name": None
    },
    "how many active customers?.": {
        "tool": "get_customer_status_count",
        "arguments": {},
        "customer_name": None
    },
    "who has overdue payments?": {
        "tool": "get_overdue_list",
        "arguments": {},
        "customer_name": None
    },
    "latest unresolved invoices": {
        "tool": "get_invoices",
        "arguments": {
            "payment_status": "unpaid"
        },
        "customer_name": None
    },
    "show package report": {
        "tool": "get_package_report",
        "arguments": {},
        "customer_name": None
    },
    "show complaint status counts": {
        "tool": "get_complaint_status_count",
        "arguments": {},
        "customer_name": None
    },
    "give bank account number of archana": {
        "tool": "get_customer_profile",
        "arguments": {},
        "customer_name": "Archana"
    },
    "give me the owner of account number 345678765432": {
        "tool": "get_customer_profile",
        "arguments": {},
        "customer_name": "345678765432"
    },
    "joshi": {
        "tool": "search_customer",
        "arguments": {},
        "customer_name": "Joshi"
    },
    "give me the details of transaction id 6a3e213661a96": {
        "tool": "get_transactions",
        "arguments": {
            "transaction_id": "6a3e213661a96"
        },
        "customer_name": None
    },
    "give me the customer that come under the area appolo junction": {
        "tool": "search_customer",
        "arguments": {
            "area": "APPOLO JUNCTION"
        },
        "customer_name": None
    },
    "how many active customers?": {
        "tool": "get_customer_status_count",
        "arguments": {},
        "customer_name": None
    },
    "total collection for today": {
        "tool": "get_dashboard_data",
        "arguments": {},
        "customer_name": None
    },
    "give details of advaith v": {
        "tool": "get_customer_profile",
        "arguments": {},
        "customer_name": "ADVAITH V"
    },
    "give me the lead enquiry details": {
        "tool": "get_enquiries",
        "arguments": {},
        "customer_name": None
    },
    "give me the lead list": {
        "tool": "get_leads",
        "arguments": {},
        "customer_name": None
    },
    "how much follow up overdue left": {
        "tool": "get_followups",
        "arguments": {},
        "customer_name": None
    },
    "give overdue follow-ups list": {
        "tool": "get_followups",
        "arguments": {},
        "customer_name": None
    },
    "how many leads": {
        "tool": "get_leads",
        "arguments": {},
        "customer_name": None
    },
    "how mny expired subscription": {
        "tool": "get_subscription_report",
        "arguments": {},
        "customer_name": None
    },
    "how much cable tv connection do we have now": {
        "tool": "get_connection_data",
        "arguments": {},
        "customer_name": None
    },
    "how mych total dues": {
        "tool": "get_dashboard_data",
        "arguments": {},
        "customer_name": None
    },
    "how much subscription has ben expired": {
        "tool": "get_subscription_report",
        "arguments": {},
        "customer_name": None
    },
    "how muc total enquiries": {
        "tool": "get_enquiries",
        "arguments": {},
        "customer_name": None
    }
}
