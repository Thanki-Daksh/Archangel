"""Data persistence — stores raw posts, analysis, scores, and runtime history."""

import logging

logger = logging.getLogger(__name__)


class StorageBackend:
    """Persistent storage interface (SQLite / JSON / PostgreSQL)."""

    def __init__(self) -> None:
        logger.debug("StorageBackend created.")
