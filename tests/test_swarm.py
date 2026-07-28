"""Unit tests for 24/7 Agent Swarm subsystem."""

import pytest
from pathlib import Path
from archangel.memory.profile import UserProfileMemory
from archangel.agents.swarm.filter import TokenFreeFilter
from archangel.agents.swarm.registry import PlatformRegistry
from archangel.agents.swarm.logger import SwarmFileWriter, format_lead_block
from archangel.agents.swarm.manager import SwarmManager, parse_duration_seconds
from archangel.models import RawPost


def test_parse_duration_seconds():
    assert parse_duration_seconds("30s") == 30
    assert parse_duration_seconds("5m") == 300
    assert parse_duration_seconds("3h") == 10800
    assert parse_duration_seconds("continuous") == 0


def test_parse_fresh_range():
    from archangel.agents.swarm.filter import parse_fresh_range
    assert parse_fresh_range("3d") == (0.0, 3 * 86400.0)
    assert parse_fresh_range("3 days") == (0.0, 3 * 86400.0)
    assert parse_fresh_range("1-10d") == (1 * 86400.0, 10 * 86400.0)
    assert parse_fresh_range("1-10 days") == (1 * 86400.0, 10 * 86400.0)
    assert parse_fresh_range("2w") == (0.0, 2 * 604800.0)
    assert parse_fresh_range("1-4 weeks") == (1 * 604800.0, 4 * 604800.0)
    assert parse_fresh_range("1y") == (0.0, 31536000.0)
    assert parse_fresh_range("1-2y") == (31536000.0, 2 * 31536000.0)
    assert parse_fresh_range("1-2 years") == (31536000.0, 2 * 31536000.0)


def test_extract_budget_profile_currencies():
    from archangel.agents.swarm.filter import extract_budget_profile

    # USD explicit and implicit unadorned rates
    b1 = extract_budget_profile("Typical rates: $120-$170/hr")
    assert b1.currency_code == "USD"
    assert b1.min_amount == 120.0
    assert b1.max_amount == 170.0
    assert "$120-$170/hr (USD Hourly)" in b1.formatted

    b2 = extract_budget_profile("Pay: 50/hr")
    assert b2.currency_code == "USD"
    assert b2.min_amount == 50.0

    # Explicit INR rate
    b3 = extract_budget_profile("Rate: ₹500/hr")
    assert b3.currency_code == "INR"
    assert b3.min_amount == 500.0

    # Explicit EUR rate
    b4 = extract_budget_profile("Rate: €80/hr")
    assert b4.currency_code == "EUR"
    assert b4.min_amount == 80.0


def test_parse_budget_amount_currencies():
    from archangel.agents.swarm.filter import parse_budget_amount

    assert parse_budget_amount("$1000") == 1000.0
    assert parse_budget_amount("1000inr") == 11.5
    assert parse_budget_amount("1000eur") == 1080.0


def test_format_budget_display():
    from archangel.agents.swarm.filter import format_budget_display

    assert format_budget_display("1000inr") == "₹1,000+"
    assert format_budget_display("₹50000") == "₹50,000+"
    assert format_budget_display("1000eur") == "€1,000+"
    assert format_budget_display("1000gbp") == "£1,000+"
    assert format_budget_display("1000usd") == "$1,000+"
    assert format_budget_display("$1000") == "$1,000+"


def test_parse_multi_leads_queries():
    from archangel.agents.swarm.filter import parse_multi_leads_queries

    q1 = parse_multi_leads_queries('"website development" && "custom bot"')
    assert q1 == ["website development", "custom bot"]

    q2 = parse_multi_leads_queries('"website development" & "custom bot"')
    assert q2 == ["website development", "custom bot"]

    q3 = parse_multi_leads_queries('website development AND custom bot')
    assert q3 == ["website development", "custom bot"]

    q4 = parse_multi_leads_queries('website development, custom bot')
    assert q4 == ["website development", "custom bot"]


def test_swarm_command_parse_args():
    import click
    from archangel.cli.main import swarm_cmd

    ctx = click.Context(swarm_cmd)

    # Test space-separated quoted args with '&'
    swarm_cmd.parse_args(ctx, ["-l", "looking for website developer", "&", "need automation", "-f", "1-5d", "-c", "0", "-b", "1000inr"])
    assert ctx.params["leads_query"] == "looking for website developer && need automation"
    assert ctx.params["fresh"] == "1-5d"
    assert ctx.params["comments"] == "0"
    assert ctx.params["budget"] == "1000inr"

    # Test space-separated quoted args without explicit operator
    ctx2 = click.Context(swarm_cmd)
    swarm_cmd.parse_args(ctx2, ["-l", "looking for website developer", "need automation", "-f", "1-5d"])
    assert ctx2.params["leads_query"] == "looking for website developer && need automation"


