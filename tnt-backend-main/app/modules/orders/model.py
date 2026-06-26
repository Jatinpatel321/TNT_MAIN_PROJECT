import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class OrderStatus(enum.Enum):
    # ── Canonical states ─────────────────────────────────────────────────
    PLACED    = "placed"     # order submitted by student
    CONFIRMED = "confirmed"  # vendor accepted
    PREPARING = "preparing"  # vendor is preparing the order
    READY     = "ready"      # vendor has prepared; QR pickup available
    PICKED    = "picked"     # student collected (terminal)
    CANCELLED = "cancelled"  # cancelled (terminal)
    # ── Legacy states — kept for backward-compat with existing DB rows ───
    PENDING          = "pending"           # pre-PROMPT-11 PLACED equivalent
    READY_FOR_PICKUP = "ready_for_pickup"  # pre-PROMPT-11 READY equivalent
    COMPLETED        = "completed"         # pre-PROMPT-11 PICKED equivalent


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(OrderStatus, values_callable=lambda x: [e.value for e in x]), default=OrderStatus.PLACED)
    total_amount = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utcnow_naive)

    # QR Pickup fields
    qr_code = Column(String(255), unique=True, nullable=True)
    pickup_confirmed_at = Column(DateTime, nullable=True)
    pickup_confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ETA fields (set by checkout_service; queried by AI intelligence)
    eta_minutes = Column(Integer, nullable=True)
    actual_completion_minutes = Column(Integer, nullable=True)

    # Fraud fields
    fraud_flag = Column(Boolean, nullable=False, default=False, server_default="0")
    flagged_at = Column(DateTime, nullable=True)  # set when fraud_flag flips to True
    fraud_reason = Column(String(500), nullable=True)  # human-readable reason from auto-detection

    # Combined booking: link to a stationery job when this order is part of a combined booking
    stationery_job_id = Column(Integer, ForeignKey("stationery_jobs.id"), nullable=True)

    # Booking type discriminator: food / stationery / combined
    booking_type = Column(String(20), nullable=False, server_default="food")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_at_time = Column(Float, nullable=False)
