"""Unit tests for TelegramSwarmBot and PersonalInstructionsStore (Batch 1)."""

import pytest
from pathlib import Path
from archangel.config.personal_instructions import PersonalInstructionsStore
from archangel.agents.swarm.telegram_bot import TelegramSwarmBot


def test_personal_instructions_store(tmp_path: Path):
    config_file = tmp_path / "user_instructions.json"
    store = PersonalInstructionsStore(config_path=config_file)

    assert "Next.js" in store.data["preferred_stack"]
    ctx = store.get_pitch_context()
    assert "Developer Bio" in ctx

    res = store.update_instruction("Focus on building Fast-API + Next.js SaaS MVPs under 2 weeks.")
    assert "Updated personal instructions" in res
    assert store.data["custom_instructions"] == "Focus on building Fast-API + Next.js SaaS MVPs under 2 weeks."
    assert config_file.exists()


def test_telegram_bot_keyboards():
    bot = TelegramSwarmBot(token="TEST_TOKEN", chat_id="123456")
    kb = bot.build_lead_inline_keyboard(target_url="https://reddit.com/r/forhire/comments/123456")

    assert "inline_keyboard" in kb
    rows = kb["inline_keyboard"]
    assert len(rows) == 2

    row0 = rows[0]
    assert row0[0]["text"] == "💬 DM Client"
    assert row0[0]["url"] == "https://reddit.com/r/forhire/comments/123456"
    assert row0[1]["text"] == "⚡ Quick Pitch"
    assert "pitch:" in row0[1]["callback_data"]


def test_telegram_bot_quick_pitch(tmp_path: Path):
    config_file = tmp_path / "user_instructions.json"
    store = PersonalInstructionsStore(config_path=config_file)
    store.update_instruction("Specializing in fast Python microservices.")

    bot = TelegramSwarmBot(token="TEST_TOKEN", chat_id="123456")
    bot.instructions_store = store

    pitch = bot.generate_quick_pitch(post_text="Need Senior Python Developer for scraping pipeline")
    assert "Python" in pitch or "Next.js" in pitch
    assert "architecture" in pitch.lower()


def test_natural_language_swarm_cmd():
    bot = TelegramSwarmBot(token="TEST_TOKEN", chat_id="123456")
    msg = "btw bro can you start the agent swarm? i need 1k workers, intermediate level, i look for 15k inr budget"
    parsed = bot.parse_natural_language_swarm_cmd(msg)

    assert parsed["is_swarm_cmd"] is True
    assert parsed["action"] == "start"
    assert parsed["workers"] == 1000
    assert parsed["budget"] == "15kinr"
    assert "intermediate" in parsed["tiers"]

