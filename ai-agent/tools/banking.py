"""
Banking tools — functions for querying accounts and transactions from BillerQ.
"""

import logging

from api.client import api_client

logger = logging.getLogger(__name__)


async def get_accounts() -> dict:
    """Get all bank/cash accounts.

    Returns:
        Accounts list.
    """
    logger.info("Getting accounts")
    return await api_client.get("show_account")


async def get_transactions() -> dict:
    """Get banking transactions list.

    Returns:
        Transactions list.
    """
    logger.info("Getting transactions")
    return await api_client.get("get_transaction_list")
