"""Vendor models — dedicated vendor business entity and staff management.

Vendors are business entities owned by a User (owner_id → users.id).
Vendor Staff are employees who can act on behalf of a vendor.

This is separate from the existing convention of treating User records
with role=VENDOR as vendors — here we provide a proper business entity
model with authentication, staff management, and role-based access.
"""

from __future__ import annotations

import enum

import bcrypt
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class VendorStatus(enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class Vendor(Base):
    """Vendor business entity — linked to a User via owner_id."""

    __tablename__ = "vendors"

    vendor_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_name = Column(String(150), nullable=False)
    category = Column(String(50), nullable=True)  # "food" | "stationery"
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(
        Enum(VendorStatus, values_callable=lambda x: [e.value for e in x]),
        default=VendorStatus.PENDING,
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow_naive)

    # ORM relationships
    owner = relationship("User", foreign_keys=[owner_id])
    staff_members = relationship(
        "VendorStaff", back_populates="vendor", cascade="all, delete-orphan"
    )

    @staticmethod
    def hash_password(plain: str) -> str:
        """Hash a plain-text password using bcrypt."""
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plain-text password against a bcrypt hash."""
        return bcrypt.checkpw(plain.encode(), hashed.encode())


class VendorStaff(Base):
    """Staff member employed by a vendor."""

    __tablename__ = "vendor_staff"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(
        Integer, ForeignKey("vendors.vendor_id"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False, default="staff")  # "manager" | "staff"
    phone = Column(String(20), nullable=False)
    permissions = Column(JSON, default=dict)
    password_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)

    # ORM relationships
    vendor = relationship("Vendor", back_populates="staff_members")

    @staticmethod
    def hash_password(plain: str) -> str:
        """Hash a plain-text password using bcrypt."""
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        """Verify a plain-text password against a bcrypt hash."""
        return bcrypt.checkpw(plain.encode(), hashed.encode())