"""Unit tests for UserProfileMemory engine and you.txt bullet parsing."""

import pytest
from pathlib import Path
from archangel.memory.profile import UserProfileMemory
from archangel.models import LeadAnalysis
from archangel.scoring.learning import AdaptiveScorer


def test_user_profile_memory_parsing(tmp_path: Path):
    you_txt = tmp_path / "you.txt"
    you_txt.write_text(
        "1. I build web apps in Python, FastAPI, and React\n"
        "2. I specialize in scraping bots and automation\n"
        "3. I prefer remote work with budget > $2,000\n"
        "4. I do NOT want WordPress or PHP jobs\n",
        encoding="utf-8"
    )

    mem = UserProfileMemory(file_path=you_txt)

    assert "python" in mem.positive_keywords
    assert "fastapi" in mem.positive_keywords
    assert "react" in mem.positive_keywords
    assert "wordpress" in mem.negative_keywords
    assert "php" in mem.negative_keywords
    assert mem.min_budget == 2000.0


def test_evaluate_lead_positive(tmp_path: Path):
    you_txt = tmp_path / "you.txt"
    you_txt.write_text(
        "1. I build web apps in Python and FastAPI\n"
        "2. Budget over $1000\n",
        encoding="utf-8"
    )
    mem = UserProfileMemory(file_path=you_txt)

    res = mem.evaluate_lead(
        tags=["Python", "FastAPI"],
        category="Backend",
        content="Hiring FastAPI dev for microservices",
        estimated_budget="$5000",
    )

    assert res["is_excluded"] is False
    assert res["score_modifier"] > 0.0


def test_evaluate_lead_exclusion(tmp_path: Path):
    you_txt = tmp_path / "you.txt"
    you_txt.write_text(
        "1. I do NOT want WordPress or PHP\n",
        encoding="utf-8"
    )
    mem = UserProfileMemory(file_path=you_txt)

    res = mem.evaluate_lead(
        tags=["PHP", "WordPress"],
        category="CMS",
        content="Need WordPress plugin maintenance",
    )

    assert res["is_excluded"] is True
    assert res["score_modifier"] == -50.0


def test_adaptive_scorer_with_profile(tmp_path: Path):
    you_txt = tmp_path / "you.txt"
    you_txt.write_text(
        "1. I build Python and FastAPI bots\n"
        "2. Budget over $1,000\n",
        encoding="utf-8"
    )
    mem = UserProfileMemory(file_path=you_txt)
    scorer = AdaptiveScorer(profile_memory=mem)

    analysis = LeadAnalysis(
        raw_post_id=1,
        is_lead=True,
        confidence=0.9,
        estimated_budget="$5000",
        urgency="high",
        category="Backend Python",
        tags=["Python", "FastAPI", "Bots"],
    )

    score = scorer.score_analysis(analysis)
    assert score.score > 70.0
