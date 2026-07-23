import pytest
from archangel.enrichment.agent import EnrichmentAgent
from archangel.enrichment.engine import EnrichmentEngine
from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend


def test_enrichment_engine():
    engine = EnrichmentEngine()
    post = RawPost(
        source="reddit",
        author="acme_corp",
        content="We are hiring a Python & FastAPI developer at https://acme-inc.io! Github: https://github.com/acme",
        url="http://reddit.com/r/forhire/123",
    )
    res = engine.enrich_post(post)

    assert res["domain"] == "acme-inc.io"
    assert res["company_name"] == "Acme-inc"
    assert "Python" in res["detected_tech"]
    assert len(res["social_links"]) == 1
    assert res["social_links"][0]["platform"] == "github"
    assert res["social_links"][0]["handle"] == "acme"


def test_enrichment_agent_and_storage(tmp_path):
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test_enrichment.db")
    agent = EnrichmentAgent(event_bus=bus, storage=storage)

    post = RawPost(
        source="discord",
        author="dev_lead",
        content="Looking for React and Node.js dev for https://myagency.net",
        url="http://discord.gg/job1",
    )
    post_id = storage.store_raw_post(post)
    post.id = post_id

    events = []
    bus.subscribe("lead.enriched", lambda payload: events.append(payload))

    bus.publish("raw_post.stored", {"post": post, "raw_post_id": post_id})

    assert len(events) == 1
    assert events[0]["raw_post_id"] == post_id

    stored_enrichment = storage.get_enrichment(post_id)
    assert stored_enrichment is not None
    assert stored_enrichment["domain"] == "myagency.net"
    assert "JavaScript/TypeScript" in stored_enrichment["detected_tech"]

    storage.close()
