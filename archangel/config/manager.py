"""Configuration manager — loads, validates, and serves config values."""

import logging
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path("configs")


def load_config(config_dir: str | Path | None = None) -> dict[str, Any]:
    """Load and merge all configuration YAML files.

    Parameters
    ----------
    config_dir : str or Path, optional
        Directory containing YAML configuration files.

    Returns
    -------
    dict
        Merged configuration dictionary.
    """
    load_dotenv()
    config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR

    if not config_dir.exists():
        logger.warning("Config directory '%s' not found; using defaults.", config_dir)
        return _default_config()

    cfg: dict[str, Any] = {}
    import yaml

    for yaml_file in sorted(config_dir.glob("*.yaml")):
        try:
            with open(yaml_file, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if isinstance(data, dict):
                cfg.update(data)
                logger.debug("Loaded config from %s", yaml_file.name)
        except Exception as exc:
            logger.error("Failed to load %s: %s", yaml_file.name, exc)

    return cfg if cfg else _default_config()


def _default_config() -> dict[str, Any]:
    return {
        "runtime": {"debug": False, "log_level": "INFO", "timezone": "UTC"},
        "plugins": {"auto_discovery": True},
        "guardian": {"enabled": True},
        "engine": {"workers": "auto"},
    }


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Validate configuration structure and return a list of error messages.

    Returns an empty list when the configuration is valid.
    """
    errors: list[str] = []
    if not isinstance(cfg, dict):
        errors.append("Configuration must be a dictionary.")
    return errors
