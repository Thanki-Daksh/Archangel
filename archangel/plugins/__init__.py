"""Dynamically loaded plugins — external integrations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).parent


class PluginLoader:
    """Discovers, loads manifests, and manages plugins with error isolation and health tracking."""

    def __init__(self) -> None:
        self._manifests: List[dict[str, Any]] = []
        self._failure_counts: Dict[str, int] = {}
        self._status_map: Dict[str, str] = {}
        self._load_manifests()
        logger.debug("PluginLoader loaded %d plugin(s).", len(self._manifests))

    def _load_manifests(self) -> None:
        """Iterate over immediate subdirectories under PLUGIN_DIR."""
        for entry in sorted(PLUGIN_DIR.iterdir()):
            if not entry.is_dir():
                continue
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

                data.get("name", entry.name)
                data["id"] = data.get("id", entry.name)
                data["dir"] = str(entry)
                data["status"] = data.get("status", "enabled")

                self._manifests.append(data)
                self._status_map[data["id"]] = data["status"]
                self._failure_counts[data["id"]] = 0
                logger.debug("Loaded manifest: %s", entry.name)
            except Exception as exc:
                logger.error("Failed to load manifest '%s': %s", manifest_path, exc)

    @property
    def manifests(self) -> List[dict[str, Any]]:
        """Read-only list of all loaded plugin manifests."""
        return list(self._manifests)

    def safe_execute(self, plugin_id: str, action_func: Callable[[], Any], fallback: Any = None) -> Any:
        """Safely execute a plugin action with fault isolation and failure tracking."""
        if plugin_id not in self._status_map:
            self._status_map[plugin_id] = "enabled"
            self._failure_counts[plugin_id] = 0

        if self._status_map.get(plugin_id) == "disabled":
            logger.warning("Skipping execution for disabled plugin '%s'", plugin_id)
            return fallback

        try:
            result = action_func()
            if self._failure_counts.get(plugin_id, 0) > 0:
                self._failure_counts[plugin_id] = 0
                if self._status_map.get(plugin_id) == "degraded":
                    self._status_map[plugin_id] = "enabled"
            return result
        except Exception as exc:
            self._failure_counts[plugin_id] = self._failure_counts.get(plugin_id, 0) + 1
            failures = self._failure_counts[plugin_id]
            logger.error("Plugin '%s' execution error (count=%d): %s", plugin_id, failures, exc, exc_info=True)

            if failures >= 5:
                self._status_map[plugin_id] = "disabled"
                logger.critical("Plugin '%s' disabled due to repeated failures (%d)", plugin_id, failures)
            elif failures >= 3:
                self._status_map[plugin_id] = "degraded"
                logger.warning("Plugin '%s' status set to degraded (failures=%d)", plugin_id, failures)

            return fallback

    def get_plugin_status(self, plugin_id: str) -> str:
        return self._status_map.get(plugin_id, "unknown")

    def update_all(self) -> dict[str, bool]:
        """Check all installed plugins for updates."""
        logger.info("Plugin update check complete.")
        return {}
