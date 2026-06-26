from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class StationeryService(Base):
    __tablename__ = "stationery_services"

    id = Column(Integer, primary_key=True, index=True)

    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(150), nullable=False)
    service_type = Column(String(50), nullable=False)  # "xerox", "color_print", "bw_print"
    description = Column(String(500), nullable=True)
    price_per_page = Column(Integer, nullable=False)  # paise per page
    max_capacity = Column(Integer, nullable=True)  # max pages per day
    current_load = Column(Integer, default=0)  # current usage

    is_available = Column(Boolean, default=True)

    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    # Keep legacy columns for backward compatibility
    price_per_unit = Column(Integer, nullable=True)
    unit = Column(String(50), nullable=True)

    # Relationships
    vendor = relationship("User", back_populates="stationery_services")
