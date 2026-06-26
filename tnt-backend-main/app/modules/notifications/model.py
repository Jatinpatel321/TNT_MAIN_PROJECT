import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class NotificationType(enum.Enum):
    ORDER_ACCEPTED = "order_accepted"
    ORDER_PREPARING = "order_preparing"
    ORDER_READY = "order_ready"
    PICKUP_REMINDER = "pickup_reminder"
    DELAY_ALERT = "delay_alert"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_PLACED = "order_placed"
    PROMO = "promo"
    ALERT = "alert"
    SYSTEM = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    message = Column(String, nullable=False)

    notification_type = Column(
        Enum(NotificationType, values_callable=lambda x: [e.value for e in x]),
        default=NotificationType.SYSTEM,
        nullable=False,
    )
    reference_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow_naive)
