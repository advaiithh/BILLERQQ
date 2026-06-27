"""
Communication tools — functions for querying SMS and WhatsApp logs from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_sms_logs() -> dict:
    """Get SMS sent logs.

    Returns:
        SMS logs.
    """
    logger.info("Getting SMS sent logs")
    return await api_client.get("get_sms_log")


async def get_whatsapp_logs() -> dict:
    """Get WhatsApp sent logs.

    Returns:
        WhatsApp logs.
    """
    logger.info("Getting WhatsApp sent logs")
    return await api_client.get("get_whatsapp_log")
