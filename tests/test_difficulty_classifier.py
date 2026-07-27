"""Unit tests for LeadDifficultyClassifier and difficulty level CLI filtering."""

import pytest
from archangel.models import DifficultyTier, RawPost
from archangel.enrichment.difficulty import LeadDifficultyClassifier
from archangel.enrichment.agent import EnrichmentAgent
from archangel.agents.swarm.filter import filter_by_difficulty


@pytest.fixture
def classifier():
    return LeadDifficultyClassifier()


@pytest.fixture
def agent():
    return EnrichmentAgent()


def test_beginner_no_experience_required(classifier):
    text = "Looking for a freelancer to build a Python web scraper script. Budget: $500."
    res = classifier.evaluate(text, budget=500.0)

    assert res.tier == DifficultyTier.BEGINNER
    assert res.experience_years == 0
    assert "No experience requirement listed on post (0 years)" in res.reasons


def test_intermediate_experience(classifier):
    text = "Need a full stack developer with 2+ years of experience in FastAPI and React to build an MVP dashboard."
    res = classifier.evaluate(text, budget=3000.0)

    assert res.tier == DifficultyTier.INTERMEDIATE
    assert res.experience_years == 2


def test_pro_experience(classifier):
    text = "Stripe is hiring a Senior Backend Engineer. Qualifications: 5+ years of experience building microservices and distributed systems."
    res = classifier.evaluate(text, budget=12000.0)

    assert res.tier == DifficultyTier.PRO
    assert res.experience_years == 5


def test_master_experience(classifier):
    text = "Hedge fund seeking Principal Architect with 10+ years of experience in low latency C++ trading systems."
    res = classifier.evaluate(text, budget=30000.0)

    assert res.tier == DifficultyTier.MASTER
    assert res.experience_years == 10


def test_difficulty_filtering_utility():
    assert filter_by_difficulty("beginner", {"beginner"}) is True
    assert filter_by_difficulty("pro", {"beginner"}) is False
    assert filter_by_difficulty("intermediate", {"beginner", "intermediate"}) is True
    assert filter_by_difficulty("master", {"all"}) is True
