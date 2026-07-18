"""Lead quality calculation and ranking."""

import logging
import re
from pathlib import Path

from archangel.models import RawPost, LeadAnalysis, LeadScore

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "confidence": 40,
    "urgency": 25,
    "budget": 20,
    "keywords": 10,
    "recency": 5,
}


class ScoringAgent:
    """Ranks opportunities by confidence, budget, urgency, and other factors."""

    def __init__(self) -> None:
        self.weights = self._load_weights()
        logger.debug("ScoringAgent created with weights: %s", self.weights)

    def _load_weights(self) -> dict[str, float]:
        import yaml
        config_path = Path("configs/scoring.yaml")
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                if data and "weights" in data:
                    w = data["weights"]
                    return {
                        "confidence": float(w.get("confidence", 40)),
                        "urgency": float(w.get("urgency", 25)),
                        "budget": float(w.get("budget", 20)),
                        "keywords": float(w.get("keywords", 10)),
                        "recency": float(w.get("recency", 5)),
                    }
            except Exception as exc:
                logger.warning("Failed to load scoring weights: %s", exc)
        return dict(DEFAULT_WEIGHTS)

    def score(self, analysis: LeadAnalysis, post: RawPost) -> LeadScore:
        confidence_score = analysis.confidence * 100.0

        urgency_map = {"High": 100.0, "Medium": 60.0, "Low": 30.0, "": 30.0}
        urgency_score = urgency_map.get(analysis.urgency, 30.0)

        budget_score = self._parse_budget_to_score(analysis.estimated_budget)

        keyword_score = min(self._count_keyword_matches(post.content) * 20.0, 100.0)

        recency_score = self._calc_recency_score(post.timestamp)

        total = (
            confidence_score * (self.weights["confidence"] / 100.0)
            + urgency_score * (self.weights["urgency"] / 100.0)
            + budget_score * (self.weights["budget"] / 100.0)
            + keyword_score * (self.weights["keywords"] / 100.0)
            + recency_score * (self.weights["recency"] / 100.0)
        )

        return LeadScore(
            analysis_id=0,
            score=round(total, 1),
            confidence_score=round(confidence_score, 1),
            budget_score=round(budget_score, 1),
            urgency_score=round(urgency_score, 1),
            keyword_score=round(keyword_score, 1),
            recency_score=round(recency_score, 1),
        )

    def _parse_budget_to_score(self, budget_str: str) -> float:
        if not budget_str or budget_str == "Unknown":
            return 30.0
        numbers = re.findall(r'\d+', budget_str.replace(",", ""))
        if not numbers:
            return 30.0
        amounts = [int(n) for n in numbers]
        avg = sum(amounts) / len(amounts)
        if avg >= 5000:
            return 100.0
        if avg >= 2000:
            return 80.0
        if avg >= 1000:
            return 60.0
        if avg >= 500:
            return 40.0
        return 20.0

    def _count_keyword_matches(self, content: str) -> int:
        import yaml
        keywords = []
        kw_path = Path("configs/keywords.yaml")
        if kw_path.exists():
            try:
                with open(kw_path, "r") as f:
                    data = yaml.safe_load(f)
                keywords = data.get("include", []) if data else []
            except Exception:
                pass
        if not keywords:
            return 0
        content_lower = content.lower()
        count = sum(1 for kw in keywords if kw.lower() in content_lower)
        return count

    def _calc_recency_score(self, timestamp: float) -> float:
        import time
        now = time.time()
        age_hours = (now - timestamp) / 3600 if timestamp > 0 else 999
        if age_hours <= 24:
            return 100.0
        if age_hours <= 72:
            return 80.0
        if age_hours <= 168:
            return 60.0
        if age_hours <= 336:
            return 40.0
        return 20.0
