"""Dynamically loaded plugins — external integrations."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers, loads, and manages plugins."""

    def __init__(self) -> None:
        logger.debug("PluginLoader created.")

    def update_all(self) -> dict[str, bool]:
        """Check all installed plugins for updates.

        Returns a dict mapping plugin name to whether it was updated.
        """
        logger.info("Plugin update check (no plugins installed).")
        return {}
