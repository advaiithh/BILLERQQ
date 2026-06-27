"""
Lead tools — functions for querying lead, enquiry, and follow-up data from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_enquiries() -> dict:
    """Get all enquiries.

    Returns:
        Enquiry list.
    """
    logger.info("Getting enquiries")
    return await api_client.get("show_enquiry")


async def get_enquiry_status_count() -> dict:
    """Get enquiry status count.

    Returns:
        Enquiry status counts.
    """
    logger.info("Getting enquiry status count")
    return await api_client.get("enquiry_status_count")


async def get_leads() -> dict:
    """Get all leads.

    Returns:
        Lead list.
    """
    logger.info("Getting leads")
    return await api_client.get("show_lead")


async def get_lead_count() -> dict:
    """Get lead status wise count.

    Returns:
        Lead count details.
    """
    logger.info("Getting lead count")
    return await api_client.get("lead_count")


async def get_followups() -> dict:
    """Get all follow-ups.

    Returns:
        Follow-up list.
    """
    logger.info("Getting followups")
    return await api_client.get("show_followup")
