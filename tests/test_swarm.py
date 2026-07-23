"""Unit tests for 24/7 Agent Swarm subsystem."""

import pytest
import asyncio
from pathlib import Path
from archangel.memory.profile import UserProfileMemory
from archangel.agents.swarm.filter import TokenFreeFilter
from archangel.agents.swarm.registry import PlatformRegistry
from archangel.agents.swarm.logger import SwarmFileWriter, format_lead_block
from archangel.agents.swarm.pipeline import StoragePipeline
from archangel.agents.swarm.pool import SwarmPool
from archangel.agents.swarm.manager import SwarmManager, parse_duration_seconds
from archangel.models import RawPost


def test_parse_duration_seconds():
    assert parse_duration_seconds("30s") == 30
    assert parse_duration_seconds("5m") == 300
    assert parse_duration_seconds("3h") == 10800
    assert parse_duration_seconds("continuous") == 0


def test_token_free_filter(tmp_path: Path):
    you_txt = tmp_path / "you.txt"
    you_txt.write_text(
        "1. I build Python and FastAPI apps\n"
        "2. I do NOT want WordPress\n",
        encoding="utf-8"
    )
    profile = UserProfileMemory(file_path=you_txt)
    filter_engine = TokenFreeFilter(profile_memory=profile)

    # Lead post
    res1 = filter_engine.evaluate(
        content="Hiring Senior Python & FastAPI developer for remote project.",
        title="Need Developer",
    )
    assert res1["is_lead"] is True
    assert res1["confidence"] >= 0.60
    assert "python" in res1["matched_keywords"]

    # Excluded post
    res2 = filter_engine.evaluate(
        content="Hiring WordPress developer for site theme.",
        title="WordPress Job",
    )
    assert res2["is_lead"] is False
    assert res2["is_excluded"] is True


def test_platform_registry():
    registry = PlatformRegistry()
    targets = registry.resolve_targets("reddit.com,r/forhire,upwork.com,https://mycustomsite.com/jobs")
    
    assert len(targets) > 3
    assert any(t.platform == "reddit" for t in targets)
    assert any(t.platform == "rss" for t in targets)
    assert any(t.platform == "custom" for t in targets)


def test_swarm_file_writer(tmp_path: Path):
    """Test SwarmFileWriter writes formatted lead blocks to file."""
    out_file = tmp_path / "swarm.log"
    writer = SwarmFileWriter(output_path=out_file)

    post = RawPost(
        source="reddit",
        channel="forhire",
        author="client_john",
        content="Hiring Python developer",
        url="https://reddit.com/r/forhire/101",
    )

    block = format_lead_block(post, {"confidence": 0.85, "matched_keywords": ["python"]}, 1)
    writer.write_batch([block])
    writer.close()

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "client_john" in content
    assert "0.85" in content
    assert "LEAD #00001" in content


@pytest.mark.asyncio
async def test_swarm_manager_short_run(tmp_path: Path):
    out_file = tmp_path / "swarm_test.log"
    manager = SwarmManager(
        duration="5s",
        output_path=out_file,
        targets="r/forhire,upwork.com",
        max_workers=5,
    )

    await manager.run()
    assert out_file.exists()
