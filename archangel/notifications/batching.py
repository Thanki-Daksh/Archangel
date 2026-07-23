"""Smart Notification Batching & Digest Engine."""

import logging
import time
from typing import List, Dict, Any, Optional
from archangel.events import EventBus
from archangel.models import RawPost, LeadScore

logger = logging.getLogger(__name__)


class BatchingAgent:
    """Batches low-priority lead notifications (<80 score) into digests while immediately pushing high-priority leads (>80)."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        high_priority_threshold: float = 80.0,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.high_priority_threshold = high_priority_threshold
        self.pending_batch: List[Dict[str, Any]] = []

        self.event_bus.subscribe("lead.scored", self._on_lead_scored)
        logger.debug("BatchingAgent initialized (threshold=%.1f)", high_priority_threshold)

    def _on_lead_scored(self, payload: dict) -> None:
        score_val = float(payload.get("score", 0.0))
        raw_post_id = payload.get("raw_post_id")

        item = {
            "raw_post_id": raw_post_id,
            "score": score_val,
            "timestamp": time.time(),
        }

        if score_val >= self.high_priority_threshold:
            # Immediate high-priority dispatch
            self.event_bus.publish(
                "notification.immediate",
                {
                    "raw_post_id": raw_post_id,
                    "score": score_val,
                    "reason": f"High priority score ({score_val:.1f} >= {self.high_priority_threshold})",
                },
            )
            logger.info("Immediate notification published for lead #%d (score: %.1f)", raw_post_id, score_val)
        else:
            # Queue for batch digest
            self.pending_batch.append(item)
            logger.debug("Queued lead #%d in batch digest (score: %.1f)", raw_post_id, score_val)

    def flush_digest(self) -> Dict[str, Any]:
        """Flushes queued low-priority leads into a batch digest event."""
        if not self.pending_batch:
            return {"count": 0, "leads": []}

        digest_items = list(self.pending_batch)
        self.pending_batch.clear()

        digest = {
            "count": len(digest_items),
            "leads": digest_items,
            "generated_at": time.time(),
        }

        self.event_bus.publish("notification.digest", digest)
        logger.info("Flushed notification digest containing %d leads", len(digest_items))
        return digest
