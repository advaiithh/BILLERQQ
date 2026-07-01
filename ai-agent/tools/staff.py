"""
Staff and Role tools — functions for querying staff and roles data from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_staff() -> dict:
    """Get staff/agents list.

    Returns:
        Staff/agents details.
    """
    logger.info("Getting staff list")
    return await api_client.get("view_agent")


async def get_roles() -> dict:
    """Get roles.

    Returns:
        List of roles.
    """
    logger.info("Getting roles")
    return await api_client.get("view_role")
