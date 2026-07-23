import pytest
from archangel.events import EventBus
from archangel.notifications.batching import BatchingAgent


def test_batching_agent_immediate_vs_digest():
    bus = EventBus()
    agent = BatchingAgent(event_bus=bus, high_priority_threshold=80.0)

    immediate_events = []
    digest_events = []

    bus.subscribe("notification.immediate", lambda p: immediate_events.append(p))
    bus.subscribe("notification.digest", lambda p: digest_events.append(p))

    # High priority lead (>80)
    bus.publish("lead.scored", {"raw_post_id": 1, "score": 95.0})
    assert len(immediate_events) == 1
    assert len(agent.pending_batch) == 0

    # Low priority lead (<80)
    bus.publish("lead.scored", {"raw_post_id": 2, "score": 65.0})
    assert len(immediate_events) == 1
    assert len(agent.pending_batch) == 1

    # Flush digest
    digest = agent.flush_digest()
    assert digest["count"] == 1
    assert len(digest_events) == 1
    assert len(agent.pending_batch) == 0
