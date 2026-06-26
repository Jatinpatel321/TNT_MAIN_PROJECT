"""Emergency shutdown state management.

Persistence hierarchy:
1. Database (source of truth) — SystemConfig table
2. Redis (60-second read-through cache) — fast reads
3. In-memory fallback (last resort if both DB and Redis are unavailable)
"""
import logging

from app.core.redis import redis_client

EMERGENCY_SHUTDOWN_KEY = "tnt:emergency_shutdown"
_fallback_shutdown_enabled = False
_REDIS_CACHE_TTL = 60  # seconds

logger = logging.getLogger("tnt.emergency")


def is_emergency_shutdown_enabled() -> bool:
    """Check shutdown state — Redis cache first, then DB fallback, then in-memory."""
    try:
        cached = redis_client.get(EMERGENCY_SHUTDOWN_KEY)
        if cached is not None:
            return str(cached, "utf-8").strip() in {"1", "true", "True", "yes", "on"}
    except Exception:
        pass

    # Cache miss or Redis error — read from DB
    try:
        from app.database.session import SessionLocal
        from app.modules.admin.model import SystemConfig
        db = SessionLocal()
        config = db.query(SystemConfig).filter(SystemConfig.key == "emergency_shutdown").first()
        db.close()
        enabled = config.value == "true" if config else False

        # Write back to Redis cache
        try:
            redis_client.setex(EMERGENCY_SHUTDOWN_KEY, _REDIS_CACHE_TTL, "1" if enabled else "0")
        except Exception:
            pass

        return enabled
    except Exception:
        pass

    return _fallback_shutdown_enabled


def set_emergency_shutdown(enabled: bool) -> bool:
    """Persist shutdown state to DB and invalidate Redis cache."""
    global _fallback_shutdown_enabled
    _fallback_shutdown_enabled = enabled

    # Persist to database
    try:
        from app.database.session import SessionLocal
        from app.modules.admin.model import SystemConfig
        db = SessionLocal()
        config = db.query(SystemConfig).filter(SystemConfig.key == "emergency_shutdown").first()
        if config:
            config.value = "true" if enabled else "false"
        else:
            config = SystemConfig(key="emergency_shutdown", value="true" if enabled else "false")
            db.add(config)
        db.commit()
        db.close()
    except Exception as exc:
        logger.error("emergency_db_write_failed error=%s", exc)

    # Update Redis cache
    try:
        redis_client.setex(EMERGENCY_SHUTDOWN_KEY, _REDIS_CACHE_TTL, "1" if enabled else "0")
    except Exception:
        pass

    return enabled