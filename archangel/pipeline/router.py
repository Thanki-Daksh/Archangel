"""MultiPipelineRouter — Routes classified signals to dedicated intelligence streams."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from archangel.events import EventBus
from archangel.models import Lead, LeadType
from archangel.agents.swarm.logger import format_lead_block

logger = logging.getLogger(__name__)

PIPELINE_STREAMS = {
    LeadType.SALES_LEAD: Path("data/swarm_leads.log"),
    LeadType.HIRING_SIGNAL: Path("data/hiring_intelligence.log"),
    LeadType.FUNDING_EVENT: Path("data/funding_tracker.log"),
    LeadType.PRODUCT_LAUNCH: Path("data/product_launches.log"),
    LeadType.FEATURE_REQUEST: Path("data/feature_requests.log"),
    LeadType.PAIN_DISCUSSION: Path("data/market_pains.log"),
    LeadType.COMPANY_INTELLIGENCE: Path("data/company_intelligence.log"),
    LeadType.UNKNOWN: Path("data/unclassified_signals.log"),
}


class MultiPipelineRouter:
    """Subscribes to 'lead.enriched' events and dispatches records to targeted pipeline files."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.event_bus.subscribe("lead.enriched", self._on_lead_enriched)
        logger.debug("MultiPipelineRouter initialized and subscribed to 'lead.enriched'")

    def _on_lead_enriched(self, payload: dict) -> None:
        lead = payload.get("lead")
        raw_post_id = payload.get("raw_post_id", 0)
        if not lead or not isinstance(lead, Lead):
            return

        target_file = PIPELINE_STREAMS.get(lead.lead_type, PIPELINE_STREAMS[LeadType.UNKNOWN])
        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            formatted_block = format_lead_block(lead, raw_post_id=raw_post_id)
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(formatted_block + "\n\n")
            logger.info("Dispatched Lead #%d [%s] to pipeline stream '%s'", raw_post_id, lead.lead_type.value, target_file)
        except Exception as exc:
            logger.error("Failed to write lead to pipeline stream '%s': %s", target_file, exc)
