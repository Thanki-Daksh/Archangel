"""Data models for The Archangel."""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from enum import Enum

logger = logging.getLogger(__name__)


class LeadType(str, Enum):
    UNKNOWN = "unknown"
    SALES_LEAD = "sales_lead"
    HIRING_SIGNAL = "hiring_signal"
    FUNDING_EVENT = "funding_event"
    PRODUCT_LAUNCH = "product_launch"
    FEATURE_REQUEST = "feature_request"
    PAIN_DISCUSSION = "pain_discussion"
    COMPANY_INTELLIGENCE = "company_intelligence"


class DifficultyTier(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    PRO = "pro"
    MASTER = "master"
    ALL = "all"


@dataclass
class RawPost:
    source: str = ""
    channel: str = ""
    author: str = ""
    content: str = ""
    timestamp: float = 0.0
    url: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class LeadAnalysis:
    raw_post_id: int = 0
    is_lead: bool = False
    confidence: float = 0.0
    estimated_budget: str = ""
    urgency: str = ""
    category: str = ""
    tags: list = field(default_factory=list)
    recommended_action: str = ""
    reasoning: str = ""


@dataclass
class LeadScore:
    analysis_id: int = 0
    score: float = 0.0
    confidence_score: float = 0.0
    budget_score: float = 0.0
    urgency_score: float = 0.0
    keyword_score: float = 0.0
    recency_score: float = 0.0


@dataclass
class Lead:
    """Canonical Archangel V1.5 Lead Object — single source of truth passed across all pipeline stages."""

    id: int = 0
    raw_post: RawPost = field(default_factory=RawPost)
    lead_type: LeadType = LeadType.UNKNOWN
    evaluation: dict = field(default_factory=dict)
    company_profile: dict = field(default_factory=dict)
    contacts: dict = field(default_factory=dict)
    website: dict = field(default_factory=dict)
    fingerprint: dict = field(default_factory=dict)
    ai_readiness: dict = field(default_factory=dict)
    health: dict = field(default_factory=dict)
    pains: list = field(default_factory=list)
    opportunities: list = field(default_factory=list)
    revenue: dict = field(default_factory=dict)
    competition: dict = field(default_factory=dict)
    pitch: dict = field(default_factory=dict)
    score: float = 0.0  # Overall Lead Score
    sales_readiness: float = 0.0
    opportunity_score: float = 0.0
    company_importance_score: float = 0.0
    buying_intent_score: float = 0.0
    hiring_signal_score: float = 0.0
    company_quality_score: float = 0.0
    budget_confidence: float = 0.0
    score_explanation: list = field(default_factory=list)
    intent_evidence: list = field(default_factory=list)
    difficulty_tier: DifficultyTier = DifficultyTier.BEGINNER
    difficulty_reasons: list = field(default_factory=list)
    priority: str = "MEDIUM"
    confidence: float = 0.0
    lifecycle_stage: str = "discovered"
    created_at: str = ""
    updated_at: str = ""
    analysis: Optional[LeadAnalysis] = None
    score_details: Optional[LeadScore] = None
