"""
BillerQ API endpoint registry.

All read-only API endpoints mapped from the BillerQ platform.
The agent ONLY calls read/query endpoints — never write/mutate endpoints.
"""


# -------------------------------------------------------------------
# API Registry — maps logical names to BillerQ endpoint paths
# -------------------------------------------------------------------

API_REGISTRY = {
    # ---------------------------------------------------------------
    # Customer APIs
    # ---------------------------------------------------------------
    "show_customer": "/admin/show-customer",
    "get_customer": "/admin/get-customer",
    "get_customer_profile": "/admin/get-customer-profile",
    "get_customer_list": "/admin/get-customer-list",
    "get_customer_search": "/admin/get-customer-search",
    "get_customer_status_count": "/admin/get-customer-status-wise-count",
    "get_archived_customer": "/admin/get-archived-customer",
    "get_last_customer_id": "/admin/get-last-customerid",

    # ---------------------------------------------------------------
    # Subscription APIs
    # ---------------------------------------------------------------
    "show_subscription": "/admin/show-customer-subscription",
    "get_single_subscription": "/admin/get-single-subscription",
    "subscription_history": "/admin/customer-subscription-history",
    "get_pending_subscriptions": "/admin/get-pending-subscription-list",

    # ---------------------------------------------------------------
    # Payment APIs
    # ---------------------------------------------------------------
    "payment_history": "/admin/get-customer-payment-history",
    "get_recent_payment": "/admin/get-recent-payment",
    "get_payment_receipt": "/admin/get-payment-receipt",
    "get_unpaid_customers": "/admin/get-unpaid-customers",
    "get_payment_due": "/admin/get-payment-due-data",
    "get_online_payment": "/admin/get-online-payment-data",
    "get_customer_payment_report": "/admin/get-customer-payment-report",
    "get_order_recent_payment": "/admin/get-order-recent-payment",
    "get_invoice_amount": "/admin/get-invoice-amount",

    # ---------------------------------------------------------------
    # Invoice / Order APIs
    # ---------------------------------------------------------------
    "show_order": "/admin/show-order",
    "show_single_order": "/admin/show-single-customer-order",
    "get_recent_order": "/admin/get-recent-order",
    "get_invoice_data": "/admin/get-invoice-data-show",
    "cancelled_invoice": "/admin/cancelled-invoice",

    # ---------------------------------------------------------------
    # Reports APIs
    # ---------------------------------------------------------------
    "package_report": "/admin/get-package-report",
    "wallet_report": "/admin/get-wallet-report",
    "tax_report": "/admin/get-tax-report",
    "addon_report": "/admin/get-add-on-report",
    "subscription_report": "/admin/get-subscription-report",
    "agent_collection_report": "/admin/get-agent-collection-report",
    "income_summary_report": "/admin/get-income-summary-report",
    "expense_summary_report": "/admin/get-expense-summary-report",

    # ---------------------------------------------------------------
    # Dashboard APIs
    # ---------------------------------------------------------------
    "get_connection_data": "/admin/get-connection-data",
    "get_dashboard_data": "/admin/get-data",

    # ---------------------------------------------------------------
    # STB (Set-Top Box) APIs
    # ---------------------------------------------------------------
    "view_stb": "/admin/view-stb",
    "get_single_stb": "/admin/get-single-customer-stb",
    "stb_status_count": "/admin/stb-status-count",
    "get_stb_details": "/admin/get-stb-details",
    "stb_select": "/admin/stb-select",
    "get_stb_plans": "/admin/get-stb-plans",

    # ---------------------------------------------------------------
    # Complaint APIs
    # ---------------------------------------------------------------
    "get_complaint": "/admin/get-complaint",
    "complaint_status_count": "/admin/complaint-status-count",
    "get_problem_types": "/admin/get-problem-types",

    # ---------------------------------------------------------------
    # Area APIs
    # ---------------------------------------------------------------
    "view_area": "/admin/view-area",
    "get_area_select": "/admin/get-area-select",

    # ---------------------------------------------------------------
    # Package APIs
    # ---------------------------------------------------------------
    "view_package": "/admin/view-package",
    "get_package_select": "/admin/get-package-select",

    # ---------------------------------------------------------------
    # Wallet APIs
    # ---------------------------------------------------------------
    "show_wallet": "/admin/show-wallet",

    # ---------------------------------------------------------------
    # Add-on APIs
    # ---------------------------------------------------------------
    "show_addon": "/admin/show-add-on",
    "addon_history": "/admin/customer-add-on-history",
    "show_single_addon": "/admin/show-single-customer-add-on",
    "get_addon_select": "/admin/get-add-on-select",

    # ---------------------------------------------------------------
    # Overdue APIs
    # ---------------------------------------------------------------
    "overdues": "/admin/overdues",
    "overdue_list": "/admin/overdue-list",

    # ---------------------------------------------------------------
    # Enquiry APIs
    # ---------------------------------------------------------------
    "show_enquiry": "/admin/show-enquiry",
    "enquiry_status_count": "/admin/enquiry-status-count",

    # ---------------------------------------------------------------
    # Lead APIs
    # ---------------------------------------------------------------
    "show_lead": "/admin/show-lead",
    "lead_count": "/admin/lead-count",

    # ---------------------------------------------------------------
    # Notification APIs
    # ---------------------------------------------------------------
    "list_notification": "/admin/list-notification",
    "notification_count": "/admin/get-notification-count",

    # ---------------------------------------------------------------
    # Recurring APIs
    # ---------------------------------------------------------------
    "get_recurring_data": "/admin/get-recurring-data",

    # ---------------------------------------------------------------
    # Account / Transaction APIs
    # ---------------------------------------------------------------
    "show_account": "/admin/show-account",
    "get_transaction_list": "/admin/get-transaction-list",

    # ---------------------------------------------------------------
    # Tax APIs
    # ---------------------------------------------------------------
    "get_tax_groups": "/admin/get-tax-groups",
    "get_tax": "/admin/get-tax",
    "get_tax_select": "/admin/get-tax-select",
    "get_tax_rate_name": "/admin/get-tax-rate-name",

    # ---------------------------------------------------------------
    # Provider APIs
    # ---------------------------------------------------------------
    "display_provider": "/admin/display-provider",
    "get_provider_select": "/admin/get-provider-for-select",

    # ---------------------------------------------------------------
    # Category APIs
    # ---------------------------------------------------------------
    "get_category_data": "/admin/get-category-data",
    "get_category_income": "/admin/get-category/income",
    "get_category_expense": "/admin/get-category/expense",
    "get_category_item": "/admin/get-category/item",
    "get_category_select": "/admin/get-category-select",

    # ---------------------------------------------------------------
    # Item APIs
    # ---------------------------------------------------------------
    "show_item": "/admin/show-item",
    "get_item_select": "/admin/get-item-select",
    "get_item_detail": "/admin/get-selected-item-detail",

    # ---------------------------------------------------------------
    # Agent APIs
    # ---------------------------------------------------------------
    "view_agent": "/admin/view-agent",
    "get_agent_payments": "/admin/get-agent-payments",

    # ---------------------------------------------------------------
    # Company APIs
    # ---------------------------------------------------------------
    "view_company": "/admin/view-company",
    "get_company_data": "/admin/get-company-data",
    "user_connection_data": "/admin/user-connection-data",

    # ---------------------------------------------------------------
    # Role / Permission APIs
    # ---------------------------------------------------------------
    "view_role": "/admin/view-role",
    "show_permission": "/admin/show-permission",

    # ---------------------------------------------------------------
    # Message / Communication APIs
    # ---------------------------------------------------------------
    "message_channel_show": "/admin/message-channel-show",
    "get_message_settings": "/admin/get-message-settings",
    "get_whatsapp_log": "/admin/get-whatsapp-sent-log",
    "get_sms_log": "/admin/get-message-sent-log",

    # ---------------------------------------------------------------
    # Header APIs
    # ---------------------------------------------------------------
    "get_header": "/admin/get-header",
    "get_header_select": "/admin/get-header-select",

    # ---------------------------------------------------------------
    # Vendor APIs
    # ---------------------------------------------------------------
    "get_vendor": "/admin/get-vendor",
    "get_vendor_select": "/admin/get-vendor-select",

    # ---------------------------------------------------------------
    # Expense APIs
    # ---------------------------------------------------------------
    "get_expense": "/admin/get-expense",
    "get_expense_details": "/admin/get-expense-details",

    # ---------------------------------------------------------------
    # Income APIs
    # ---------------------------------------------------------------
    "get_income": "/admin/get-income",
    "get_income_details": "/admin/get-income-details",

    # ---------------------------------------------------------------
    # Follow-up APIs
    # ---------------------------------------------------------------
    "show_followup": "/admin/show-followup",

    # ---------------------------------------------------------------
    # Problem Type APIs
    # ---------------------------------------------------------------
    "show_problem_type": "/admin/show-problem-type",
    "get_problem_type": "/admin/get-problem-type",

    # ---------------------------------------------------------------
    # Misc APIs
    # ---------------------------------------------------------------
    "get_currency_list": "/admin/get-currency-list",
    "get_languages": "/get-languages",
    "get_user_select": "/admin/get-user-select",
    "get_company_change_data": "/admin/get-company-change-data",
}


def get_endpoint(key: str) -> str:
    """Get an API endpoint path by its registry key.

    Args:
        key: The logical name of the API endpoint.

    Returns:
        The endpoint path string.

    Raises:
        KeyError: If the key is not found in the registry.
    """
    if key not in API_REGISTRY:
        raise KeyError(
            f"Unknown API endpoint: '{key}'. "
            f"Available endpoints: {', '.join(sorted(API_REGISTRY.keys()))}"
        )
    return API_REGISTRY[key]
