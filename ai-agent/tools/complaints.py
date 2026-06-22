"""
Complaints tools — functions for querying complaint data from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_complaints() -> dict:
    """Get all complaints.

    Returns:
        List of complaints with details.
    """
    logger.info("Getting complaints")
    return await api_client.get("get_complaint")


async def get_complaint_status_count() -> dict:
    """Get complaint counts grouped by status.

    Returns:
        Status-wise complaint counts (open, resolved, etc.).
    """
    logger.info("Getting complaint status counts")
    return await api_client.get("complaint_status_count")


async def get_problem_types() -> dict:
    """Get available problem type categories for complaints.

    Returns:
        List of problem types.
    """
    logger.info("Getting problem types")
    return await api_client.get("get_problem_types")
