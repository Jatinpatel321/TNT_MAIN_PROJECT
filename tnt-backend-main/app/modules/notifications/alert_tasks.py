import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.reorder_service import detect_delay, calculate_eta
from app.modules.notifications.service import notify_user
from app.modules.notifications.model import Notification, NotificationType
from app.modules.users.model import User

logger = logging.getLogger("tnt.notifications.alert_tasks")

def check_proactive_delays_job(db: Session) -> int:
    """Proactively alerts users when their active order delay exceeds the threshold."""
    active_orders = db.query(Order).filter(
        Order.status.in_([OrderStatus.PLACED, OrderStatus.CONFIRMED, OrderStatus.PREPARING])
    ).all()

    count = 0
    now = utcnow_naive()
    for order in active_orders:
        estimated_ready_at = getattr(order, "estimated_ready_at", None)
        if not estimated_ready_at:
            estimated_ready_at = calculate_eta(order, db)
            setattr(order, "estimated_ready_at", estimated_ready_at)
            db.commit()

        if detect_delay(order, db):
            # Check if delay alert has already been sent for this order
            existing = db.query(Notification).filter(
                Notification.user_id == order.user_id,
                Notification.title == "Order Delayed",
                Notification.message.like(f"%order #{order.id}%")
            ).first()

            if not existing:
                user = db.query(User).filter(User.id == order.user_id).first()
                if user:
                    delay_minutes = max(0.0, (now - estimated_ready_at).total_seconds() / 60.0)
                    notify_user(
                        user_id=user.id,
                        phone=user.phone,
                        title="Order Delayed",
                        message=f"Your order #{order.id} is running about {delay_minutes:.0f} minutes late. We are sorry for the delay.",
                        db=db,
                        send_sms_flag=True,
                        notification_type=NotificationType.DELAY_ALERT,
                        reference_id=order.id
                    )
                    count += 1
                    logger.info(f"Proactive delay alert sent to user {user.id} for order {order.id}")
    if count > 0:
        db.commit()
    return count


def send_proactive_rush_hour_alerts_job(db: Session) -> int:
    """Proactively alerts users during pre-rush hours suggesting optimal ordering times."""
    current_hour = utcnow_naive().hour
    # Only send at 11 (pre-lunch) and 18 (pre-dinner)
    if current_hour not in [11, 18]:
        return 0

    # Ensure we don't send multiple alerts in the same hour block
    # Check if a rush hour alert has already been sent to anyone today within this hour
    today = utcnow_naive().date()
    existing_alert = db.query(Notification).filter(
        Notification.title == "Good Time to Order",
        Notification.created_at >= datetime.combine(today, datetime.min.time())
    ).first()
    
    if existing_alert and existing_alert.created_at.hour == current_hour:
        logger.info(f"Proactive rush hour alert already sent for hour {current_hour} today.")
        return 0

    # Find active users (e.g. students and faculty)
    from app.modules.users.model import UserRole
    users_to_notify = db.query(User).filter(
        User.role.in_([UserRole.STUDENT, UserRole.FACULTY])
    ).all()

    count = 0
    next_hour = current_hour + 1
    for user in users_to_notify:
        notify_user(
            user_id=user.id,
            phone=user.phone,
            title="Good Time to Order",
            message=f"Now is a great time to place your order for {next_hour}:00 pickup. Pre-book your slot to beat the rush!",
            db=db,
            send_sms_flag=False,
            notification_type=NotificationType.ALERT
        )
        count += 1
    
    db.commit()
    logger.info(f"Sent {count} proactive rush hour alerts to users.")
    return count
