import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class SlotStatus(enum.Enum):
    AVAILABLE = "available"
    LIMITED = "limited"
    FULL = "full"
    BLOCKED = "blocked"


class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    max_orders = Column(Integer, nullable=False)
    current_orders = Column(Integer, default=0)
    congestion_level = Column(Float, default=0.0)
    is_locked = Column(Boolean, default=False)
    locked_by = Column(String, nullable=True)
    locked_at = Column(DateTime, nullable=True)
    status = Column(Enum(SlotStatus, values_callable=lambda x: [e.value for e in x]), default=SlotStatus.AVAILABLE)
    
    # Advanced slot management fields
    slot_duration_minutes = Column(Integer, nullable=True)
    is_peak_hour = Column(Boolean, default=False)
    is_faculty_priority = Column(Boolean, default=False)
    auto_block_enabled = Column(Boolean, default=False)
    dynamic_capacity = Column(Integer, nullable=True)
    capacity_notes = Column(Text, nullable=True)

    bookings = relationship("SlotBooking", back_populates="slot", cascade="all, delete-orphan")


class BookingType(enum.Enum):
    FOOD = "food"
    STATIONERY = "stationery"
    COMBINED = "combined"


class BookingStatus(enum.Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class SlotBooking(Base):
    __tablename__ = "slot_bookings"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    booking_type = Column(Enum(BookingType, values_callable=lambda x: [e.value for e in x]), default=BookingType.FOOD, nullable=False)
    status = Column(Enum(BookingStatus, values_callable=lambda x: [e.value for e in x]), default=BookingStatus.CONFIRMED)
    booked_at = Column(DateTime, default=utcnow_naive)
    cancelled_at = Column(DateTime, nullable=True)

    slot = relationship("Slot", back_populates="bookings")


class SlotCapacityRule(Base):
    __tablename__ = "slot_capacity_rules"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_name = Column(String(255), nullable=False)
    day_of_week = Column(Integer, nullable=True)
    start_hour = Column(Integer, nullable=False)
    end_hour = Column(Integer, nullable=False)
    base_capacity = Column(Integer, nullable=False)
    peak_capacity = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class SlotRule(Base):
    __tablename__ = "slot_rules"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_config = Column(Text, nullable=False)
    is_enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class SlotTemplate(Base):
    """Reusable slot-generation template (admin-managed).

    A template defines a recurring daily window and slot sizing; the admin
    applies it to a vendor over a date range to generate real Slot rows.
    ``vendor_id`` NULL means a campus-wide template usable for any vendor.
    ``day_of_week`` NULL means it applies to every weekday.
    """
    __tablename__ = "slot_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    day_of_week = Column(Integer, nullable=True)  # 0=Mon .. 6=Sun; null = all days
    start_time = Column(String(5), nullable=False)  # "HH:MM"
    end_time = Column(String(5), nullable=False)    # "HH:MM"
    slot_duration_minutes = Column(Integer, nullable=False, default=30)
    max_orders_per_slot = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
