"""Source-specific collectors — gather raw information from the internet."""

import logging

logger = logging.getLogger(__name__)


class CollectorAgent:
    """Gathers raw information from configured sources."""

    def __init__(self) -> None:
        logger.debug("CollectorAgent created.")
