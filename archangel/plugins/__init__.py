"""Dynamically loaded plugins — external integrations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).parent


class PluginLoader:
    """Discovers, loads manifests, and manages plugins.

    Scans ``archangel/plugins/`` for subdirectories containing a
    ``manifest.yaml``, reads and parses each manifest, and stores the
    resulting list of plugin dicts.
    """

    def __init__(self) -> None:
        self._manifests: list[dict[str, Any]] = []
        self._load_manifests()
        logger.debug("PluginLoader loaded %d plugin(s).", len(self._manifests))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_manifests(self) -> None:
        """Iterate over immediate subdirectories under PLUGIN_DIR."""
        for entry in sorted(PLUGIN_DIR.iterdir()):
            if not entry.is_dir():
                continue
            # Skip ourself and private directories
            if entry.name.startswith("_") or entry.name == "__pycache__":
                continue
            manifest_path = entry / "manifest.yaml"
            if not manifest_path.is_file():
                logger.warning(
                    "Plugin directory '%s' is missing manifest.yaml; skipping.",
                    entry.name,
                )
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as fh:
                    data: dict[str, Any] = yaml.safe_load(fh) or {}
                if not isinstance(data, dict):
                    logger.warning("Manifest '%s' is not a dict; skipping.", manifest_path)
                    continue
                self._manifests.append(data)
                logger.debug("Loaded manifest: %s", entry.name)
            except Exception as exc:
                logger.error("Failed to load manifest '%s': %s", manifest_path, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def manifests(self) -> list[dict[str, Any]]:
        """Read-only list of all loaded plugin manifests."""
        return list(self._manifests)

    def update_all(self) -> dict[str, bool]:
        """Check all installed plugins for updates.

        Returns a dict mapping plugin name to whether it was updated.
        """
        logger.info("Plugin update check (no plugins installed).")
        return {}
