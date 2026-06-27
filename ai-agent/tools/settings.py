"""
Settings tools — functions for querying settings from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_message_settings() -> dict:
    """Get message settings / message credit info.

    Returns:
        Message settings/channel info.
    """
    logger.info("Getting message settings")
    return await api_client.get("get_message_settings")


async def get_providers() -> dict:
    """Get CAS/ISP providers list.

    Returns:
        Providers details.
    """
    logger.info("Getting providers list")
    return await api_client.get("display_provider")


async def get_categories() -> dict:
    """Get all settings categories.

    Returns:
        Categories list.
    """
    logger.info("Getting categories")
    return await api_client.get("get_category_data")


async def get_tax_classes() -> dict:
    """Get tax classes list.

    Returns:
        Tax class details.
    """
    logger.info("Getting tax classes")
    return await api_client.get("get_tax")
