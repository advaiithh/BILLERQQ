"""
Reports tools — functions for querying reports and analytics from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_dashboard_data() -> dict:
    """Get main dashboard data (recurring info, summary stats).

    Returns:
        Dashboard summary data.
    """
    logger.info("Getting dashboard data")
    return await api_client.get("get_dashboard_data")


async def get_connection_data() -> dict:
    """Get connection/subscription overview data for dashboard.

    Returns:
        Connection counts and stats.
    """
    logger.info("Getting connection data")
    return await api_client.get("get_connection_data")


async def get_package_report() -> dict:
    """Get package distribution report.

    Returns:
        Package report showing subscriber counts per package.
    """
    logger.info("Getting package report")
    return await api_client.get("package_report")


async def get_wallet_report() -> dict:
    """Get wallet balance report.

    Returns:
        Wallet report data.
    """
    logger.info("Getting wallet report")
    return await api_client.get("wallet_report")


async def get_tax_report() -> dict:
    """Get tax collection report.

    Returns:
        Tax report data.
    """
    logger.info("Getting tax report")
    return await api_client.get("tax_report")


async def get_addon_report() -> dict:
    """Get add-on subscription report.

    Returns:
        Add-on report data.
    """
    logger.info("Getting add-on report")
    return await api_client.get("addon_report")


async def get_subscription_report() -> dict:
    """Get subscription report.

    Returns:
        Subscription report data.
    """
    logger.info("Getting subscription report")
    return await api_client.get("subscription_report")


async def get_agent_collection_report(start_date: str | None = None, end_date: str | None = None) -> dict:
    """Get agent-wise collection report.

    Args:
        start_date: Optional start date in DD-MM-YYYY format
        end_date: Optional end date in DD-MM-YYYY format

    Returns:
        Agent collection summary.
    """
    logger.info("Getting agent collection report for dates: %s to %s", start_date, end_date)
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    return await api_client.get("agent_collection_report", params=params)


async def get_income_summary(month: str | None = None, year: str | None = None) -> dict:
    """Get income summary report.

    Args:
        month: Optional month name (e.g. "May")
        year: Optional year (e.g. "2026")

    Returns:
        Income summary data.
    """
    logger.info("Getting income summary report for month: %s, year: %s", month, year)
    params = {}
    if month:
        params["month"] = month
    if year:
        params["year"] = year
    return await api_client.get("income_summary_report", params=params)


async def get_expense_summary() -> dict:
    """Get expense summary report.

    Returns:
        Expense summary data.
    """
    logger.info("Getting expense summary report")
    return await api_client.get("expense_summary_report")


async def get_packages() -> dict:
    """Get all available packages.

    Returns:
        Package list.
    """
    logger.info("Getting packages")
    return await api_client.get("view_package")


async def get_areas() -> dict:
    """Get all areas/zones.

    Returns:
        Area list.
    """
    logger.info("Getting areas")
    return await api_client.get("view_area")


async def get_stb_status_count() -> dict:
    """Get set-top box status counts.

    Returns:
        STB status summary.
    """
    logger.info("Getting STB status count")
    return await api_client.get("stb_status_count")


async def get_stbs() -> dict:
    """Get all set-top boxes.

    Returns:
        STB list.
    """
    logger.info("Getting all set-top boxes")
    return await api_client.get("view_stb")
