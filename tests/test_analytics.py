import pytest
from archangel.analytics.engine import AnalyticsEngine
from archangel.models import RawPost
from archangel.storage import StorageBackend


def test_analytics_engine(tmp_path):
    storage = StorageBackend(db_path=tmp_path / "test_analytics.db")
    engine = AnalyticsEngine(storage=storage)

    p1 = RawPost(source="reddit", content="Python FastAPI dev needed", url="http://reddit.com/1")
    p2 = RawPost(source="github", content="React TypeScript developer", url="http://github.com/1")
    id1 = storage.store_raw_post(p1)
    id2 = storage.store_raw_post(p2)

    storage.store_enrichment(id1, domain="reddit.com", detected_tech=["Python", "FastAPI"])
    storage.store_enrichment(id2, domain="github.com", detected_tech=["React", "TypeScript"])

    report = engine.generate_market_report()

    assert report["total_leads_analyzed"] == 2
    assert report["leads_by_source"]["reddit"] == 1
    assert report["leads_by_source"]["github"] == 1
    assert "Python" in report["top_tech_stacks"]
    assert "React" in report["top_tech_stacks"]

    storage.close()
