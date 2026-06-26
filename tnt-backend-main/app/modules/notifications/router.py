from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.notifications.model import Notification, NotificationType
from app.modules.notifications.schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.modules.notifications.service import get_unread_count, mark_all_read, send_notification
from app.modules.orders.model import Order
from app.modules.users.model import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ── Vendor-Specific Notification Endpoints ──────────────────────────────────


@router.get("/vendor", summary="Get vendor notifications")
def get_vendor_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    notification_type: NotificationType | None = Query(None, description="Filter by type"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get notifications for the authenticated vendor with pagination."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    q = db.query(Notification).filter(Notification.user_id == db_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    if notification_type:
        q = q.filter(Notification.notification_type == notification_type)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.post("/vendor/notify-delay", summary="Send delay notification to user")
def notify_delay(
    order_id: int,
    delay_minutes: int,
    reason: str = "Delayed due to high volume",
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send a delay notification to the user for a specific order."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Resolve the order's student user for phone
    student = db.query(User).filter(User.id == order.user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Order user not found")

    try:
        send_notification(
            user_id=order.user_id,
            phone=student.phone,
            title="Order Delay",
            message=f"Your order #{order_id} is delayed by {delay_minutes} minutes. {reason}",
            db=db,
            send_sms_flag=True,
            notification_type=NotificationType.DELAY_ALERT,
            reference_id=order_id,
        )
        return {"message": "Delay notification sent", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/vendor/notify-ready", summary="Send pickup ready notification to user")
def notify_ready(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send a pickup ready notification to the user."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Resolve the order's student user for phone
    student = db.query(User).filter(User.id == order.user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Order user not found")

    try:
        send_notification(
            user_id=order.user_id,
            phone=student.phone,
            title="Order Ready for Pickup!",
            message=f"Your order #{order_id} is ready. Please collect it from the pickup counter.",
            db=db,
            send_sms_flag=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=order_id,
        )
        return {"message": "Ready notification sent", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.post("/vendor/notify-custom", summary="Send custom message to user")
def notify_custom(
    order_id: int,
    message: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send a custom message to the user for a specific order."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Resolve the order's student user for phone
    student = db.query(User).filter(User.id == order.user_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Order user not found")

    try:
        send_notification(
            user_id=order.user_id,
            phone=student.phone,
            title="Message from Vendor",
            message=message,
            db=db,
            send_sms_flag=False,
            notification_type=NotificationType.SYSTEM,
            reference_id=order_id,
        )
        return {"message": "Custom notification sent", "order_id": order_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


def _resolve_db_user(user: dict, db: Session):
    from app.modules.users.model import User
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Authenticated user not found")
    return db_user


@router.get("/history", summary="Get notification history with pagination")
def get_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.modules.notifications.service import get_notification_history
    db_user = _resolve_db_user(user, db)
    return get_notification_history(
        user_id=db_user.id,
        db=db,
        limit=limit,
        offset=offset,
        unread_only=unread_only,
    )


@router.get("/preferences", summary="Get notification preferences")
def get_preferences(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    from app.modules.notifications.service import get_notification_preferences
    db_user = _resolve_db_user(user, db)
    return get_notification_preferences(db_user.id, db)


@router.get("/", summary="Get current user's notifications")
def get_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    notification_type: NotificationType | None = Query(None, description="Filter by type"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = _resolve_db_user(user, db)
    q = db.query(Notification).filter(Notification.user_id == db_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    if notification_type:
        q = q.filter(Notification.notification_type == notification_type)
    total = q.count()
    items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/unread-count", summary="Get unread notification count", response_model=UnreadCountResponse)
def unread_count(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = _resolve_db_user(user, db)
    count = get_unread_count(db_user.id, db)
    return UnreadCountResponse(unread_count=count)


@router.get("/{user_id}", summary="Get notifications for a specific user", response_model=list[NotificationResponse])
def get_notifications_by_user_id(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_caller = _resolve_db_user(user, db)
    allowed_roles = {"vendor", "admin", "superadmin"}
    caller_role = db_caller.role.value if hasattr(db_caller.role, "value") else str(db_caller.role)
    if db_caller.id != user_id and caller_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Cannot view another user's notifications")

    from app.modules.users.model import User
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = _resolve_db_user(user, db)
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == db_user.id,
    ).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.flush()
    return notification


@router.post("/mark-all-read", summary="Mark all notifications as read", response_model=MarkAllReadResponse)
def mark_all_as_read(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = _resolve_db_user(user, db)
    count = mark_all_read(db_user.id, db)
    return MarkAllReadResponse(updated_count=count)
