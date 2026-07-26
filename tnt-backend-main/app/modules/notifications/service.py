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

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("tnt.notifications")

REDIS_QUEUE_KEY = "tnt:notifications:queue"
SMS_FALLBACK_WINDOW_SECONDS = 30  # suppress SMS if push was delivered within this window

_notification_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="notif_dispatch")


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


def _async_dispatch_notification_external(
    user_id: int,
    phone: str,
    title: str,
    message: str,
    notification_id: int,
    notification_type_val: str,
    reference_id: Optional[int],
    device_token: Optional[str],
    push_enabled: bool,
    user_preferences: Optional[dict],
    send_sms_flag: bool,
    sms_fallback: bool,
) -> None:
    """Execute external notification network calls asynchronously (FCM, SMS, Redis, WebSockets)."""
    push_succeeded = False

    # Push notification via FCM
    if device_token and push_enabled:
        try:
            send_push(
                device_token=device_token,
                title=title,
                body=message,
                data={
                    "notification_type": notification_type_val,
                    "reference_id": reference_id,
                },
            )
            push_succeeded = True
            _mark_push_delivered(user_id)
        except Exception:
            logger.exception("notification_push_fcm_failed user_id=%s", user_id)

    # Resolve per-user sms_fallback preference
    if isinstance(user_preferences, dict):
        user_sms_fallback = user_preferences.get("sms_fallback")
        if user_sms_fallback is not None:
            sms_fallback = bool(user_sms_fallback)

    try:
        _enqueue_to_redis(
            user_id=user_id,
            notification_id=notification_id,
            title=title,
            message=message,
            notification_type=notification_type_val,
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
                "notification_type": notification_type_val,
                "reference_id": reference_id,
                "created_at": utcnow_naive().isoformat(),
            },
        )
    except Exception:
        logger.exception("notification_event_publish_failed user_id=%s", user_id)

    # Decide whether to send SMS
    should_sms = send_sms_flag
    if should_sms and sms_fallback and push_succeeded:
        if _push_delivered_recently(user_id):
            logger.info(
                "sms_skipped_push_recent user_id=%s notification_id=%s",
                user_id,
                notification_id,
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

    # Pre-fetch user metadata needed for external dispatch
    from app.modules.users.model import User
    user = db.query(User).filter(User.id == user_id).first()
    device_token = user.device_token if user else None
    push_enabled = getattr(user, 'push_enabled', True) if user else True
    user_preferences = user.preferences if user else None

    # Offload external network side-effects (FCM, SMS, Redis, WebSockets) to non-blocking background thread
    notification_type_val = notification_type.value if hasattr(notification_type, "value") else str(notification_type)
    _notification_executor.submit(
        _async_dispatch_notification_external,
        user_id=user_id,
        phone=phone,
        title=title,
        message=message,
        notification_id=notification.id,
        notification_type_val=notification_type_val,
        reference_id=reference_id,
        device_token=device_token,
        push_enabled=push_enabled,
        user_preferences=user_preferences,
        send_sms_flag=send_sms_flag,
        sms_fallback=sms_fallback,
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


def send_vendor_push(
    vendor_id: int,
    title: str,
    message: str,
    data: dict | None = None,
) -> bool:
    """Send a push notification directly to a vendor.

    Looks up the vendor's User record (the vendor's User is the user whose
    ``device_token`` is set via the vendor app's FCM registration) and
    dispatches the push via ``send_push()``.

    Args:
        vendor_id: The User.id of the vendor.
        title: Notification title.
        message: Notification body.
        data: Optional extra payload (e.g. ``{"type": "new_order", "order_id": 123}``).

    Returns:
        True if the push was sent successfully, False otherwise.
    """
    from app.modules.users.model import User

    try:
        vendor = None
        # Try resolving via User.id first (most common path)
        vendor = _resolve_user(vendor_id)
        if not vendor:
            logger.warning("vendor_push_no_user vendor_id=%s", vendor_id)
            return False

        if not vendor.device_token:
            logger.info("vendor_push_no_token vendor_id=%s", vendor_id)
            return False

        from app.core.fcm import send_push

        sent = send_push(
            device_token=vendor.device_token,
            title=title,
            body=message,
            data=data or {},
        )
        if sent:
            logger.info("vendor_push_sent vendor_id=%s title=%s", vendor_id, title)
        else:
            logger.warning("vendor_push_failed vendor_id=%s title=%s", vendor_id, title)
        return sent
    except Exception:
        logger.exception("vendor_push_error vendor_id=%s", vendor_id)
        return False


def _resolve_user(user_id: int):
    """Resolve a User by id using a short-lived session."""
    from app.database.session import SessionLocal
    from app.modules.users.model import User

    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


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
