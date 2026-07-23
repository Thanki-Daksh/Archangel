import pytest
from archangel.events import EventBus
from archangel.models import RawPost, LeadAnalysis
from archangel.outreach.agent import OutreachAgent
from archangel.outreach.engine import OutreachEngine
from archangel.storage import StorageBackend


def test_outreach_engine_drafts():
    engine = OutreachEngine()
    post = RawPost(
        source="reddit",
        author="john_doe",
        content="Hiring FastAPI dev for microservices",
        url="http://reddit.com/job1",
    )
    analysis = LeadAnalysis(tags=["FastAPI", "Python"])
    enrichment = {"company_name": "AcmeInc", "detected_tech": ["FastAPI", "Python"]}

    drafts = engine.generate_drafts(post, analysis=analysis, enrichment=enrichment)

    assert "email" in drafts
    assert "discord" in drafts
    assert "telegram" in drafts
    assert "linkedin" in drafts
    assert "AcmeInc" in drafts["email"]
    assert "FastAPI" in drafts["discord"]


def test_outreach_agent_event_flow(tmp_path):
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test_outreach.db")
    agent = OutreachAgent(event_bus=bus, storage=storage)

    post = RawPost(source="discord", author="client_x", content="Need React dev", url="http://discord.gg/1")
    post_id = storage.store_raw_post(post)

    events = []
    bus.subscribe("outreach.drafts_generated", lambda p: events.append(p))

    bus.publish("lead.enriched", {"raw_post_id": post_id, "enrichment": {"company_name": "AgencyX", "detected_tech": ["React"]}})

    assert len(events) == 1
    assert events[0]["raw_post_id"] == post_id
    assert "email" in events[0]["drafts"]

    storage.close()
