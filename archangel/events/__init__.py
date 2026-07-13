"""Event bus — communication backbone for agents and subsystems."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EventBus:
    """Simple in-memory event bus placeholder.

    The real implementation will support pub/sub, filtering, and
    async delivery to registered handlers.
    """

    _instance: "EventBus | None" = None

    def __init__(self) -> None:
        self._handlers: dict[str, list[callable]] = {}
        logger.debug("EventBus initialized.")

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        logger.debug("Event published: %s", event_type)

    def subscribe(self, event_type: str, handler: callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: callable) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)


class GuardianAgent:
    """Supervisor that monitors health of the platform."""

    def __init__(self) -> None:
        logger.debug("GuardianAgent created.")


class CommanderAgent:
    """Orchestrator for startup, shutdown, and command routing."""

    def __init__(self) -> None:
        logger.debug("CommanderAgent created.")
