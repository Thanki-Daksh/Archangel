"""Unit tests for Archangel V2.0 Recency Decay, Source Quality Weighting, Dual-Scoring, and Multi-Pipeline Router."""

import time
import pytest
from archangel.models import RawPost, LeadType
from archangel.enrichment.agent import EnrichmentAgent
from archangel.scoring.weights import calculate_recency_decay, get_source_quality_weight
from archangel.pipeline.router import MultiPipelineRouter


@pytest.fixture
def agent():
    return EnrichmentAgent()


def test_recency_decay():
    now = time.time()
    mult_today, exp_today = calculate_recency_decay(now - 3600)
    mult_7d, exp_7d = calculate_recency_decay(now - (7 * 86400))
    mult_40d, exp_40d = calculate_recency_decay(now - (40 * 86400))

    assert mult_today == 1.00
    assert mult_7d == 0.75
    assert mult_40d == 0.10


def test_source_quality_weights():
    w_rfp, _ = get_source_quality_weight("web", "gov_rfp")
    w_yc, _ = get_source_quality_weight("rss", "ycombinator")
    w_reddit, _ = get_source_quality_weight("reddit", "r/forhire")

    assert w_rfp == 100.0
    assert w_yc == 90.0
    assert w_reddit == 60.0


def test_dual_scoring_funding_event(agent):
    content = "OpenAI raised $10B in new funding to expand AI infrastructure."
    post = RawPost(source="techcrunch", channel="news", author="tc_reporter", content=content, url="https://techcrunch.com/openai")
    lead = agent._process_enrichment(post, raw_post_id=201)

    assert lead.lead_type == LeadType.FUNDING_EVENT
    assert lead.sales_readiness < 40.0
    assert lead.opportunity_score >= 30.0  # High strategic value


def test_explainability_and_evidence(agent):
    content = "Request for proposal (RFP): Seeking agency or freelancer to build a Python FastAPI web application. Fixed project budget: $5,000."
    post = RawPost(source="ycombinator", channel="jobs", author="buyer_user", content=content, url="https://news.ycombinator.com/item1")
    lead = agent._process_enrichment(post, raw_post_id=202)

    assert lead.lead_type == LeadType.SALES_LEAD
    assert len(lead.intent_evidence) > 0
    assert len(lead.score_explanation) > 0
    assert any("Buying Intent" in line for line in lead.score_explanation)
