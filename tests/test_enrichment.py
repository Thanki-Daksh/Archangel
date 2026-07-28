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

    assert res["company_profile"]["domain"]["value"] == "acme-inc.io"
    assert res["company_profile"]["company_name"]["value"] == "Acme-inc"
    assert "Python" in res["detected_tech"]
    assert "github" in res["company_profile"]["socials"]["value"]
    assert res["company_profile"]["socials"]["value"]["github"] == "acme"


def test_enrichment_agent_and_storage(tmp_path):
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test_enrichment.db")
    EnrichmentAgent(event_bus=bus, storage=storage)

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


def test_pitch_generator_priority():
    from archangel.enrichment.pitch import PitchGenerator

    gen = PitchGenerator()

    # Case 1: Has website health issues < 80 AND explicit Pain -> MUST choose Pain Resolution angle
    enriched_data = {
        "website_health": {"score": 40, "sales_hooks": ["Missing OpenGraph"]},
        "pain_categories": [{"name": "API Integration"}],
        "detected_tech": ["Python"],
        "company_profile": {"company_name": {"value": "Acme Corp"}},
    }
    pitch1 = gen.generate(enriched_data)
    assert pitch1.angle_type == "Pain Resolution"
    assert "tackling api integration challenges" in pitch1.opening_line.lower()

    # Case 2: Has website health issues < 80 AND Tech -> MUST choose Tech Specific angle over Health
    enriched_data2 = {
        "website_health": {"score": 40, "sales_hooks": ["Missing OpenGraph"]},
        "pain_categories": [],
        "detected_tech": ["Python"],
        "company_profile": {"company_name": {"value": "Beta LLC"}},
    }
    pitch2 = gen.generate(enriched_data2)
    assert pitch2.angle_type == "Tech Specific"
    assert "actively working with python" in pitch2.opening_line.lower()

    # Case 3: Has ONLY website health issues -> Fall back to Performance & Health angle
    enriched_data3 = {
        "website_health": {"score": 40, "sales_hooks": ["Missing OpenGraph"]},
        "pain_categories": [],
        "detected_tech": [],
        "company_profile": {"company_name": {"value": "Gamma Inc"}},
    }
    pitch3 = gen.generate(enriched_data3)
    assert pitch3.angle_type == "Performance & Health"
    assert "missing opengraph" in pitch3.opening_line.lower()
