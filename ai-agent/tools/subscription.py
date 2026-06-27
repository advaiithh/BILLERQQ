"""
Subscription tools — functions for querying subscription data from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_subscription(customer_id: int) -> dict:
    """Get active subscriptions for a customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        Customer subscription data.
    """
    logger.info("Getting subscription for customer ID: %d", customer_id)
    return await api_client.get("show_subscription", params={"customer_id": customer_id})


async def get_subscription_history(customer_id: int) -> dict:
    """Get subscription change history for a customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        Subscription history records.
    """
    logger.info("Getting subscription history for customer ID: %d", customer_id)
    return await api_client.get("subscription_history", params={"customer_id": customer_id})


async def get_single_subscription(subscription_id: int) -> dict:
    """Get details of a specific subscription.

    Args:
        subscription_id: The subscription ID.

    Returns:
        Single subscription details.
    """
    logger.info("Getting single subscription ID: %d", subscription_id)
    return await api_client.get("get_single_subscription", params={"id": subscription_id})


async def get_pending_subscriptions() -> dict:
    """Get list of pending (not yet activated) subscriptions.

    Returns:
        Pending subscription list.
    """
    logger.info("Getting pending subscriptions")
    return await api_client.get("get_pending_subscriptions")


async def get_subscription_report() -> dict:
    """Get subscription report data.

    Returns:
        Subscription report with analytics.
    """
    logger.info("Getting subscription report")
    return await api_client.get("subscription_report")


async def get_addon(customer_id: int) -> dict:
    """Get add-on subscriptions for a customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        Add-on data for the customer.
    """
    logger.info("Getting add-ons for customer ID: %d", customer_id)
    return await api_client.get("show_single_addon", params={"customer_id": customer_id})


async def get_addon_history(customer_id: int) -> dict:
    """Get add-on subscription history for a customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        Add-on history records.
    """
    logger.info("Getting add-on history for customer ID: %d", customer_id)
    return await api_client.get("addon_history", params={"customer_id": customer_id})


async def get_items() -> dict:
    """Get all items.

    Returns:
        List of items.
    """
    logger.info("Getting all items")
    return await api_client.get("show_item")


async def get_all_addons() -> dict:
    """Get all add-ons.

    Returns:
        Add-ons list.
    """
    logger.info("Getting all add-ons")
    return await api_client.get("show_addon")
