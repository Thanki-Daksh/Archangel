"""Unit tests for TelegramSwarmBot commands and live telemetry dashboard."""

import pytest
from archangel.notifications.telegram_bot import TelegramSwarmBot, render_telegram_dashboard
from archangel.storage import StorageBackend


@pytest.fixture
def temp_storage(tmp_path):
    db_path = tmp_path / "test_telegram.db"
    return StorageBackend(db_path=str(db_path))


@pytest.mark.asyncio
async def test_telegram_bot_help(temp_storage):
    bot = TelegramSwarmBot(storage=temp_storage)
    res = await bot.handle_command("/help")
    assert "ARCHANGEL TELEGRAM BOT COMMANDS" in res
    assert "/swarm_start" in res
    assert "/swarm_live" in res


@pytest.mark.asyncio
async def test_telegram_bot_status_and_live(temp_storage):
    bot = TelegramSwarmBot(storage=temp_storage)
    status_res = await bot.handle_command("/swarm_status")
    assert "ARCHANGEL AGENT SWARM TELEMETRY" in status_res
    assert "Scanned Posts:" in status_res

    live_res = await bot.handle_command("/swarm_live")
    assert "Live Telemetry Dashboard Activated" in live_res
    assert bot._is_live is True

    # Toggle off
    live_off = await bot.handle_command("/swarm_live")
    assert "paused" in live_off
    assert bot._is_live is False


@pytest.mark.asyncio
async def test_telegram_bot_swarm_lifecycle(temp_storage):
    bot = TelegramSwarmBot(storage=temp_storage)
    start_res = await bot.handle_command("/swarm_start 30s")
    assert "Agent Swarm Launched" in start_res
    assert bot.swarm_manager is not None
    assert bot.swarm_manager.is_running is True

    # Stop swarm
    stop_res = await bot.handle_command("/swarm_stop")
    assert "Agent Swarm Stopped Cleanly" in stop_res
    assert bot.swarm_manager.is_running is False


def test_render_telegram_dashboard():
    metrics = {
        "scanned_count": 150,
        "qualified_count": 12,
        "discovery_queue_size": 5,
        "storage_queue_size": 0,
        "total_flushed": 12,
        "total_failed": 0,
        "avg_flush_duration_ms": 14.5,
    }
    rendered = render_telegram_dashboard(metrics, elapsed=125, duration_str="3h", active=True)
    assert "150" in rendered
    assert "12" in rendered
    assert "00:02:05" in rendered
    assert "🟢 RUNNING" in rendered
