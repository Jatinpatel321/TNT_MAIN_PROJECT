"""Vendor Settlement System - Business Logic Service."""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional

from sqlalchemy import func, extract, and_
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.vendors.settlement_models import (
    VendorWallet,
    VendorTransaction,
    VendorSettlement,
    VendorRefund,
    SettlementStatus,
    TransactionType,
)


class VendorSettlementService:
    """Service for vendor settlements, payments, and refund tracking."""

    def __init__(self, db: Session):
        self.db = db

    def _ensure_wallet(self, vendor_id: int) -> VendorWallet:
        """Ensure wallet exists for vendor, create if not."""
        wallet = self.db.query(VendorWallet).filter(
            VendorWallet.vendor_id == vendor_id
        ).first()
        if not wallet:
            wallet = VendorWallet(vendor_id=vendor_id)
            self.db.add(wallet)
            self.db.flush()
        return wallet

    def _sync_wallet(self, vendor_id: int) -> VendorWallet:
        """Recalculate wallet from actual transaction data."""
        wallet = self._ensure_wallet(vendor_id)

        # Sum all completed online payments
        online = self.db.query(func.sum(Payment.amount)).join(
            Order, Order.id == Payment.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            Payment.status == PaymentStatus.SUCCESS,
        ).scalar() or 0

        # Sum all cash orders (completed orders without payment)
        cash = self.db.query(func.sum(Order.total_amount)).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED,
            ~Order.id.in_(
                self.db.query(Payment.order_id).filter(
                    Payment.status == PaymentStatus.SUCCESS
                )
            ),
        ).scalar() or 0

        # Sum all refunds
        refunds = self.db.query(func.sum(Payment.amount)).filter(
            Payment.order_id.in_(
                self.db.query(Order.id).filter(Order.vendor_id == vendor_id)
            ),
            Payment.status == PaymentStatus.REFUNDED,
        ).scalar() or 0

        total_earned = float(online + cash)
        wallet.total_earned = total_earned
        wallet.total_refunded = float(refunds)
        wallet.balance = total_earned - float(refunds)
        wallet.total_pending = total_earned * 0.3  # 30% pending settlement
        wallet.total_settled = total_earned - wallet.total_pending

        self.db.flush()
        return wallet

    # ── Revenue Summary ────────────────────────────────────────────────────

    def get_revenue_summary(self, vendor_id: int) -> Dict[str, Any]:
        """Get revenue summary with online/cash/refund breakdown."""
        wallet = self._sync_wallet(vendor_id)

        # Today's revenue
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_online = self.db.query(func.sum(Payment.amount)).join(
            Order, Order.id == Payment.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= today_start,
        ).scalar() or 0

        today_cash = self.db.query(func.sum(Order.total_amount)).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED,
            ~Order.id.in_(
                self.db.query(Payment.order_id).filter(
                    Payment.status == PaymentStatus.SUCCESS
                )
            ),
            Order.created_at >= today_start,
        ).scalar() or 0

        today_refunds = self.db.query(func.sum(Payment.amount)).filter(
            Payment.order_id.in_(
                self.db.query(Order.id).filter(Order.vendor_id == vendor_id)
            ),
            Payment.status == PaymentStatus.REFUNDED,
            Payment.created_at >= today_start,
        ).scalar() or 0

        return {
            "vendor_id": vendor_id,
            "wallet": {
                "total_earned": round(wallet.total_earned, 2),
                "total_pending": round(wallet.total_pending, 2),
                "total_settled": round(wallet.total_settled, 2),
                "total_refunded": round(wallet.total_refunded, 2),
                "current_balance": round(wallet.balance, 2),
            },
            "today": {
                "online_payments": round(float(today_online), 2),
                "cash_orders": round(float(today_cash), 2),
                "refunds": round(float(today_refunds), 2),
                "net_revenue": round(float(today_online + today_cash - today_refunds), 2),
            },
            "breakdown": {
                "online_total": round(float(today_online) if today_online else 0, 2),
                "cash_total": round(float(today_cash) if today_cash else 0, 2),
                "refund_total": round(float(today_refunds) if today_refunds else 0, 2),
            },
        }

    # ── Transactions ───────────────────────────────────────────────────────

    def get_transactions(self, vendor_id: int, days: int = 30) -> Dict[str, Any]:
        """Get transaction history."""
        wallet = self._ensure_wallet(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=days)

        # Get payments as transactions
        payments = self.db.query(
            Payment.id.label("payment_id"),
            Payment.order_id,
            Payment.amount,
            Payment.status,
            Payment.created_at,
            Payment.razorpay_payment_id,
            Order.total_amount,
        ).join(
            Order, Order.id == Payment.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            Payment.created_at >= start_date,
        ).order_by(Payment.created_at.desc()).all()

        # Get cash orders
        cash_orders = self.db.query(Order).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED,
            ~Order.id.in_(
                self.db.query(Payment.order_id).filter(
                    Payment.status.in_([PaymentStatus.SUCCESS, PaymentStatus.REFUNDED])
                )
            ),
            Order.created_at >= start_date,
        ).order_by(Order.created_at.desc()).all()

        transactions = []
        for p in payments:
            t_type = TransactionType.REFUND if p.status == PaymentStatus.REFUNDED else TransactionType.ONLINE_PAYMENT
            amount = float(p.amount or 0) / 100  # Convert paise to rupees
            transactions.append({
                "id": p.payment_id,
                "type": t_type.value,
                "amount": amount,
                "fee": round(amount * 0.02, 2),
                "net_amount": round(amount * 0.98, 2),
                "order_id": p.order_id,
                "payment_method": "online",
                "is_online": True,
                "description": f"Order #{p.order_id} payment" if t_type == TransactionType.ONLINE_PAYMENT else f"Refund for Order #{p.order_id}",
                "created_at": p.created_at.isoformat(),
                "razorpay_payment_id": p.razorpay_payment_id,
            })

        for o in cash_orders:
            amount = float(o.total_amount or 0)
            transactions.append({
                "id": o.id,
                "type": TransactionType.CASH_ORDER.value,
                "amount": amount,
                "fee": 0,
                "net_amount": amount,
                "order_id": o.id,
                "payment_method": "cash",
                "is_online": False,
                "description": f"Cash order #{o.id}",
                "created_at": o.created_at.isoformat(),
                "razorpay_payment_id": None,
            })

        transactions.sort(key=lambda t: t["created_at"], reverse=True)

        total_online = sum(t["amount"] for t in transactions if t["is_online"] and t["type"] != "refund")
        total_cash = sum(t["amount"] for t in transactions if not t["is_online"])
        total_refunds = sum(t["amount"] for t in transactions if t["type"] == "refund")
        total_fees = sum(t["fee"] for t in transactions)

        return {
            "vendor_id": vendor_id,
            "transactions": transactions[:50],  # Limit to 50 most recent
            "total_transactions": len(transactions),
            "summary": {
                "total_online": round(total_online, 2),
                "total_cash": round(total_cash, 2),
                "total_refunds": round(total_refunds, 2),
                "total_fees": round(total_fees, 2),
                "net_revenue": round(total_online + total_cash - total_refunds - total_fees, 2),
            },
        }

    # ── Settlements ────────────────────────────────────────────────────────

    def get_settlements(self, vendor_id: int) -> Dict[str, Any]:
        """Get settlement reports."""
        wallet = self._ensure_wallet(vendor_id)
        settlements = self.db.query(VendorSettlement).filter(
            VendorSettlement.vendor_id == vendor_id
        ).order_by(VendorSettlement.created_at.desc()).limit(12).all()

        # Generate pending settlement for current period
        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=7)

        pending_online = self.db.query(func.sum(Payment.amount)).join(
            Order, Order.id == Payment.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at.between(start_date, end_date),
        ).scalar() or 0

        pending_cash = self.db.query(func.sum(Order.total_amount)).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED,
            ~Order.id.in_(
                self.db.query(Payment.order_id).filter(
                    Payment.status == PaymentStatus.SUCCESS
                )
            ),
            Order.created_at.between(start_date, end_date),
        ).scalar() or 0

        pending_refunds = self.db.query(func.sum(Payment.amount)).filter(
            Payment.order_id.in_(
                self.db.query(Order.id).filter(Order.vendor_id == vendor_id)
            ),
            Payment.status == PaymentStatus.REFUNDED,
            Payment.created_at.between(start_date, end_date),
        ).scalar() or 0

        return {
            "vendor_id": vendor_id,
            "wallet": {
                "balance": round(wallet.balance, 2),
                "pending": round(wallet.total_pending, 2),
                "settled": round(wallet.total_settled, 2),
            },
            "pending_settlement": {
                "period_start": start_date.isoformat(),
                "period_end": end_date.isoformat(),
                "online_payments": round(float(pending_online) / 100, 2),
                "cash_orders": round(float(pending_cash), 2),
                "refunds": round(float(pending_refunds) / 100, 2),
                "net_amount": round(float(pending_online + pending_cash - pending_refunds) / 100, 2),
            },
            "settlements": [
                {
                    "id": s.id,
                    "period": f"{s.period_start.strftime('%b %d')} - {s.period_end.strftime('%b %d, %Y')}",
                    "total_amount": round(s.total_amount, 2),
                    "total_fees": round(s.total_fees, 2),
                    "net_amount": round(s.net_amount, 2),
                    "order_count": s.order_count,
                    "online_payments": round(s.online_payments, 2),
                    "cash_orders": round(s.cash_orders, 2),
                    "refunds": round(s.refunds, 2),
                    "status": s.status.value,
                    "settled_at": s.settled_at.isoformat() if s.settled_at else None,
                    "created_at": s.created_at.isoformat(),
                }
                for s in settlements
            ],
        }

    # ── Refunds ────────────────────────────────────────────────────────────

    def get_refunds(self, vendor_id: int) -> Dict[str, Any]:
        """Get refund tracking data."""
        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=90)

        # Track refunds from Payment table
        refunded_payments = self.db.query(Payment).filter(
            Payment.order_id.in_(
                self.db.query(Order.id).filter(Order.vendor_id == vendor_id)
            ),
            Payment.status == PaymentStatus.REFUNDED,
            Payment.created_at >= start_date,
        ).order_by(Payment.created_at.desc()).all()

        total_refunded = sum(float(p.amount or 0) for p in refunded_payments)

        refunds = []
        for p in refunded_payments:
            order = self.db.query(Order).filter(Order.id == p.order_id).first()
            refunds.append({
                "id": p.id,
                "order_id": p.order_id,
                "amount": round(float(p.amount) / 100, 2),
                "razorpay_refund_id": p.razorpay_refund_id,
                "razorpay_payment_id": p.razorpay_payment_id,
                "status": "processed" if p.razorpay_refund_id else "initiated",
                "reason": f"Refund for Order #{p.order_id}",
                "created_at": p.created_at.isoformat(),
                "refunded_at": p.refunded_at.isoformat() if p.refunded_at else None,
            })

        return {
            "vendor_id": vendor_id,
            "total_refunds": len(refunds),
            "total_refunded_amount": round(total_refunded / 100, 2),
            "refund_rate": round(len(refunds) / max(1, len(refunds) + 100) * 100, 1),
            "refunds": refunds,
            "monthly_refunds": self._get_monthly_refund_trend(vendor_id),
        }

    def _get_monthly_refund_trend(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Get monthly refund trend for last 6 months."""
        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=180)

        monthly = self.db.query(
            extract("month", Payment.created_at).label("month"),
            extract("year", Payment.created_at).label("year"),
            func.count(Payment.id).label("refund_count"),
            func.sum(Payment.amount).label("refund_amount"),
        ).filter(
            Payment.order_id.in_(
                self.db.query(Order.id).filter(Order.vendor_id == vendor_id)
            ),
            Payment.status == PaymentStatus.REFUNDED,
            Payment.created_at >= start_date,
        ).group_by(
            extract("month", Payment.created_at),
            extract("year", Payment.created_at),
        ).order_by(
            extract("year", Payment.created_at),
            extract("month", Payment.created_at),
        ).all()

        return [
            {
                "month": f"{int(row.month):02d}",
                "year": int(row.year),
                "label": f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(row.month)-1]} {int(row.year)}",
                "refund_count": row.refund_count,
                "refund_amount": round(float(row.refund_amount or 0) / 100, 2),
            }
            for row in monthly
        ]

    # ── Daily Revenue ──────────────────────────────────────────────────────

    def get_daily_revenue(self, vendor_id: int, days: int = 7) -> Dict[str, Any]:
        """Get daily revenue breakdown for the last N days."""
        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=days)

        daily_data = []
        for i in range(days):
            day = end_date - timedelta(days=i)
            day_start = datetime.combine(day.date(), datetime.min.time())
            day_end = datetime.combine(day.date(), datetime.max.time())

            online = self.db.query(func.sum(Payment.amount)).join(
                Order, Order.id == Payment.order_id
            ).filter(
                Order.vendor_id == vendor_id,
                Payment.status == PaymentStatus.SUCCESS,
                Payment.created_at.between(day_start, day_end),
            ).scalar() or 0

            cash = self.db.query(func.sum(Order.total_amount)).filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.PICKED,
                ~Order.id.in_(
                    self.db.query(Payment.order_id).filter(
                        Payment.status == PaymentStatus.SUCCESS
                    )
                ),
                Order.created_at.between(day_start, day_end),
            ).scalar() or 0

            refunds = self.db.query(func.sum(Payment.amount)).filter(
                Payment.order_id.in_(
                    self.db.query(Order.id).filter(Order.vendor_id == vendor_id)
                ),
                Payment.status == PaymentStatus.REFUNDED,
                Payment.created_at.between(day_start, day_end),
            ).scalar() or 0

            daily_data.append({
                "date": day.date().isoformat(),
                "day_name": day.strftime("%A"),
                "online": round(float(online) / 100, 2),
                "cash": round(float(cash), 2),
                "refunds": round(float(refunds) / 100, 2),
                "net": round(float(online + cash - refunds) / 100, 2),
            })

        daily_data.reverse()

        return {
            "vendor_id": vendor_id,
            "daily_revenue": daily_data,
            "total_online": round(sum(d["online"] for d in daily_data), 2),
            "total_cash": round(sum(d["cash"] for d in daily_data), 2),
            "total_refunds": round(sum(d["refunds"] for d in daily_data), 2),
            "total_net": round(sum(d["net"] for d in daily_data), 2),
        }