"""
Expenses & Income tools — functions for querying expenses, incomes, headers, and vendors.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_expenses() -> dict:
    """Get list of expenses.

    Returns:
        Expense list.
    """
    logger.info("Getting expenses list")
    return await api_client.get("get_expense")


async def get_incomes() -> dict:
    """Get list of incomes.

    Returns:
        Income list.
    """
    logger.info("Getting incomes list")
    return await api_client.get("get_income")


async def get_headers() -> dict:
    """Get list of revenue/expense headers.

    Returns:
        Headers list.
    """
    logger.info("Getting headers list")
    return await api_client.get("get_header")


async def get_vendors() -> dict:
    """Get list of vendors.

    Returns:
        Vendors list.
    """
    logger.info("Getting vendors list")
    return await api_client.get("get_vendor")
