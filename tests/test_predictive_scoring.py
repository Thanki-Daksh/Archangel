import pytest
from archangel.events import EventBus
from archangel.models import LeadAnalysis, RawPost
from archangel.scoring.learning import AdaptiveScorer, LearningAgent
from archangel.storage import StorageBackend


def test_adaptive_scorer_default(tmp_path):
    storage = StorageBackend(db_path=tmp_path / "test_scoring.db")
    scorer = AdaptiveScorer(storage=storage)

    analysis = LeadAnalysis(
        confidence=0.9,
        estimated_budget="$5000",
        urgency="high",
        tags=["python", "fastapi"],
    )

    score = scorer.score_analysis(analysis, raw_post_id=1)
    assert score.score > 70.0
    assert score.confidence_score == 90.0
    storage.close()


def test_learning_agent_feedback_loop(tmp_path):
    bus = EventBus()
    storage = StorageBackend(db_path=tmp_path / "test_learning.db")
    scorer = AdaptiveScorer(storage=storage)
    agent = LearningAgent(event_bus=bus, storage=storage, scorer=scorer)

    post = RawPost(source="reddit", content="Need Python dev", url="http://reddit.com/dev")
    post_id = storage.store_raw_post(post)

    events = []
    bus.subscribe("model.retrained", lambda p: events.append(p))

    # Send positive feedback
    bus.publish(
        "user.feedback",
        {
            "raw_post_id": post_id,
            "feedback_type": "like",
            "rating": 1.0,
        },
    )

    assert len(events) == 1
    assert "updated_weights" in events[0]

    history = storage.get_feedback_history()
    assert len(history) == 1
    assert history[0]["feedback_type"] == "like"

    storage.close()
