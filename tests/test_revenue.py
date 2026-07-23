import pytest
from archangel.revenue.tracker import RevenueTracker
from archangel.storage import StorageBackend


def test_revenue_tracker(tmp_path):
    storage = StorageBackend(db_path=tmp_path / "test_revenue.db")
    tracker = RevenueTracker(storage=storage)

    tracker.record_conversion(raw_post_id=1, amount=5000.0, source="reddit", notes="FastAPI project")
    tracker.record_conversion(raw_post_id=2, amount=3000.0, source="discord", notes="React project")
    tracker.record_conversion(raw_post_id=3, amount=2000.0, source="reddit", notes="Python script")

    summary = tracker.get_summary()

    assert summary["total_revenue"] == 10000.0
    assert summary["converted_leads_count"] == 3
    assert summary["average_deal_size"] == 3333.33
    assert summary["revenue_by_source"]["reddit"] == 7000.0
    assert summary["revenue_by_source"]["discord"] == 3000.0

    storage.close()
