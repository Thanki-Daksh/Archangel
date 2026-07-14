"""Plugin registry — read-only access to loaded plugin manifests."""

from __future__ import annotations

from typing import Any


class PluginRegistry:
    """Read-only registry of loaded plugin manifests keyed by plugin name."""

    def __init__(self, plugins: list[dict[str, Any]]) -> None:
        self._plugins: dict[str, dict[str, Any]] = {}
        for p in plugins:
            name = p.get("name", "unknown")
            self._plugins[name] = p

    def list_all(self) -> list[dict[str, Any]]:
        """Return all registered plugin manifests."""
        return list(self._plugins.values())

    def get(self, name: str) -> dict[str, Any] | None:
        """Look up a plugin by its name.  Returns None when not found."""
        return self._plugins.get(name)

    def filter_by(self, category: str) -> list[dict[str, Any]]:
        """Return plugins whose ``category`` matches the given value."""
        return [p for p in self._plugins.values() if p.get("category") == category]

    def filter_by_status(self, status: str) -> list[dict[str, Any]]:
        """Return plugins whose ``status`` matches the given value."""
        return [p for p in self._plugins.values() if p.get("status") == status]
