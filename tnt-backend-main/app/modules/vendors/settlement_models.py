"""Vendor Settlement System - Database Models."""

from __future__ import annotations

import enum
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Boolean, Text

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class SettlementStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionType(enum.Enum):
    ONLINE_PAYMENT = "online_payment"
    CASH_ORDER = "cash_order"
    REFUND = "refund"
    SETTLEMENT = "settlement"
    WITHDRAWAL = "withdrawal"
    ADJUSTMENT = "adjustment"


class VendorWallet(Base):
    """Vendor wallet tracking total balance."""
    __tablename__ = "vendor_wallets"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    total_earned = Column(Float, default=0.0)
    total_pending = Column(Float, default=0.0)
    total_settled = Column(Float, default=0.0)
    total_refunded = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorTransaction(Base):
    """Individual vendor transactions."""
    __tablename__ = "vendor_transactions"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    transaction_type = Column(Enum(TransactionType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)
    payment_method = Column(String(50), nullable=True)
    is_online = Column(Boolean, default=False)
    status = Column(String(20), default="completed")
    created_at = Column(DateTime, default=utcnow_naive)


class VendorSettlement(Base):
    """Vendor settlement cycles."""
    __tablename__ = "vendor_settlements"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False)
    total_fees = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    order_count = Column(Integer, default=0)
    online_payments = Column(Float, default=0.0)
    cash_orders = Column(Float, default=0.0)
    refunds = Column(Float, default=0.0)
    status = Column(Enum(SettlementStatus, values_callable=lambda x: [e.value for e in x]), default=SettlementStatus.PENDING)
    settled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class VendorRefund(Base):
    """Vendor refund tracking."""
    __tablename__ = "vendor_refunds"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=True)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=True)
    razorpay_refund_id = Column(String, nullable=True)
    status = Column(String(20), default="initiated")  # initiated, processed, failed
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)