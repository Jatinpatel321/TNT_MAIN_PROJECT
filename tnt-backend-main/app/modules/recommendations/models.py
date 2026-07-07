"""
User Behaviour Tracking Models
==============================

Stores granular user interaction events for preference learning
and recommendation engine improvements.

Does NOT duplicate existing order/menu/vendor tables.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, JSON, Index
from sqlalchemy.orm import relationship

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class UserBehaviour(Base):
    """Records every user interaction for behaviour learning.

    Tracks:
        - Vendor visits (page_view)
        - Menu item clicks (item_click)
        - Search queries (search)
        - Order events (order_placed, order_cancelled)
        - Category browsing (category_view)
        - Favourite toggles (favourite)

    This is append-only.  Old rows can be archived after 90 days.
    """

    __tablename__ = "user_behaviour"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Event taxonomy
    event_type = Column(String(50), nullable=False, index=True)

    # Polymorphic target identifiers (one of these is set)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    category = Column(String(100), nullable=True)

    # Search context
    search_query = Column(String(500), nullable=True)
    search_results_count = Column(Integer, nullable=True)

    # Interaction metadata
    source_screen = Column(String(100), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    referrer = Column(String(100), nullable=True)

    # Weight / importance (higher = stronger signal)
    weight = Column(Float, nullable=False, default=1.0)

    # Timestamp
    created_at = Column(DateTime, default=utcnow_naive, nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    vendor = relationship("User", foreign_keys=[vendor_id])
    menu_item = relationship("MenuItem", foreign_keys=[menu_item_id])

    __table_args__ = (
        Index("ix_user_behaviour_user_event", "user_id", "event_type"),
        Index("ix_user_behaviour_user_created", "user_id", "created_at"),
    )


class UserPreferenceSnapshot(Base):
    """Materialised preference snapshot for quick lookup.

    Continuously updated by the preference learning service.
    Avoids expensive aggregation queries on every recommendation request.
    """

    __tablename__ = "user_preference_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Favourite vendors (JSON array of {vendor_id, score, order_count})
    favourite_vendors = Column(JSON, nullable=False, default=list)

    # Favourite menu items (JSON array of {item_id, name, score, order_count})
    favourite_menu_items = Column(JSON, nullable=False, default=list)

    # Favourite categories (JSON array of {category, score})
    favourite_categories = Column(JSON, nullable=False, default=list)

    # Preferred pickup timings (JSON: {hour_distribution: {0: n, ...}, preferred_hour: int})
    preferred_timings = Column(JSON, nullable=False, default=dict)

    # Derived preferences
    preferred_vendor_types = Column(JSON, nullable=False, default=list)
    avg_order_frequency_days = Column(Float, nullable=True)
    total_orders = Column(Integer, nullable=False, default=0)
    is_veg_preferred = Column(Integer, nullable=True)

    # Last computed
    computed_at = Column(DateTime, default=utcnow_naive, nullable=False)

    # Relationship
    user = relationship("User", foreign_keys=[user_id])


class PredictionHistory(Base):
    """Stores prediction history for learning and accuracy tracking.

    Each prediction made by the ML engine is logged here with actual outcomes
    to continuously improve prediction accuracy.
    """

    __tablename__ = "prediction_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Prediction type
    prediction_type = Column(String(50), nullable=False, index=True)
    # Types: "next_order", "preferred_time", "preferred_vendor", "preferred_item"

    # Predicted values
    predicted_vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    predicted_menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    predicted_hour = Column(Integer, nullable=True)
    predicted_day_of_week = Column(Integer, nullable=True)  # 0=Monday, 6=Sunday

    # Confidence score (0.0 to 1.0)
    confidence_score = Column(Float, nullable=False)

    # Prediction metadata
    prediction_data = Column(JSON, nullable=False, default=dict)
    # Stores: {"pattern": "weekly", "frequency": "daily", "semester_phase": "mid"}

    # Actual outcome (filled when order is placed)
    actual_vendor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actual_menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=True)
    actual_order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    actual_hour = Column(Integer, nullable=True)
    was_correct = Column(Integer, nullable=True)  # 1=correct, 0=incorrect, NULL=pending

    # Timestamps
    predicted_at = Column(DateTime, default=utcnow_naive, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    predicted_vendor = relationship("User", foreign_keys=[predicted_vendor_id])
    predicted_menu_item = relationship("MenuItem", foreign_keys=[predicted_menu_item_id])
    actual_vendor = relationship("User", foreign_keys=[actual_vendor_id])
    actual_menu_item = relationship("MenuItem", foreign_keys=[actual_menu_item_id])

    __table_args__ = (
        Index("ix_prediction_user_type", "user_id", "prediction_type"),
        Index("ix_prediction_user_created", "user_id", "predicted_at"),
    )
