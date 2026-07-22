import pytest
from archangel.agents.groupchat import GroupChatEngine, AGENT_ROLES


def test_groupchat_engine_init():
    engine = GroupChatEngine()
    assert engine.max_turns_per_round == 4
    assert len(engine.history) == 0
    prompt = engine.get_group_system_prompt()
    assert "ARCHANGEL MULTI-AGENT GROUPCHAT" in prompt
    assert "archangel.agents.commander" in prompt


def test_parse_turns_structured():
    engine = GroupChatEngine()
    raw = (
        "[archangel.agents.commander]: Starting evaluation of scraping goal.\n"
        "[archangel.agents.collector]: I found 3 RSS feeds for Python dev leads.\n"
        "[archangel.agents.intelligence]: Verified 2 high-intent leads.\n"
    )
    turns = engine._parse_turns(raw)
    assert len(turns) == 3
    assert turns[0]["agent"] == "commander"
    assert turns[0]["text"] == "Starting evaluation of scraping goal."
    assert turns[1]["agent"] == "collector"
    assert turns[1]["text"] == "I found 3 RSS feeds for Python dev leads."
    assert turns[2]["agent"] == "intelligence"
    assert turns[2]["text"] == "Verified 2 high-intent leads."


def test_parse_turns_fallback():
    engine = GroupChatEngine()
    raw = "Generic response without agent tags"
    turns = engine._parse_turns(raw)
    assert len(turns) == 1
    assert turns[0]["agent"] == "commander"
    assert turns[0]["text"] == "Generic response without agent tags"
