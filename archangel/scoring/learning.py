"""Predictive Scoring with Feedback Loop — adaptive weight tuning based on user feedback."""

import logging
from typing import Dict, Any, Optional
from archangel.events import EventBus
from archangel.models import LeadScore, LeadAnalysis
from archangel.storage import StorageBackend

logger = logging.getLogger(__name__)


class AdaptiveScorer:
    """Computes dynamic score weights tuned by user preference history."""

    def __init__(self, storage: Optional[StorageBackend] = None) -> None:
        self.storage = storage or StorageBackend.get_instance()
        self.default_weights = {
            "confidence": 0.35,
            "budget": 0.25,
            "urgency": 0.20,
            "keyword": 0.20,
        }

    def get_user_weights(self) -> Dict[str, float]:
        """Calculates dynamic weight multipliers based on past positive/negative feedback."""
        history = self.storage.get_feedback_history(limit=100)
        if not history:
            return dict(self.default_weights)

        weights = dict(self.default_weights)
        pos_count = sum(1 for h in history if h.get("feedback_type") in ("like", "upvote", "converted"))
        neg_count = sum(1 for h in history if h.get("feedback_type") in ("ignore", "downvote", "dismissed"))

        total = pos_count + neg_count
        if total == 0:
            return weights

        # Boost or penalize weights based on user preference trends
        boost_factor = 1.0 + ((pos_count - neg_count) / max(total, 1)) * 0.2
        for k in weights:
            weights[k] = round(weights[k] * boost_factor, 4)

        return weights

    def score_analysis(self, analysis: LeadAnalysis, raw_post_id: int = 0) -> LeadScore:
        """Generates a LeadScore applying adaptive weights."""
        weights = self.get_user_weights()

        conf_score = analysis.confidence * 100.0
        budget_score = 80.0 if "5000" in analysis.estimated_budget or "$" in analysis.estimated_budget else 50.0
        urgency_score = 90.0 if analysis.urgency.lower() == "high" else (60.0 if analysis.urgency.lower() == "medium" else 30.0)
        keyword_score = min(len(analysis.tags) * 20.0, 100.0)

        total_weight = sum(weights.values())
        raw_score = (
            conf_score * weights["confidence"]
            + budget_score * weights["budget"]
            + urgency_score * weights["urgency"]
            + keyword_score * weights["keyword"]
        ) / (total_weight if total_weight > 0 else 1.0)

        final_score = round(min(max(raw_score, 0.0), 100.0), 2)

        return LeadScore(
            analysis_id=analysis.raw_post_id or raw_post_id,
            score=final_score,
            confidence_score=round(conf_score, 2),
            budget_score=round(budget_score, 2),
            urgency_score=round(urgency_score, 2),
            keyword_score=round(keyword_score, 2),
            recency_score=100.0,
        )


class LearningAgent:
    """Subscribes to user feedback events to continuously update adaptive scoring."""

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        storage: Optional[StorageBackend] = None,
        scorer: Optional[AdaptiveScorer] = None,
    ) -> None:
        self.event_bus = event_bus or EventBus.get_instance()
        self.storage = storage or StorageBackend.get_instance()
        self.scorer = scorer or AdaptiveScorer(storage=self.storage)

        self.event_bus.subscribe("user.feedback", self._on_user_feedback)
        logger.debug("LearningAgent initialized and subscribed to user.feedback")

    def _on_user_feedback(self, payload: dict) -> None:
        raw_post_id = payload.get("raw_post_id")
        feedback_type = payload.get("feedback_type", "like")
        rating = float(payload.get("rating", 1.0))
        features = payload.get("features", {})

        if raw_post_id:
            self.storage.store_feedback(
                raw_post_id=raw_post_id,
                feedback_type=feedback_type,
                rating=rating,
                features=features,
            )
            self.event_bus.publish(
                "model.retrained",
                {
                    "feedback_count": len(self.storage.get_feedback_history()),
                    "updated_weights": self.scorer.get_user_weights(),
                },
            )
            logger.info("Feedback recorded for lead #%d (%s). Model updated.", raw_post_id, feedback_type)
