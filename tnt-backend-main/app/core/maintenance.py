"""Campus maintenance mode — SystemConfig-backed flag + message.

Distinct from emergency shutdown: maintenance mode is a planned, message-driven
pause. When enabled it blocks the same mutating endpoints and surfaces a custom
message so students/vendors know it's scheduled maintenance, not an outage.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("tnt.maintenance")

_KEY_ENABLED = "maintenance_mode"
_KEY_MESSAGE = "maintenance_message"
_DEFAULT_MESSAGE = "The platform is under scheduled maintenance. Please try again shortly."


def _get_config(key: str) -> str | None:
    try:
        from app.database.session import SessionLocal
        from app.modules.admin.model import SystemConfig
        db = SessionLocal()
        try:
            row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            return row.value if row else None
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("maintenance config read failed: %s", exc)
        return None


def is_maintenance_mode_enabled() -> bool:
    return (_get_config(_KEY_ENABLED) or "false").lower() == "true"


def get_maintenance_status() -> dict:
    return {
        "enabled": is_maintenance_mode_enabled(),
        "message": _get_config(_KEY_MESSAGE) or _DEFAULT_MESSAGE,
    }


def set_maintenance_mode(enabled: bool, message: str | None = None) -> dict:
    from app.database.session import SessionLocal
    from app.modules.admin.model import SystemConfig

    db = SessionLocal()
    try:
        def _upsert(key: str, value: str) -> None:
            row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if row:
                row.value = value
            else:
                db.add(SystemConfig(key=key, value=value))

        _upsert(_KEY_ENABLED, "true" if enabled else "false")
        if message is not None:
            _upsert(_KEY_MESSAGE, message.strip() or _DEFAULT_MESSAGE)
        db.commit()
    finally:
        db.close()
    return get_maintenance_status()
