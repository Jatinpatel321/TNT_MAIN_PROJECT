import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class UserRole(enum.Enum):
    STUDENT = "student"
    FACULTY = "faculty"
    VENDOR = "vendor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), nullable=False)
    vendor_type = Column(String, nullable=False, default="food")
    university_id = Column(String, nullable=True)
    department = Column(String, nullable=True)
    semester = Column(Integer, nullable=True)
    email = Column(String(255), nullable=True)
    campus = Column(String(100), nullable=True)
    residence_type = Column(String(20), nullable=True)  # "hostel" | "day_scholar"
    dietary_preference = Column(String(20), nullable=True)  # vegetarian | non_vegetarian | vegan | jain | other
    profile_image = Column(String, nullable=True)
    device_token = Column(String(512), nullable=True)
    push_enabled = Column(Boolean, nullable=False, default=True)

    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    preferences = Column(JSON, default=dict)
    # Admin-managed vendor business metadata (keyed by the canonical User id used
    # across orders/slots/menu). Holds: stall, location, business_name, description,
    # email, operating_hours (JSON), slot_defaults (JSON). Null for non-vendors.
    vendor_meta = Column(JSON, nullable=True)
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow_naive)

    owned_groups = relationship("Group", back_populates="owner")
    group_memberships = relationship("GroupMember", back_populates="user")
    menu_items = relationship("MenuItem", back_populates="vendor")
    stationery_services = relationship("StationeryService", back_populates="vendor")
