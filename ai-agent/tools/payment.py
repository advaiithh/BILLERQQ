"""
Payment tools — functions for querying payment data from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_payment_history(customer_id: int) -> dict:
    """Get payment history for a specific customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        Payment history records.
    """
    logger.info("Getting payment history for customer ID: %d", customer_id)
    return await api_client.get("payment_history", params={"customer_id": customer_id})


async def get_recent_payments() -> dict:
    """Get recent payments across the system.

    Returns:
        List of recent payment transactions.
    """
    logger.info("Getting recent payments")
    from datetime import datetime, timedelta
    
    now = datetime.now()
    anchor = now
    if now.year < 2026:
        anchor = datetime(2026, 6, 27)
        
    start_date = (anchor - timedelta(days=30)).strftime("%d-%m-%Y")
    end_date = anchor.strftime("%d-%m-%Y")
    
    agent_payments = []
    try:
        res_agent = await api_client.get("agent_collection_report", params={
            "page": 1,
            "page_length": 50,
            "start_date": start_date,
            "end_date": end_date
        })
        if isinstance(res_agent, dict) and res_agent.get("status"):
            agent_payments = res_agent.get("data", {}).get("payments", {}).get("data", [])
    except Exception:
        logger.exception("Failed to fetch agent collection payments for recent payments")
        
    online_payments = []
    try:
        res_online = await api_client.get("get_online_payment", params={
            "page": 1,
            "page_length": 50
        })
        if isinstance(res_online, dict) and res_online.get("status"):
            online_payments = res_online.get("data", {}).get("data", [])
    except Exception:
        logger.exception("Failed to fetch online payments for recent payments")
        
    merged = []
    for p in agent_payments:
        dt_str = p.get("paid_date") or p.get("created_date") or ""
        try:
            dt = datetime.strptime(dt_str, "%d-%B-%Y")
        except Exception:
            dt = datetime.min
            
        merged.append({
            "name": p.get("customer_name") or "Unknown",
            "customer_name": p.get("customer_name") or "Unknown",
            "amount": p.get("collected_amount") or 0.0,
            "paid_amount": p.get("collected_amount") or 0.0,
            "payment_date": dt_str,
            "created_at": dt_str,
            "payment_method": p.get("account_name") or "Cash",
            "method": p.get("account_name") or "Cash",
            "subscriber_id": p.get("subscriber_id") or "N/A",
            "invoice_no": p.get("invoice_no") or "N/A",
            "type": "Agent Cash",
            "_parsed_date": dt
        })
        
    for p in online_payments:
        dt_str = p.get("paid_date") or ""
        try:
            dt = datetime.strptime(dt_str, "%d-%B-%Y")
        except Exception:
            dt = datetime.min
            
        merged.append({
            "name": p.get("customer_name") or "Unknown",
            "customer_name": p.get("customer_name") or "Unknown",
            "amount": p.get("paid_amount") or 0.0,
            "paid_amount": p.get("paid_amount") or 0.0,
            "payment_date": dt_str,
            "created_at": dt_str,
            "payment_method": "Online",
            "method": "Online",
            "subscriber_id": p.get("subscriber_id") or "N/A",
            "invoice_no": p.get("invoice_no") or "N/A",
            "type": "Online",
            "_parsed_date": dt
        })
        
    merged.sort(key=lambda x: x["_parsed_date"], reverse=True)
    
    return {
        "status": True,
        "message": "success",
        "data": {
            "data": merged,
            "total": len(merged)
        }
    }


async def get_unpaid_customers() -> dict:
    """Get list of customers with unpaid/overdue payments.

    Returns:
        Unpaid customer report data.
    """
    logger.info("Getting unpaid customers")
    return await api_client.get("get_unpaid_customers")


async def get_payment_due_data() -> dict:
    """Get payment due collection data.

    Returns:
        Payment due summary.
    """
    logger.info("Getting payment due data")
    return await api_client.get("get_payment_due")


async def get_overdues() -> dict:
    """Get overdue summary data.

    Returns:
        Overdue summary/counts.
    """
    logger.info("Getting overdue summary")
    return await api_client.get("overdues")


async def get_overdue_list() -> dict:
    """Get detailed list of all overdue payments.

    Returns:
        Detailed overdue payment records.
    """
    logger.info("Getting overdue list")
    return await api_client.get("overdue_list")


async def get_customer_payment_report() -> dict:
    """Get customer payment report.

    Returns:
        Payment report data.
    """
    logger.info("Getting customer payment report")
    return await api_client.get("get_customer_payment_report")


async def get_online_payments() -> dict:
    """Get online payment data.

    Returns:
        Online payment records.
    """
    logger.info("Getting online payment data")
    return await api_client.get("get_online_payment")


async def get_payment_receipt(payment_id: int) -> dict:
    """Get a specific payment receipt.

    Args:
        payment_id: The payment/transaction ID.

    Returns:
        Payment receipt details.
    """
    logger.info("Getting payment receipt for ID: %d", payment_id)
    return await api_client.get("get_payment_receipt", params={"id": payment_id})


async def get_invoices(customer_id: int | None = None, **kwargs) -> dict:
    """Get all invoices/orders across the system or for a specific customer.

    Args:
        customer_id: Optional customer ID to filter by.
        **kwargs: Extra query parameters for status filtering.

    Returns:
        List of invoices/orders.
    """
    logger.info("Getting invoices, customer_id: %s, kwargs: %s", customer_id, kwargs)
    params = {}
    params.update(kwargs)
    if customer_id:
        params["customer_id"] = customer_id
        return await api_client.get("show_single_order", params=params)
    return await api_client.get("show_order", params=params)


async def get_cancelled_invoices() -> dict:
    """Get all cancelled invoices.

    Returns:
        Cancelled invoice records.
    """
    logger.info("Getting cancelled invoices")
    return await api_client.get("cancelled_invoice")

