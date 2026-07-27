"""LeadDifficultyClassifier — Evaluates technical difficulty and experience requirements for leads.

Tiering Rules:
- BEGINNER: NO experience requirement listed in the post (0 yrs), entry-level, simple scripts, scrapers, automations.
- INTERMEDIATE: 1-3 years experience, mid-level full-stack MVPs, REST APIs, dashboards.
- PRO: 3-7 years experience, Senior/Lead titles, microservices, RAG/AI pipelines, K8s/Docker infra.
- MASTER: 8+ years experience, Principal/Architect titles, low-latency trading, kernel/compiler, security audits.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from archangel.models import DifficultyTier


@dataclass
class DifficultyResult:
    tier: DifficultyTier = DifficultyTier.BEGINNER
    score: float = 20.0  # 0 to 100
    experience_years: int = 0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier.value,
            "score": round(self.score, 1),
            "experience_years": self.experience_years,
            "reasons": self.reasons,
        }


# Regex patterns for experience extraction
EXP_YEARS_PATTERNS = [
    re.compile(r"\b(\d+)\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp|background|work)\b", re.IGNORECASE),
    re.compile(r"\b(?:minimum|at least|requires?|with)\s+(\d+)\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\b", re.IGNORECASE),
    re.compile(r"\b(\d+)\+?\s*(?:years?|yrs?)\s+as\s+a\b", re.IGNORECASE),
]

MASTER_TITLES = re.compile(r"\b(?:principal|architect|distinguished|director|head of|vp of|kernel engineer|compiler engineer)\b", re.IGNORECASE)
PRO_TITLES = re.compile(r"\b(?:senior|lead|staff|tech lead|senior software engineer)\b", re.IGNORECASE)
BEGINNER_TITLES = re.compile(r"\b(?:junior|entry level|intern|internship|beginner|apprentice)\b", re.IGNORECASE)

BEGINNER_SCOPE = re.compile(r"\b(?:script|web scraper|bot|bug fix|zapier|make\.com|wordpress|simple site|small update|html/css|automation)\b", re.IGNORECASE)
PRO_SCOPE = re.compile(r"\b(?:microservices|kubernetes|k8s|rag|langchain|vector database|finetune|distributed systems|aws infra)\b", re.IGNORECASE)
MASTER_SCOPE = re.compile(r"\b(?:low latency|high frequency|hft|compiler|kernel|security audit|soc2|reverse engineering)\b", re.IGNORECASE)


class LeadDifficultyClassifier:
    """Classifies incoming posts into technical difficulty levels."""

    def evaluate(self, text: str, budget: Optional[float] = None) -> DifficultyResult:
        if not text or not text.strip():
            return DifficultyResult(
                tier=DifficultyTier.BEGINNER,
                score=10.0,
                experience_years=0,
                reasons=["No experience requirement listed (Empty text)"]
            )

        reasons = []
        exp_years = 0

        # 1. Extract explicit experience years requirement
        for pattern in EXP_YEARS_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                try:
                    matched_num = int(matches[0]) if isinstance(matches[0], str) else int(matches[0][0])
                    if matched_num > exp_years:
                        exp_years = matched_num
                except (ValueError, IndexError):
                    pass

        if exp_years > 0:
            reasons.append(f"Explicit experience requirement: {exp_years}+ years")
        else:
            reasons.append("No experience requirement listed on post (0 years)")

        # 2. Inspect Titles & Key Terminology
        has_master_title = bool(MASTER_TITLES.search(text))
        has_pro_title = bool(PRO_TITLES.search(text))
        has_beginner_title = bool(BEGINNER_TITLES.search(text))

        has_master_scope = bool(MASTER_SCOPE.search(text))
        has_pro_scope = bool(PRO_SCOPE.search(text))
        has_beginner_scope = bool(BEGINNER_SCOPE.search(text))

        if has_master_title:
            reasons.append("Contains Master/Principal title")
        if has_pro_title:
            reasons.append("Contains Senior/Lead title")
        if has_beginner_title:
            reasons.append("Contains Junior/Entry-level title")

        if has_master_scope:
            reasons.append("Contains Master technical scope (Low latency/Security audit/Kernel)")
        elif has_pro_scope:
            reasons.append("Contains Pro technical scope (Microservices/RAG/Distributed Systems)")
        elif has_beginner_scope:
            reasons.append("Contains Beginner technical scope (Script/Scraper/Zapier/Fix)")

        # 3. Determine Primary Tier & Score
        if exp_years >= 8 or has_master_title or has_master_scope or (budget and budget >= 25000):
            tier = DifficultyTier.MASTER
            score = 90.0
        elif exp_years >= 3 or has_pro_title or has_pro_scope or (budget and budget >= 7500):
            tier = DifficultyTier.PRO
            score = 70.0
        elif exp_years >= 1 or (budget and budget >= 1500):
            tier = DifficultyTier.INTERMEDIATE
            score = 45.0
        else:
            tier = DifficultyTier.BEGINNER
            score = 20.0

        return DifficultyResult(
            tier=tier,
            score=score,
            experience_years=exp_years,
            reasons=reasons,
        )
