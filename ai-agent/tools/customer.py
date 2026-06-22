"""
Customer tools — functions for querying customer data from BillerQ.
"""

import logging
from typing import Optional

from api.client import api_client

logger = logging.getLogger(__name__)


async def search_customer(query: str) -> dict:
    """Search for customers by name, mobile, or subscriber ID.

    Args:
        query: Search term (name, phone number, etc.).

    Returns:
        API response with matching customers.
    """
    logger.info("Searching customer: '%s'", query)
    return await api_client.get("get_customer_search", params={"search_value": query})


async def get_customer_profile(customer_id: int) -> dict:
    """Get detailed profile for a specific customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        Full customer profile data.
    """
    logger.info("Getting profile for customer ID: %d", customer_id)
    return await api_client.get("get_customer_profile", params={"customer_id": customer_id})


async def get_all_customers(page: int = 1) -> dict:
    """Get all customers (paginated).

    Args:
        page: Page number for pagination.

    Returns:
        List of customers.
    """
    logger.info("Getting all customers, page %d", page)
    return await api_client.get("show_customer", params={"page": page})


async def get_single_customer(customer_id: int) -> dict:
    """Get a single customer's basic details.

    Args:
        customer_id: The customer's ID.

    Returns:
        Customer basic data.
    """
    logger.info("Getting single customer ID: %d", customer_id)
    return await api_client.get("get_customer", params={"customer_id": customer_id})


async def get_customers_by_area(area_name: str) -> dict:
    """Get all customers, then filter by area name.

    Since the API doesn't have a direct area filter endpoint,
    we fetch all and filter client-side.

    Args:
        area_name: The area name to filter by (case-insensitive).

    Returns:
        Filtered customer data matching the area.
    """
    logger.info("Getting customers by area: '%s'", area_name)
    response = await api_client.get("show_customer")

    # Try to filter the response by area
    if isinstance(response, dict):
        # Handle paginated response with 'data' key
        customers = response.get("data", response.get("customers", []))
        if isinstance(customers, list):
            filtered = [
                c for c in customers
                if area_name.lower() in str(c.get("area_name", "")).lower()
                or area_name.lower() in str(c.get("area", "")).lower()
            ]
            return {"data": filtered, "total": len(filtered), "area_filter": area_name}

    return response


async def get_customer_status_count() -> dict:
    """Get count of customers grouped by status (active, inactive, etc.).

    Returns:
        Status-wise customer counts.
    """
    logger.info("Getting customer status counts")
    return await api_client.get("get_customer_status_count")


async def get_customer_list() -> dict:
    """Get customer list for selection/dropdowns.

    Returns:
        Simplified customer list.
    """
    logger.info("Getting customer list")
    return await api_client.get("get_customer_list")


async def get_archived_customers() -> dict:
    """Get archived/deleted customers.

    Returns:
        List of archived customers.
    """
    logger.info("Getting archived customers")
    return await api_client.get("get_archived_customer")


async def get_customer_stb(customer_id: int) -> dict:
    """Get set-top boxes assigned to a customer.

    Args:
        customer_id: The customer's ID.

    Returns:
        STB data for the customer.
    """
    logger.info("Getting STBs for customer ID: %d", customer_id)
    return await api_client.get("get_single_stb", params={"customer_id": customer_id})
