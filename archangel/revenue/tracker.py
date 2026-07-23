"""Revenue & ROI Tracker — calculates total earnings, average deal size, and platform ROI."""

import logging
from typing import Dict, List, Any, Optional
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class RevenueTracker:
    """Tracks conversions, total revenue, average deal size, and source-level ROI."""

    def __init__(self, storage: Optional[StorageBackend] = None) -> None:
        self.storage = storage or StorageBackend.get_instance()

    def record_conversion(self, raw_post_id: int, amount: float, source: str = "", notes: str = "") -> int:
        rec_id = self.storage.store_revenue(
            raw_post_id=raw_post_id,
            amount=amount,
            source=source,
            notes=notes,
        )
        logger.info("Recorded revenue conversion of $%.2f for lead #%d (source: %s)", amount, raw_post_id, source)
        return rec_id

    def get_summary(self) -> Dict[str, Any]:
        records = self.storage.get_revenue_records()
        total_revenue = sum(r["amount"] for r in records)
        count = len(records)
        avg_deal_size = total_revenue / count if count > 0 else 0.0

        by_source: Dict[str, float] = {}
        for r in records:
            src = r.get("source") or "unknown"
            by_source[src] = by_source.get(src, 0.0) + r["amount"]

        return {
            "total_revenue": round(total_revenue, 2),
            "converted_leads_count": count,
            "average_deal_size": round(avg_deal_size, 2),
            "revenue_by_source": {k: round(v, 2) for k, v in by_source.items()},
        }
