"""VaultAgent — Event subscriber that syncs lead updates into the Obsidian Markdown Vault."""

import logging
from typing import Optional, Dict

from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend
from archangel.vault.builder import VaultBuilder

logger = logging.getLogger(__name__)


class VaultAgent:
    """Subscribes to lead lifecycle, enrichment, and outreach events to maintain Obsidian vault notes."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        builder: Optional[VaultBuilder] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.builder = builder or VaultBuilder()
        self._drafts_cache: Dict[int, dict] = {}

        self.event_bus.subscribe("lead.enriched", self._on_lead_enriched)
        self.event_bus.subscribe("outreach.drafts_generated", self._on_drafts_generated)
        self.event_bus.subscribe("lead.lifecycle_changed", self._on_lifecycle_changed)
        self.event_bus.subscribe("lead.merged", self._on_lead_merged)
        logger.debug("VaultAgent initialized and subscribed to vault sync events")

    def _on_lead_merged(self, payload: dict) -> None:
        canonical_lead_id = payload.get("canonical_lead_id")
        merged_post_id = payload.get("merged_post_id")
        if canonical_lead_id:
            self._sync_lead_note(canonical_lead_id)

    def _on_lead_enriched(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        enrichment = payload.get("enrichment", {})
        if raw_post_id:
            self._sync_lead_note(raw_post_id, enrichment=enrichment)

    def _on_drafts_generated(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        drafts = payload.get("drafts", {})
        if raw_post_id and drafts:
            self._drafts_cache[raw_post_id] = drafts
            self._sync_lead_note(raw_post_id, drafts=drafts)

    def _on_lifecycle_changed(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        new_status = payload.get("new_status", "discovered")
        if raw_post_id:
            self._sync_lead_note(raw_post_id, status=new_status)

    def _sync_lead_note(
        self,
        raw_post_id: int,
        status: str = "discovered",
        enrichment: Optional[dict] = None,
        drafts: Optional[dict] = None,
    ) -> None:
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

        if not enrichment:
            enrichment = self.storage.get_enrichment(raw_post_id) or {}

        if not drafts:
            drafts = self._drafts_cache.get(raw_post_id, {})

        history = self.storage.get_lead_lifecycle(raw_post_id)
        if history and status == "discovered":
            status = history[-1]["status"]

        self.builder.build_lead_note(
            post=post,
            raw_post_id=raw_post_id,
            status=status,
            enrichment=enrichment,
            drafts=drafts,
        )
        logger.info("Synced lead note for #%d into Obsidian vault", raw_post_id)
