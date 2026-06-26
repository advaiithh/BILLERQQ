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
    return await api_client.get("get_recent_payment")


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


async def get_invoices(customer_id: int | None = None) -> dict:
    """Get all invoices/orders across the system or for a specific customer.

    Args:
        customer_id: Optional customer ID to filter by.

    Returns:
        List of invoices/orders.
    """
    logger.info("Getting invoices, customer_id: %s", customer_id)
    if customer_id:
        return await api_client.get("show_single_order", params={"customer_id": customer_id})
    return await api_client.get("show_order")

