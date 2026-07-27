"""ConfigManager — Manages persistent configuration in ~/.archangel/."""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".archangel"


class ConfigManager:
    """Thread-safe manager for user preferences, provider credentials, and swarm defaults."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or CONFIG_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, filename: str) -> Path:
        return self.base_dir / filename

    def is_setup_completed(self) -> bool:
        """Returns True if Archangel setup has been run and validated."""
        cfg = self.load("config.json")
        return bool(cfg.get("setup_completed", False))

    def mark_setup_completed(self, status: bool = True) -> None:
        """Updates setup status in ~/.archangel/config.json."""
        cfg = self.load("config.json")
        cfg["setup_completed"] = status
        cfg["configured_at"] = os.popen("date").read().strip() if sys.platform != "win32" else "configured"
        self.save("config.json", cfg)

    def load(self, filename: str) -> Dict[str, Any]:
        """Loads a JSON configuration file from ~/.archangel/."""
        path = self._get_path(filename)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed loading config %s: %s", path, exc)
            return {}

    def save(self, filename: str, data: Dict[str, Any]) -> None:
        """Saves data to a JSON configuration file in ~/.archangel/."""
        path = self._get_path(filename)
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("Failed saving config %s: %s", path, exc)

    def get_profile(self) -> Dict[str, Any]:
        return self.load("profile.json")

    def save_profile(self, profile_data: Dict[str, Any]) -> None:
        self.save("profile.json", profile_data)

    def get_providers(self) -> Dict[str, Any]:
        return self.load("providers.json")

    def save_providers(self, providers_data: Dict[str, Any]) -> None:
        self.save("providers.json", providers_data)

    def get_telegram(self) -> Dict[str, Any]:
        return self.load("telegram.json")

    def save_telegram(self, telegram_data: Dict[str, Any]) -> None:
        self.save("telegram.json", telegram_data)

    def get_search(self) -> Dict[str, Any]:
        defaults = {
            "default_workers": 300,
            "default_depth": 10,
            "max_concurrent_requests": 128,
            "preferred_regions": ["US", "Remote"],
            "preferred_industries": ["SaaS", "AI", "Software"],
        }
        loaded = self.load("search.json")
        defaults.update(loaded)
        return defaults

    def save_search(self, search_data: Dict[str, Any]) -> None:
        self.save("search.json", search_data)

    def reset_all(self) -> None:
        """Deletes all persistent configuration files in ~/.archangel/."""
        for fn in ["config.json", "profile.json", "providers.json", "telegram.json", "search.json", "outputs.json"]:
            path = self._get_path(fn)
            if path.exists():
                try:
                    path.unlink()
                except Exception as exc:
                    logger.warning("Could not delete %s: %s", path, exc)


def load_config() -> Dict[str, Any]:
    """Helper returning persistent configuration dict from ConfigManager."""
    mgr = ConfigManager()
    return mgr.load("config.json")
