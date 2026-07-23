"""Market Trend Analytics Engine — computes top tech trends, budget distribution, and platform lead volumes."""

import logging
from collections import Counter
from typing import Dict, List, Any, Optional
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """Aggregates lead data into actionable market intelligence reports."""

    def __init__(self, storage: Optional[StorageBackend] = None) -> None:
        self.storage = storage or StorageBackend.get_instance()

    def generate_market_report(self) -> Dict[str, Any]:
        leads = self.storage.get_leads(limit=500)
        total_leads = len(leads)

        source_counts: Counter = Counter()
        urgency_counts: Counter = Counter()
        tech_counts: Counter = Counter()

        for lead in leads:
            source = lead.get("source") or "unknown"
            source_counts[source] += 1

            urgency = lead.get("urgency") or "medium"
            urgency_counts[urgency] += 1

            # Fetch enrichment if available
            raw_post_id = lead.get("id")
            if raw_post_id:
                enrichment = self.storage.get_enrichment(raw_post_id)
                if enrichment and enrichment.get("detected_tech"):
                    for t in enrichment["detected_tech"]:
                        tech_counts[t] += 1

        return {
            "total_leads_analyzed": total_leads,
            "leads_by_source": dict(source_counts),
            "urgency_distribution": dict(urgency_counts),
            "top_tech_stacks": dict(tech_counts.most_common(10)),
        }
