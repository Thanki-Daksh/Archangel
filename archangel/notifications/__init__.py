"""Message delivery — sends completed leads through configured channels."""

import logging

logger = logging.getLogger(__name__)


class NotificationAgent:
    """Delivers opportunities via Telegram, Discord, Email, or Desktop."""

    def __init__(self) -> None:
        logger.debug("NotificationAgent created.")
