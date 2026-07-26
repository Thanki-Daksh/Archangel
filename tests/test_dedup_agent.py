from archangel.deduplication.agent import DeduplicationAgent
from archangel.events import EventBus
from archangel.models import RawPost
from archangel.storage import StorageBackend


def test_deduplication_agent_event_flow(tmp_path):
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test.db")
    DeduplicationAgent(event_bus=bus, storage=storage)

    p1 = RawPost(
        source="reddit",
        content="Need Python developer for AI bot",
        url="http://reddit.com/bot1",
    )
    id1 = storage.store_raw_post(p1)

    events_received = []
    bus.subscribe("lead.*", lambda payload: events_received.append(payload))

    p2 = RawPost(
        source="discord",
        content="Need Python developer for AI bot",
        url="http://discord.com/bot1",
    )
    id2 = storage.store_raw_post(p2)
    p2.id = id2

    bus.publish("raw_post.stored", {"post": p2, "raw_post_id": id2})

    assert len(events_received) > 0
    assert any(e.get("action") == "merged" for e in events_received)
    assert events_received[0]["canonical_lead_id"] == id1
    storage.close()
