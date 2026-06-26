import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.fcm import send_push
from app.core.order_events import publish_order_event
from app.core.sms import send_sms
from app.core.time_utils import utcnow_naive
from app.modules.notifications.model import Notification, NotificationType

logger = logging.getLogger("tnt.notifications")

REDIS_QUEUE_KEY = "tnt:notifications:queue"
SMS_FALLBACK_WINDOW_SECONDS = 30  # suppress SMS if push was delivered within this window


def _push_delivered_recently(user_id: int) -> bool:
    """Check whether a push notification was delivered and acknowledged
    within ``SMS_FALLBACK_WINDOW_SECONDS`` for this user.

    Uses a lightweight Redis marker that is set when a push notification
    is successfully dispatched.  If the marker exists and is recent enough,
    we skip SMS to avoid double-pinging the user.
    """
    try:
        from app.core.redis import redis_client

        key = f"push_delivered:{user_id}"
        ttl = redis_client.ttl(key)
        # If the key exists and has at least half the window remaining,
        # consider the push "just delivered" — skip SMS.
        if ttl >= SMS_FALLBACK_WINDOW_SECONDS // 2:
            logger.debug(
                "sms_fallback_suppressed user_id=%s ttl=%s",
                user_id,
                ttl,
            )
            return True
        return False
    except Exception:
        logger.exception("sms_fallback_check_error user_id=%s", user_id)
        return False


def _mark_push_delivered(user_id: int) -> None:
    """Record that a push notification was just delivered."""
    try:
        from app.core.redis import redis_client

        key = f"push_delivered:{user_id}"
        redis_client.setex(key, SMS_FALLBACK_WINDOW_SECONDS, "1")
    except Exception:
        logger.exception("push_delivered_mark_error user_id=%s", user_id)


def notify_user(
    user_id: int,
    phone: str,
    title: str,
    message: str,
    db: Session,
    send_sms_flag: bool = True,
    sms_fallback: bool = True,
    notification_type: NotificationType = NotificationType.SYSTEM,
    reference_id: Optional[int] = None,
):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_id=reference_id,
    )

    db.add(notification)
    db.flush()

    push_succeeded = False

    # Push notification via FCM
    try:
        from app.modules.users.model import User

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.device_token and getattr(user, 'push_enabled', True):
            send_push(
                device_token=user.device_token,
                title=title,
                body=message,
                data={
                    "notification_type": notification_type.value,
                    "reference_id": reference_id,
                },
            )
            push_succeeded = True
            _mark_push_delivered(user_id)
    except Exception:
        logger.exception("notification_push_fcm_failed user_id=%s", user_id)

    # Resolve per-user sms_fallback preference from user.preferences JSON column.
    # If the user has explicitly set sms_fallback=false in preferences, respect
    # that as an opt-out.  Default to the caller-supplied value.
    if user is not None and isinstance(user.preferences, dict):
        user_sms_fallback = user.preferences.get("sms_fallback")
        if user_sms_fallback is not None:
            sms_fallback = bool(user_sms_fallback)
    elif user is not None:
        # preferences might be a string or None; treat missing as default
        pass

    try:
        _enqueue_to_redis(
            user_id=user_id,
            notification_id=notification.id,
            title=title,
            message=message,
            notification_type=notification_type.value,
        )
    except Exception:
        logger.exception("notification_redis_enqueue_failed user_id=%s", user_id)

    # Broadcast notification event to user's WebSocket channel
    try:
        publish_order_event(
            order_id=reference_id or 0,
            event="notification",
            data={
                "user_id": user_id,
                "title": title,
                "message": message,
                "notification_type": notification_type.value,
                "reference_id": reference_id,
                "created_at": utcnow_naive().isoformat(),
            },
        )
    except Exception:
        logger.exception("notification_event_publish_failed user_id=%s", user_id)

    # Decide whether to send SMS
    should_sms = send_sms_flag
    if should_sms and sms_fallback and push_succeeded:
        # If push was just delivered, skip SMS to avoid double-ping
        if _push_delivered_recently(user_id):
            logger.info(
                "sms_skipped_push_recent user_id=%s notification_id=%s",
                user_id,
                notification.id,
            )
            should_sms = False

    if not send_sms_flag:
        logger.debug(
            "sms_skipped_by_flag user_id=%s title=%s",
            user_id,
            title,
        )

    if should_sms:
        try:
            send_sms(phone, message)
        except Exception:
            logger.exception(
                "notification_sms_failed user_id=%s phone=%s",
                user_id,
                phone,
            )

    return notification


def _enqueue_to_redis(user_id: int, notification_id: int, title: str, message: str, notification_type: str) -> None:
    try:
        from app.core.redis import redis_client

        payload = json.dumps({
            "user_id": user_id,
            "notification_id": notification_id,
            "title": title,
            "message": message,
            "type": notification_type,
        })
        redis_client.lpush(REDIS_QUEUE_KEY, payload)
        redis_client.expire(REDIS_QUEUE_KEY, 86400)
        logger.info("notification_enqueued user_id=%s id=%s", user_id, notification_id)
    except Exception:
        logger.exception("notification_redis_enqueue_failed user_id=%s", user_id)


def get_unread_count(user_id: int, db: Session) -> int:
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).count()


def mark_all_read(user_id: int, db: Session) -> int:
    rows = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False,
    ).all()
    count = len(rows)
    for row in rows:
        row.is_read = True
    db.flush()
    return count


def get_notification_history(
    user_id: int,
    db: Session,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
) -> dict:
    """Return paginated notification history for a user."""
    q = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    total = q.count()
    items = (
        q.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# Alias for backward compatibility with router imports
send_notification = notify_user


def get_notification_preferences(user_id: int, db: Session) -> dict:
    """Return push notification preferences for the user.

    Returns a dict with defaults overridden by any values stored
    in the user's ``preferences`` JSON column (e.g. ``sms_fallback``).
    """
    from app.modules.users.model import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}

    prefs = user.preferences or {}
    if isinstance(prefs, dict):
        user_sms_fallback = prefs.get("sms_fallback")
    else:
        user_sms_fallback = None

    return {
        "push_enabled": getattr(user, "push_enabled", True),
        "sms_fallback": user_sms_fallback if user_sms_fallback is not None else True,
        "sms_enabled": True,
        "order_updates": True,
        "promotions": False,
        "delay_alerts": True,
    }
