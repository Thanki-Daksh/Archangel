import logging
from archangel.config.manager import load_config

logger = logging.getLogger(__name__)

def get_allowed_users() -> list[int]:
    try:
        cfg = load_config()
        telegram_cfg = cfg.get("channels", {}).get("telegram", {})
        allowed_ids = telegram_cfg.get("allowed_user_ids")
        if allowed_ids and isinstance(allowed_ids, list):
            return [int(uid) for uid in allowed_ids]
    except Exception as exc:
        logger.error("Failed to load allowed users from config: %s", exc)
    # Safe fallback to provided ID
    return [8741237853]

def is_authorized(user_id: int) -> bool:
    return user_id in get_allowed_users()
