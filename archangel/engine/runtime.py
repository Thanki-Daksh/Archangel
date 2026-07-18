"""Engine runtime — controls the platform lifecycle."""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_engine_running = False


def start(debug: bool = False, config_path: str | None = None) -> None:
    """Start the Archangel runtime engine.

    Parameters
    ----------
    debug : bool
        Enable debug-level logging (default False).
    config_path : str or None
        Path to a custom configuration file.
    """
    global _engine_running
    if _engine_running:
        logger.warning("Engine is already running.")
        return

    logger.info("Engine starting (debug=%s, config=%s)", debug, config_path)
    _engine_running = True
    logger.info("Engine started successfully.")


def stop() -> None:
    """Gracefully shut down the runtime engine."""
    global _engine_running
    if not _engine_running:
        logger.warning("Engine is not running.")
        return

    logger.info("Engine shutting down ...")
    _engine_running = False
    logger.info("Engine stopped.")


def run_once() -> dict[str, Any]:
    """Execute a one-time scan cycle.

    Returns
    -------
    dict
        A summary of what was collected / analysed.
    """
    start_time = time.time()

    from archangel.collectors import CollectorAgent
    from archangel.analysis import IntelligenceAgent
    from archangel.scoring import ScoringAgent
    from archangel.storage import StorageBackend
    from archangel.notifications import NotificationAgent
    from archangel.events import EventBus

    collector = CollectorAgent()
    intelligence = IntelligenceAgent()
    scorer = ScoringAgent()
    storage = StorageBackend()
    notifier = NotificationAgent()
    event_bus = EventBus.get_instance()

    raw_posts = collector.collect_all()
    stored = 0
    leads_found = 0

    for post in raw_posts:
        try:
            if storage.lead_exists(post.url):
                continue
            post_id = storage.store_raw_post(post)
            if not post_id:
                logger.warning("Failed to store post: %s", post.url)
                continue

            analysis = intelligence.analyze(post)
            analysis.raw_post_id = post_id
            analysis_id = storage.store_analysis(analysis)

            lead_score = scorer.score(analysis, post)
            lead_score.analysis_id = analysis_id
            storage.store_score(lead_score)

            stored += 1
            if analysis.is_lead:
                leads_found += 1
                event_bus.publish("lead.discovered", {
                    "post": post,
                    "analysis": analysis,
                    "score": lead_score,
                })
                notifier.notify(post, analysis, lead_score)

            logger.info(
                "Processed post %s (lead=%s, score=%.1f, confidence=%.2f)",
                post.url, analysis.is_lead, lead_score.score, analysis.confidence,
            )
        except Exception as exc:
            logger.error("Failed to process post %s: %s", post.url, exc)

    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        "Scan complete: %d posts, %d stored, %d leads in %dms",
        len(raw_posts), stored, leads_found, duration_ms,
    )

    sources_count = len(raw_posts)
    return {
        "sources_checked": sources_count if sources_count > 0 else 0,
        "posts_collected": len(raw_posts),
        "leads_identified": leads_found,
        "leads_stored": stored,
        "duration_ms": duration_ms,
    }


def get_status() -> dict[str, str]:
    """Return a snapshot of current runtime status as a dict."""
    from archangel.storage import StorageBackend
    try:
        storage = StorageBackend.get_instance()
        lead_count = storage.get_lead_count()
    except Exception:
        lead_count = 0

    state = "running" if _engine_running else "stopped"
    return {
        "Engine": state,
        "Event Bus": "initialized",
        "Storage": f"active ({lead_count} leads)",
        "Collectors": "ready",
        "Intelligence": "ready",
        "Scoring": "ready",
        "Notification": "ready",
    }
