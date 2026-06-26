"""Vendor Retention Platform - Database Models."""

from __future__ import annotations

import enum
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Boolean, Text

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class OfferType(enum.Enum):
    DISCOUNT_PERCENTAGE = "discount_percentage"
    DISCOUNT_FIXED = "discount_fixed"
    COMBO_DEAL = "combo_deal"
    FREE_ITEM = "free_item"
    BUY_X_GET_Y = "buy_x_get_y"


class CampaignStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DiscountCampaign(Base):
    """Vendor-created discount campaigns."""
    __tablename__ = "discount_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    offer_type = Column(Enum(OfferType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    discount_value = Column(Float, nullable=True)  # percentage or fixed amount
    min_order_amount = Column(Float, nullable=True)
    max_discount_amount = Column(Float, nullable=True)
    is_combo = Column(Boolean, default=False)
    combo_items = Column(Text, nullable=True)  # JSON array of item IDs
    combo_price = Column(Float, nullable=True)
    is_off_peak = Column(Boolean, default=False)
    off_peak_start = Column(Integer, nullable=True)  # Hour (0-23)
    off_peak_end = Column(Integer, nullable=True)    # Hour (0-23)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    usage_limit = Column(Integer, nullable=True)
    times_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    status = Column(Enum(CampaignStatus, values_callable=lambda x: [e.value for e in x]), default=CampaignStatus.DRAFT)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorOffer(Base):
    """Individual offers created by vendors for specific customers."""
    __tablename__ = "vendor_offers"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    campaign_id = Column(Integer, ForeignKey("discount_campaigns.id"), nullable=True)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL = all customers
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    discount_type = Column(Enum(OfferType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    discount_value = Column(Float, nullable=False)
    min_order_amount = Column(Float, nullable=True)
    max_discount_amount = Column(Float, nullable=True)
    is_dynamic = Column(Boolean, default=False)  # AI-suggested discount
    ai_confidence = Column(Float, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    times_redeemed = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorCampaign(Base):
    """Vendor marketing campaigns."""
    __tablename__ = "vendor_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # discount, combo, off_peak, loyalty
    target_segment = Column(String(50), nullable=True)  # all, repeat, infrequent, lapsed
    budget = Column(Float, nullable=True)
    spent = Column(Float, default=0.0)
    impressions = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    status = Column(Enum(CampaignStatus, values_callable=lambda x: [e.value for e in x]), default=CampaignStatus.DRAFT)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorOfferRedemption(Base):
    """Track offer redemptions."""
    __tablename__ = "vendor_offer_redemptions"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(Integer, ForeignKey("vendor_offers.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    discount_amount = Column(Float, nullable=False)
    redeemed_at = Column(DateTime, default=utcnow_naive)