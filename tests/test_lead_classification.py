"""Unit tests for LeadType classification, BuyingIntentDetector, HiringSignalDetector, and Sales Readiness scoring."""

import pytest
from archangel.models import RawPost, LeadType
from archangel.enrichment.agent import EnrichmentAgent
from archangel.enrichment.buying_intent import BuyingIntentDetector
from archangel.enrichment.hiring import HiringSignalDetector


@pytest.fixture
def agent():
    return EnrichmentAgent()


def test_case_1_corporate_hiring_post(agent):
    content = """
    Stripe: Backend Engineer, Core Technology
    Headquarters: San Francisco, CA
    About the team: Stripe Infrastructure is responsible for reliability and scale.
    Minimum requirements: 5+ years SWE experience.
    Benefits: 401k match, health insurance, parental leave, paid sick leave.
    To apply: https://weworkremotely.com/remote-jobs/stripe-backend-engineer
    """
    post = RawPost(source="rss", channel="jobs", author="rss_publisher", content=content, url="https://weworkremotely.com/remote-jobs/stripe-backend-engineer")
    lead = agent._process_enrichment(post, raw_post_id=101)

    assert lead.lead_type == LeadType.HIRING_SIGNAL
    assert lead.buying_intent_score == 0.0
    assert lead.sales_readiness <= 20.0
    assert lead.company_profile.get("company_name", {}).get("value") == "Stripe"


def test_case_2_freelancer_wanted(agent):
    content = """
    Looking for a freelancer to build a Python FastAPI web scraper script.
    Project budget: $2,500 fixed price. Need someone to start ASAP.
    """
    post = RawPost(source="reddit", channel="r/forhire", author="client_123", content=content, url="https://reddit.com/r/forhire/item1")
    lead = agent._process_enrichment(post, raw_post_id=102)

    assert lead.lead_type == LeadType.SALES_LEAD
    assert lead.buying_intent_score >= 40.0
    assert lead.sales_readiness >= 30.0


def test_case_3_rfp(agent):
    content = """
    Request for proposal (RFP): Seeking software agency to build a custom SaaS MVP backend and mobile app.
    Fixed budget: $15,000.
    """
    post = RawPost(source="web", channel="rfp_board", author="enterprise_buyer", content=content, url="https://rfp.example.com/post1")
    lead = agent._process_enrichment(post, raw_post_id=103)

    assert lead.lead_type == LeadType.SALES_LEAD
    assert lead.buying_intent_score >= 50.0
    assert lead.sales_readiness >= 50.0


def test_case_4_feature_request(agent):
    content = """
    Feature request: Would be nice to add support for PostgreSQL export in the dashboard.
    Tired of manually exporting CSV files every week.
    """
    post = RawPost(source="reddit", channel="r/python", author="user_dev", content=content, url="https://reddit.com/r/python/item2")
    lead = agent._process_enrichment(post, raw_post_id=104)

    assert lead.lead_type in (LeadType.FEATURE_REQUEST, LeadType.PAIN_DISCUSSION)
    assert lead.sales_readiness < 50.0


def test_case_5_funding_announcement(agent):
    content = """
    Acme Corp raised $10M Seed round from top VCs to scale cloud infrastructure.
    """
    post = RawPost(source="techcrunch", channel="news", author="tc_reporter", content=content, url="https://acme.com/blog/funding")
    lead = agent._process_enrichment(post, raw_post_id=105)

    assert lead.lead_type == LeadType.FUNDING_EVENT


def test_case_6_product_launch(agent):
    content = """
    Show HN: Introducing Acme 1.0 — automated workflow engine built with Rust.
    We just launched our public beta!
    """
    post = RawPost(source="hackernews", channel="rss", author="builder_john", content=content, url="https://news.ycombinator.com/item?id=999")
    lead = agent._process_enrichment(post, raw_post_id=106)

    assert lead.lead_type == LeadType.PRODUCT_LAUNCH
