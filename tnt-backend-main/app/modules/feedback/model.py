from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    overall_rating = Column(Integer, nullable=True)
    quality_rating = Column(Integer, nullable=False)
    time_rating = Column(Integer, nullable=False)
    behavior_rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorReview(Base):
    __tablename__ = "vendor_reviews"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    rating = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    review_text = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=False)

    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)
