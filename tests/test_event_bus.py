"""Unit tests for EventBus, GuardianAgent, and CommanderAgent."""

import pytest
from archangel.events import EventBus, GuardianAgent, CommanderAgent


@pytest.fixture(autouse=True)
def reset_event_bus():
    EventBus.reset_instance()
    yield
    EventBus.reset_instance()


def test_event_bus_singleton():
    bus1 = EventBus.get_instance()
    bus2 = EventBus.get_instance()
    assert bus1 is bus2


def test_event_bus_pub_sub():
    bus = EventBus.get_instance()
    received = []

    def handler(payload):
        received.append(payload)

    bus.subscribe("lead.discovered", handler)
    bus.publish("lead.discovered", {"url": "https://example.com/job1"})

    assert len(received) == 1
    assert received[0]["url"] == "https://example.com/job1"


def test_event_bus_wildcard_subscriber():
    bus = EventBus.get_instance()
    received = []

    def wildcard_handler(payload):
        received.append(payload)

    bus.subscribe("agent.*", wildcard_handler)
    bus.publish("agent.started", {"agent": "collector"})
    bus.publish("agent.stopped", {"agent": "collector"})

    assert len(received) == 2
    assert received[0]["agent"] == "collector"
    assert received[1]["agent"] == "collector"


def test_event_bus_handler_error_isolation():
    bus = EventBus.get_instance()
    received = []

    def bad_handler(payload):
        raise ValueError("Simulated handler crash")

    def good_handler(payload):
        received.append(payload)

    bus.subscribe("test.event", bad_handler)
    bus.subscribe("test.event", good_handler)

    # Publishing should not raise even if bad_handler crashes
    bus.publish("test.event", {"data": 123})
    assert len(received) == 1


def test_event_bus_history():
    bus = EventBus.get_instance()
    bus.publish("lead.discovered", {"id": 1})
    bus.publish("agent.started", {"id": 2})

    history = bus.get_history()
    assert len(history) >= 2


def test_guardian_agent_health_tracking():
    bus = EventBus.get_instance()
    guardian = GuardianAgent(event_bus=bus)

    guardian.record_heartbeat("collector")
    guardian.record_failure("collector", "Timeout error")

    health = guardian.get_system_health()
    assert "collector" in health["last_heartbeats"]
    assert health["error_counts"]["collector"] == 1


def test_commander_agent_lifecycle():
    bus = EventBus.get_instance()
    commander = CommanderAgent(event_bus=bus)

    commander.register_agent("collector")
    assert commander.start_agent("collector") is True
    assert commander.get_agent_states()["collector"] == "running"

    assert commander.stop_agent("collector") is True
    assert commander.get_agent_states()["collector"] == "stopped"
