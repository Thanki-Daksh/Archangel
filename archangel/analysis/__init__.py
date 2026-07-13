"""AI reasoning logic — converts raw posts into structured understanding."""

import logging

logger = logging.getLogger(__name__)


class IntelligenceAgent:
    """The reasoning engine. Analyses raw posts for lead potential."""

    def __init__(self) -> None:
        logger.debug("IntelligenceAgent created.")
