"""Engine runtime — controls the platform lifecycle."""

import logging
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
    logger.info("One-time scan executed.")
    return {
        "sources_checked": 0,
        "posts_collected": 0,
        "leads_identified": 0,
        "duration_ms": 0,
    }


def get_status() -> dict[str, str]:
    """Return a snapshot of current runtime status as a dict."""
    state = "running" if _engine_running else "stopped"
    return {
        "Engine": state,
        "Event Bus": "initialized",
        "Storage": "ready",
        "Collectors": "idle",
        "Intelligence": "idle",
        "Scoring": "idle",
        "Notification": "idle",
    }