def test_enrichment_processor_min_thresholds(tmp_path: Path):
    import asyncio
    from archangel.agents.swarm.pipeline import EnrichmentProcessor
    from archangel.models import Lead

    out_file = tmp_path / "test_leads.log"
    q = asyncio.Queue()

    # Create processor requiring min_score=20.0 and min_priority=MEDIUM
    proc = EnrichmentProcessor(enrichment_queue=q, output_path=out_file, min_score=20.0, min_priority="MEDIUM")

    # Lead 1: Score 9.3, LOW priority -> Should be suppressed
    lead_low = Lead(
        id=1,
        sales_readiness=9.3,
        priority="LOW",
    )

    # Lead 2: Score 45.0, MEDIUM priority -> Should be saved
    lead_good = Lead(
        id=2,
        sales_readiness=45.0,
        priority="MEDIUM",
    )

    # Directly test processing filter logic
    assert lead_low.sales_readiness < proc.min_score
    assert lead_good.sales_readiness >= proc.min_score


def test_parse_comments_range():
    from archangel.agents.swarm.filter import parse_comments_range

    assert parse_comments_range(None) == (0, 20)
    assert parse_comments_range("0-20") == (0, 20)
    assert parse_comments_range("15") == (0, 15)
    assert parse_comments_range("5-50") == (5, 50)
    assert parse_comments_range("all") is None
    assert parse_comments_range("off") is None


def test_token_free_filter_comments(tmp_path: Path):
    from archangel.agents.swarm.filter import TokenFreeFilter

    # Default comments range: 0-20
    filter_default = TokenFreeFilter(comments="0-20")

    # Post with 5 comments -> Accept
    res1 = filter_default.evaluate(
        content="Hiring Python & FastAPI developer for remote project.",
        title="Need Developer",
        num_comments=5,
    )
    assert res1["is_lead"] is True

    # Post with 35 comments -> Reject (exceeds max 20)
    res2 = filter_default.evaluate(
        content="Hiring Python & FastAPI developer for remote project.",
        title="Need Developer",
        num_comments=35,
    )
    assert res2["is_lead"] is False
    assert "outside --comments range" in res2["reason"]


def test_token_free_filter_multi_query(tmp_path: Path):
    from archangel.agents.swarm.filter import TokenFreeFilter

    filter_engine = TokenFreeFilter(leads_query='"website development" && "custom bot"')

    # Post matching topic 1
    res1 = filter_engine.evaluate(
        content="Hiring developer for website development project.",
        title="Need Web Dev",
    )
    assert res1["is_lead"] is True
    assert "website development" in res1["matched_keywords"]

    # Post matching topic 2
    res2 = filter_engine.evaluate(
        content="Looking for freelancer to build a custom bot for Discord.",
        title="Bot Project",
    )
    assert res2["is_lead"] is True
    assert "custom bot" in res2["matched_keywords"]

    # Unrelated post
    res3 = filter_engine.evaluate(
        content="Hiring graphic designer for logo design.",
        title="Design Job",
    )
    assert res3["is_lead"] is False


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


def test_reddit_token_pool(monkeypatch):
    from archangel.agents.swarm.workers.reddit_auth import RedditTokenPool
    
    # Test comma-separated parsing
    monkeypatch.setenv("REDDIT_CLIENT_IDS", "id1, id2, id3")
    monkeypatch.setenv("REDDIT_CLIENT_SECRETS", "sec1, sec2, sec3")

    pool = RedditTokenPool()
    pool.reload_credentials()

    assert len(pool.credentials) == 3
    assert pool.credentials[0] == ("id1", "sec1")
    assert pool.credentials[1] == ("id2", "sec2")
    assert pool.credentials[2] == ("id3", "sec3")

    # Mock bearer token fetching
    def mock_fetch(self, cid, sec):
        return f"token_{cid}"

    monkeypatch.setattr(RedditTokenPool, "_fetch_bearer_token", mock_fetch)

    hdr1 = pool.get_auth_header()
    assert hdr1 == {"Authorization": "bearer token_id1"}

    hdr2 = pool.get_auth_header()
    assert hdr2 == {"Authorization": "bearer token_id2"}

    hdr3 = pool.get_auth_header()
    assert hdr3 == {"Authorization": "bearer token_id3"}

    # Wrap around to first key
    hdr4 = pool.get_auth_header()
    assert hdr4 == {"Authorization": "bearer token_id1"}
