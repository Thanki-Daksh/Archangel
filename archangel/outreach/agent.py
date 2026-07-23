"""OutreachAgent — Event-driven subscriber for generating pitch drafts upon lead enrichment."""

import logging
from typing import Optional

from archangel.events import EventBus
from archangel.models import RawPost
from archangel.outreach.engine import OutreachEngine
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class OutreachAgent:
    """Subscribes to 'lead.enriched' / 'raw_post.stored' to auto-generate pitch drafts."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        engine: Optional[OutreachEngine] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.engine = engine or OutreachEngine()

        self.event_bus.subscribe("lead.enriched", self._on_lead_enriched)
        logger.debug("OutreachAgent initialized and subscribed to lead.enriched")

    def _on_lead_enriched(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        enrichment = payload.get("enrichment", {})

        if not raw_post_id:
            return

        leads = self.storage.get_leads(limit=100)
        target = next((r for r in leads if r.get("id") == raw_post_id), None)
        if not target:
            return

        post = RawPost(
            source=target.get("source", ""),
            channel=target.get("channel", ""),
            author=target.get("author", ""),
            content=target.get("content", ""),
            url=target.get("url", ""),
            metadata={},
        )
        post.id = raw_post_id

        drafts = self.engine.generate_drafts(post, enrichment=enrichment)

        self.event_bus.publish(
            "outreach.drafts_generated",
            {
                "raw_post_id": raw_post_id,
                "drafts": drafts,
            },
        )
        logger.info("Generated outreach drafts for lead #%d (%s)", raw_post_id, list(drafts.keys()))
