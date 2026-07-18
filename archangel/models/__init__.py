"""Data models for The Archangel."""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
    id: int = 0
    raw_post: RawPost = None
    analysis: LeadAnalysis = None
    score: LeadScore = None
    status: str = "discovered"
    created_at: str = ""
    updated_at: str = ""
