"""LifecycleAgent — Event-driven subscriber for tracking lead lifecycle progression."""

import logging
from typing import Optional

from archangel.events import EventBus
from archangel.lifecycle.engine import LifecycleEngine
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class LifecycleAgent:
    """Subscribes to lead lifecycle events and auto-advances or updates lead status."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        engine: Optional[LifecycleEngine] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.engine = engine or LifecycleEngine()

        self.event_bus.subscribe("raw_post.stored", self._on_post_discovered)
        self.event_bus.subscribe("lead.analyzed", self._on_lead_analyzed)
        self.event_bus.subscribe("lead.status_updated", self._on_status_updated)
        logger.debug("LifecycleAgent initialized and subscribed to event bus")

    def _on_post_discovered(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        if raw_post_id:
            self.update_status(raw_post_id, "discovered", notes="Auto-registered on raw post store")

    def _on_lead_analyzed(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        if raw_post_id:
            self.update_status(raw_post_id, "analyzed", notes="Auto-advanced post AI analysis")

    def _on_status_updated(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        status = payload.get("status")
        notes = payload.get("notes", "")
        if raw_post_id and status:
            self.update_status(raw_post_id, status, notes)

    def update_status(self, raw_post_id: int, status: str, notes: str = "") -> bool:
        if not self.engine.is_valid_state(status):
            logger.warning("Invalid lifecycle status '%s' for post #%d", status, raw_post_id)
            return False

        history = self.storage.get_lead_lifecycle(raw_post_id)
        current_status = history[-1]["status"] if history else ""

        if current_status and not self.engine.can_transition(current_status, status):
            logger.warning("Invalid transition '%s' -> '%s' for lead #%d", current_status, status, raw_post_id)

        self.storage.update_lead_status(raw_post_id, status, notes=notes)
        self.event_bus.publish(
            "lead.lifecycle_changed",
            {
                "raw_post_id": raw_post_id,
                "previous_status": current_status,
                "new_status": status,
                "notes": notes,
            },
        )
        logger.info("Updated lead #%d lifecycle status: %s -> %s", raw_post_id, current_status or "none", status)
        return True
