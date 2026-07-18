import logging
from typing import Any, Dict, List

logger = logging.getLogger("billerq-reducer")

def compact_api_result(tool: str, data: Any) -> Any:
    """Recursively prunes and truncates tool output JSON data to stay within token budgets."""
    if not isinstance(data, dict):
        return data

    # Check if this is an API error response, return as is
    if "error" in data:
        return {"error": data["error"]}

    # Extract total/pagination meta if present
    total = data.get("total")
    if not total and isinstance(data.get("meta"), dict):
        total = data["meta"].get("total")
    if not total and isinstance(data.get("data"), dict):
        total = data["data"].get("total")

    # 1. Customers
    if tool in ("get_all_customers", "search_customer"):
        raw_items = []
        if isinstance(data.get("data"), list):
            raw_items = data["data"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), list):
            raw_items = data["data"]["data"]
        elif isinstance(data, list):
            raw_items = data
        else:
            raw_items = []

        items = raw_items[:5]
        return {
            "total": total or len(raw_items),
            "items": [
                {
                    "id": item.get("id"),
                    "name": item.get("name") or item.get("customer_name"),
                    "subscriber_id": item.get("subscriber_id"),
                    "status": item.get("status"),
                    "mobile": item.get("mobile"),
                    "area_name": item.get("area_name") or item.get("area"),
                }
                for item in items
            ]
        }

    # 2. Complaints
    elif tool == "get_complaints":
        raw_items = []
        if isinstance(data.get("data"), list):
            raw_items = data["data"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), list):
            raw_items = data["data"]["data"]
        elif isinstance(data, list):
            raw_items = data

        items = raw_items[:5]
        return {
            "total": total or len(raw_items),
            "items": [
                {
                    "id": item.get("id"),
                    "status": item.get("status"),
                    "customer_name": item.get("customer_name"),
                    "mobile": item.get("mobile"),
                    "problem_type": item.get("problem_type") or item.get("complaint_type"),
                    "created_at": item.get("created_at"),
                }
                for item in items
            ]
        }

    # 3. Payments and Collections
    elif tool in ("get_recent_payments", "get_payment_history"):
        raw_items = []
        if isinstance(data.get("data"), list):
            raw_items = data["data"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), list):
            raw_items = data["data"]["data"]
        elif isinstance(data, list):
            raw_items = data

        items = raw_items[:5]
        return {
            "total": total or len(raw_items),
            "items": [
                {
                    "invoice_no": item.get("invoice_no") or item.get("invoice_number"),
                    "amount": item.get("amount") or item.get("paid_amount"),
                    "payment_date": item.get("payment_date") or item.get("created_at"),
                    "payment_method": item.get("payment_method") or item.get("method"),
                    "subscriber_id": item.get("subscriber_id"),
                    "customer_name": item.get("name") or item.get("customer_name"),
                }
                for item in items
            ]
        }

    # 4. Invoices
    elif tool == "get_invoices":
        raw_items = []
        if isinstance(data.get("data"), list):
            raw_items = data["data"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("data"), list):
            raw_items = data["data"]["data"]
        elif isinstance(data, list):
            raw_items = data

        items = raw_items[:5]
        return {
            "total": total or len(raw_items),
            "items": [
                {
                    "id": item.get("id"),
                    "invoice_no": item.get("invoice_no"),
                    "invoice_prefix": item.get("invoice_prefix"),
                    "amount": item.get("amount") or item.get("balance"),
                    "payment_status": item.get("payment_status") or item.get("order_status"),
                    "invoice_date": item.get("invoice_date") or item.get("created_date"),
                    "subscriber_id": item.get("subscriber_id"),
                    "customer_name": item.get("customer_name"),
                }
                for item in items
            ]
        }

    # 5. Subscriptions
    elif tool == "get_subscription":
        raw_items = []
        if isinstance(data.get("data"), list):
            raw_items = data["data"]
        elif isinstance(data, list):
            raw_items = data

        items = raw_items[:5]
        return {
            "total": total or len(raw_items),
            "items": [
                {
                    "package_name": item.get("package_name"),
                    "stb_no": item.get("stb_no"),
                    "status": item.get("status"),
                    "plan_date": item.get("plan_date") or item.get("start_date"),
                    "recurring_date": item.get("recurring_date") or item.get("end_date"),
                    "invoice_number": item.get("invoice_number"),
                }
                for item in items
            ]
        }

    # Generic fallback: search for lists inside dict values and truncate them to max length 5
    reduced = {}
    for key, value in data.items():
        if isinstance(value, list):
            reduced[key] = value[:5]
        elif isinstance(value, dict):
            reduced[key] = compact_api_result(tool, value)
        else:
            reduced[key] = value

    if total is not None and "total" not in reduced:
        reduced["total"] = total

    return reduced
