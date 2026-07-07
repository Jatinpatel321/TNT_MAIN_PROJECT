import json
import logging

from app.core.redis import redis_client

logger = logging.getLogger("tnt.university_policy")

UNIVERSITY_POLICY_KEY = "tnt:policy:university"
CACHE_TTL = 120  # 2-minute cache

_DEFAULT_POLICY = {
    "enabled": False,
    "break_start_hour": 12,
    "break_end_hour": 14,
    "max_orders_per_user": 3,
    "min_slot_duration_minutes": 15,
}


def _read_from_db() -> dict | None:
    """Read university policy from system_config table."""
    try:
        from app.database.session import SessionLocal
        from app.modules.admin.model import SystemConfig
        db = SessionLocal()
        config = db.query(SystemConfig).filter(SystemConfig.key == "university_policy").first()
        db.close()
        if config:
            return json.loads(config.value)
    except Exception as exc:
        logger.error("university_policy_db_read_failed error=%s", exc)
    return None


def _write_to_db(policy: dict) -> None:
    """Persist university policy to system_config table."""
    try:
        from app.database.session import SessionLocal
        from app.modules.admin.model import SystemConfig
        db = SessionLocal()
        config = db.query(SystemConfig).filter(SystemConfig.key == "university_policy").first()
        value = json.dumps(policy)
        if config:
            config.value = value
        else:
            config = SystemConfig(key="university_policy", value=value)
            db.add(config)
        db.commit()
        db.close()
    except Exception as exc:
        logger.error("university_policy_db_write_failed error=%s", exc)


def get_university_policy() -> dict:
    # Tier 1: Redis cache
    try:
        cached = redis_client.get(UNIVERSITY_POLICY_KEY)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    # Tier 2: Database
    policy = _read_from_db()
    if policy:
        try:
            redis_client.setex(UNIVERSITY_POLICY_KEY, CACHE_TTL, json.dumps(policy))
        except Exception:
            pass
        return policy

    # Tier 3: Default
    return dict(_DEFAULT_POLICY)


def set_university_policy(
    enabled: bool,
    break_start_hour: int,
    break_end_hour: int,
    max_orders_per_user: int,
    min_slot_duration_minutes: int,
) -> dict:
    policy = {
        "enabled": enabled,
        "break_start_hour": break_start_hour,
        "break_end_hour": break_end_hour,
        "max_orders_per_user": max_orders_per_user,
        "min_slot_duration_minutes": min_slot_duration_minutes,
    }
    _write_to_db(policy)
    try:
        redis_client.setex(UNIVERSITY_POLICY_KEY, CACHE_TTL, json.dumps(policy))
    except Exception:
        pass
    return policy


def is_hour_in_break_window(hour: int, start_hour: int, end_hour: int) -> bool:
    return start_hour <= hour < end_hour
