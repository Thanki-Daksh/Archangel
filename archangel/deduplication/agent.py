"""DeduplicationAgent — Event-driven subscriber for real-time lead deduplication."""

import logging
from typing import Optional

from archangel.deduplication.engine import DeduplicationEngine
from archangel.events import EventBus
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class DeduplicationAgent:
    """Subscribes to 'raw_post.stored' events, evaluates incoming posts, and merges duplicates."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        engine: Optional[DeduplicationEngine] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.engine = engine or DeduplicationEngine(storage=self.storage)

        self.event_bus.subscribe("raw_post.stored", self._on_raw_post_stored)
        logger.debug("DeduplicationAgent initialized and subscribed to raw_post.stored")

    def _on_raw_post_stored(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        post = payload.get("post")

        if not post or not raw_post_id:
            return

        post.id = raw_post_id
        res = self.engine.evaluate_post(post)

        if res.action == "merge" and res.target_lead_id:
            self.storage.link_lead_source(
                canonical_lead_id=res.target_lead_id,
                raw_post_id=raw_post_id,
                confidence=res.confidence,
                merge_reason=res.reason,
                tier_used=res.tier,
            )
            self.event_bus.publish(
                "lead.merged",
                {
                    "canonical_lead_id": res.target_lead_id,
                    "merged_post_id": raw_post_id,
                    "confidence": res.confidence,
                    "reason": res.reason,
                    "tier": res.tier,
                    "action": "merged",
                },
            )
            logger.info(
                "Merged post #%d into canonical lead #%d (%s)",
                raw_post_id,
                res.target_lead_id,
                res.reason,
            )
        else:
            self.event_bus.publish(
                "lead.deduped.passed",
                {
                    "raw_post_id": raw_post_id,
                    "action": "created",
                },
            )
