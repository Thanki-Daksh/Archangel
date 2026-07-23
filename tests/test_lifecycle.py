import pytest
from archangel.events import EventBus
from archangel.lifecycle.agent import LifecycleAgent
from archangel.lifecycle.engine import LifecycleEngine
from archangel.models import RawPost
from archangel.storage import StorageBackend


def test_lifecycle_engine_states():
    engine = LifecycleEngine()
    assert engine.is_valid_state("discovered")
    assert engine.is_valid_state("paid")
    assert not engine.is_valid_state("unknown_state")

    assert engine.can_transition("discovered", "analyzed")
    assert engine.can_transition("contacted", "responded")


def test_lifecycle_agent_flow(tmp_path):
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test_lifecycle.db")
    agent = LifecycleAgent(event_bus=bus, storage=storage)

    post = RawPost(source="reddit", content="Need Flutter Dev", url="http://reddit.com/flutter")
    post_id = storage.store_raw_post(post)

    events = []
    bus.subscribe("lead.lifecycle_changed", lambda p: events.append(p))

    # 1. Post discovered
    bus.publish("raw_post.stored", {"raw_post_id": post_id})
    assert len(events) == 1
    assert events[0]["new_status"] == "discovered"

    # 2. Update status to contacted
    success = agent.update_status(post_id, "contacted", notes="Sent DM on Reddit")
    assert success
    assert len(events) == 2
    assert events[1]["new_status"] == "contacted"

    history = storage.get_lead_lifecycle(post_id)
    assert len(history) == 2
    assert history[0]["status"] == "discovered"
    assert history[1]["status"] == "contacted"

    storage.close()
