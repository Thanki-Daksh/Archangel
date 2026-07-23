"""EnrichmentAgent — Event-driven agent that listens for posts and enriches lead metadata."""

import logging
from typing import Optional

from archangel.enrichment.engine import EnrichmentEngine
from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    """Subscribes to 'raw_post.stored' or 'lead.deduped.passed' events and persists enriched lead details."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        engine: Optional[EnrichmentEngine] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.engine = engine or EnrichmentEngine()

        self.event_bus.subscribe("raw_post.stored", self._on_raw_post_stored)
        self.event_bus.subscribe("lead.deduped.passed", self._on_lead_deduped_passed)
        logger.debug("EnrichmentAgent initialized and subscribed to event bus")

    def _on_raw_post_stored(self, payload: dict) -> None:
        post = payload.get("post")
        raw_post_id = payload.get("raw_post_id")
        if post and raw_post_id:
            self._process_enrichment(post, raw_post_id)

    def _on_lead_deduped_passed(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        if raw_post_id:
            # Check if post exists in storage
            leads = self.storage.get_leads(limit=100)
            target = next((r for r in leads if r.get("id") == raw_post_id), None)
            if target:
                p = RawPost(
                    source=target.get("source", ""),
                    channel=target.get("channel", ""),
                    author=target.get("author", ""),
                    content=target.get("content", ""),
                    url=target.get("url", ""),
                    metadata={},
                )
                self._process_enrichment(p, raw_post_id)

    def _process_enrichment(self, post: RawPost, raw_post_id: int) -> dict:
        enriched = self.engine.enrich_post(post)
        self.storage.store_enrichment(
            raw_post_id=raw_post_id,
            domain=enriched["domain"],
            company_name=enriched["company_name"],
            detected_tech=enriched["detected_tech"],
            social_links=enriched["social_links"],
            enrichment_data=enriched["enrichment_data"],
        )
        self.event_bus.publish(
            "lead.enriched",
            {
                "raw_post_id": raw_post_id,
                "enrichment": enriched,
            },
        )
        logger.info("Enriched lead #%d (company: %s, tech: %s)", raw_post_id, enriched["company_name"], enriched["detected_tech"])
        return enriched
