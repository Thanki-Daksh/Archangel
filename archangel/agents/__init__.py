"""Autonomous agents — each owns one responsibility."""

import logging

logger = logging.getLogger(__name__)


class GuardianAgent:
    """Supervisor that monitors health of the platform."""

    def __init__(self) -> None:
        logger.debug("GuardianAgent created.")


class CommanderAgent:
    """Orchestrator for startup, shutdown, and command routing."""

    def __init__(self) -> None:
        logger.debug("CommanderAgent created.")
