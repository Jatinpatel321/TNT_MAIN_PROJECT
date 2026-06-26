import enum
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class GroupStatus(enum.Enum):
    ACTIVE = "active"
    ORDERED = "ordered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GroupMemberRole(enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class PaymentSplitType(enum.Enum):
    EQUAL = "equal"
    CUSTOM = "custom"
    UNIFIED = "unified"


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(GroupStatus, values_callable=lambda x: [e.value for e in x]), default=GroupStatus.ACTIVE)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    # Relationships
    owner = relationship("User", back_populates="owned_groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    cart_items = relationship("GroupCartItem", back_populates="group", cascade="all, delete-orphan")
    slot_lock = relationship("GroupSlotLock", back_populates="group", uselist=False, cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(Enum(GroupMemberRole, values_callable=lambda x: [e.value for e in x]), default=GroupMemberRole.MEMBER)
    joined_at = Column(DateTime, default=utcnow_naive)

    # Relationships
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")


class GroupCartItem(Base):
    __tablename__ = "group_cart_items"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who added this item
    quantity = Column(Integer, nullable=False)
    price_at_time = Column(Float, nullable=False)
    added_at = Column(DateTime, default=utcnow_naive)

    # Relationships
    group = relationship("Group", back_populates="cart_items")
    menu_item = relationship("MenuItem")
    owner = relationship("User")


class GroupSlotLock(Base):
    __tablename__ = "group_slot_locks"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("slots.id"), nullable=False)
    locked_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    locked_at = Column(DateTime, default=utcnow_naive)
    expires_at = Column(DateTime, nullable=False)  # Lock expires after some time

    # Relationships
    group = relationship("Group", back_populates="slot_lock")
    slot = relationship("Slot")
    locked_by = relationship("User")


class GroupPaymentSplit(Base):
    __tablename__ = "group_payment_splits"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    split_type = Column(Enum(PaymentSplitType, values_callable=lambda x: [e.value for e in x]), default=PaymentSplitType.EQUAL)
    amount = Column(Float, nullable=True)  # For custom splits
    percentage = Column(Float, nullable=True)  # For percentage-based splits
    created_at = Column(DateTime, default=utcnow_naive)

    # Relationships
    group = relationship("Group")
    user = relationship("User")
