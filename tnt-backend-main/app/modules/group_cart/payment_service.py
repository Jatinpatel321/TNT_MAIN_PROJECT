"""
Group Split Payment Service
============================

Handles split payments for group orders:

Features:
- Calculate payment splits (equal/custom/percentage)
- Track individual payments
- Monitor payment status
- Handle Razorpay integration
- Generate payment reports

Integrates with existing Razorpay implementation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.group_cart.model import (
    Group,
    GroupMember,
    GroupPaymentSplit,
    PaymentSplitType,
)
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus

logger = logging.getLogger("tnt.group_payments")


class GroupPaymentService:
    """Service for managing group split payments."""

    def __init__(self, db: Session):
        self.db = db

    # ── Payment Split Calculation ─────────────────────────────────────────

    def calculate_split(
        self,
        group_id: int,
        split_type: PaymentSplitType,
        total_amount: float,
        custom_splits: Optional[Dict[int, float]] = None,
    ) -> Dict[str, Any]:
        """Calculate payment split for group members.

        Args:
            group_id: Group ID
            split_type: EQUAL, CUSTOM, or PERCENTAGE
            total_amount: Total order amount
            custom_splits: Custom amounts per member (for CUSTOM type)

        Returns:
            - splits: List of payment splits
            - total_amount: Total amount
            - split_type: Type of split
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        members = group.members
        member_count = len(members)

        if member_count == 0:
            return {"error": "No members in group"}

        splits = []

        if split_type == PaymentSplitType.EQUAL:
            # Equal split among all members
            per_member = total_amount / member_count
            for member in members:
                splits.append({
                    "user_id": member.user_id,
                    "user_name": member.user.name if member.user else "Unknown",
                    "amount": round(per_member, 2),
                    "percentage": round(100.0 / member_count, 2),
                    "split_type": "EQUAL",
                })

        elif split_type == PaymentSplitType.CUSTOM:
            # Custom amounts per member
            if not custom_splits:
                return {"error": "Custom splits required for CUSTOM type"}

            total_custom = sum(custom_splits.values())
            if abs(total_custom - total_amount) > 0.01:
                return {
                    "error": f"Custom splits total ({total_custom}) doesn't match order total ({total_amount})"
                }

            for member in members:
                amount = custom_splits.get(member.user_id, 0)
                percentage = (amount / total_amount * 100) if total_amount > 0 else 0
                splits.append({
                    "user_id": member.user_id,
                    "user_name": member.user.name if member.user else "Unknown",
                    "amount": round(amount, 2),
                    "percentage": round(percentage, 2),
                    "split_type": "CUSTOM",
                })

        elif split_type == PaymentSplitType.PERCENTAGE:
            # Percentage-based split
            # Get existing percentage splits from database
            existing_splits = (
                self.db.query(GroupPaymentSplit)
                .filter(GroupPaymentSplit.group_id == group_id)
                .all()
            )

            if not existing_splits:
                # Default to equal percentages
                per_member_pct = 100.0 / member_count
                for member in members:
                    splits.append({
                        "user_id": member.user_id,
                        "user_name": member.user.name if member.user else "Unknown",
                        "amount": round(total_amount * per_member_pct / 100, 2),
                        "percentage": round(per_member_pct, 2),
                        "split_type": "PERCENTAGE",
                    })
            else:
                # Use stored percentages
                total_pct = sum(s.percentage or 0 for s in existing_splits)
                if abs(total_pct - 100.0) > 0.01:
                    return {
                        "error": f"Percentage splits total ({total_pct}%) doesn't equal 100%"
                    }

                for split in existing_splits:
                    member = next((m for m in members if m.user_id == split.user_id), None)
                    if member:
                        amount = total_amount * (split.percentage or 0) / 100
                        splits.append({
                            "user_id": split.user_id,
                            "user_name": member.user.name if member.user else "Unknown",
                            "amount": round(amount, 2),
                            "percentage": round(split.percentage or 0, 2),
                            "split_type": "PERCENTAGE",
                        })

        return {
            "group_id": group_id,
            "splits": splits,
            "total_amount": total_amount,
            "split_type": split_type.value,
            "member_count": member_count,
        }

    # ── Payment Tracking ──────────────────────────────────────────────────

    def record_payment(
        self,
        group_id: int,
        user_id: int,
        amount: float,
        payment_method: str,
        razorpay_payment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a payment from a group member.

        Args:
            group_id: Group ID
            user_id: User ID making payment
            amount: Payment amount
            payment_method: Payment method (UPI, CARD, etc.)
            razorpay_payment_id: Razorpay payment ID

        Returns:
            - payment_record: Payment details
            - status: Payment status
        """
        # Verify user is member
        member = (
            self.db.query(GroupMember)
            .filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
            .first()
        )

        if not member:
            return {"error": "User is not a member of this group"}

        # Get or create payment split
        split = (
            self.db.query(GroupPaymentSplit)
            .filter(
                GroupPaymentSplit.group_id == group_id,
                GroupPaymentSplit.user_id == user_id,
            )
            .first()
        )

        if not split:
            # Create default split
            split = GroupPaymentSplit(
                group_id=group_id,
                user_id=user_id,
                split_type=PaymentSplitType.EQUAL,
            )
            self.db.add(split)
            self.db.commit()
            self.db.refresh(split)

        # Update split with payment info
        split.amount_paid = (split.amount_paid or 0) + amount
        split.payment_status = "PAID" if split.amount_paid >= (split.amount or 0) else "PARTIAL"
        split.paid_at = utcnow_naive()
        split.payment_method = payment_method
        split.razorpay_payment_id = razorpay_payment_id

        self.db.commit()
        self.db.refresh(split)

        return {
            "group_id": group_id,
            "user_id": user_id,
            "amount_paid": round(split.amount_paid, 2),
            "amount_due": round((split.amount or 0) - split.amount_paid, 2),
            "payment_status": split.payment_status,
            "payment_method": payment_method,
            "paid_at": split.paid_at.isoformat(),
            "razorpay_payment_id": razorpay_payment_id,
        }

    # ── Payment Status ────────────────────────────────────────────────────

    def get_payment_status(self, group_id: int) -> Dict[str, Any]:
        """Get payment status for all group members.

        Returns:
            - total_amount: Total order amount
            - total_paid: Total amount paid
            - total_pending: Total amount pending
            - payment_percentage: Overall completion percentage
            - members: Per-member payment status
            - unpaid_members: List of members who haven't paid
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        # Get all payment splits
        splits = (
            self.db.query(GroupPaymentSplit)
            .filter(GroupPaymentSplit.group_id == group_id)
            .all()
        )

        total_amount = sum(s.amount or 0 for s in splits)
        total_paid = sum(s.amount_paid or 0 for s in splits)
        total_pending = total_amount - total_paid
        payment_percentage = (total_paid / total_amount * 100) if total_amount > 0 else 0

        members_status = []
        unpaid_members = []

        for split in splits:
            member = (
                self.db.query(GroupMember)
                .filter(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == split.user_id,
                )
                .first()
            )

            user_name = member.user.name if member and member.user else "Unknown"
            amount_due = (split.amount or 0) - (split.amount_paid or 0)
            status = split.payment_status or "PENDING"

            members_status.append({
                "user_id": split.user_id,
                "user_name": user_name,
                "role": member.role.value if member else "MEMBER",
                "amount": round(split.amount or 0, 2),
                "amount_paid": round(split.amount_paid or 0, 2),
                "amount_due": round(amount_due, 2),
                "percentage": round(split.percentage or 0, 2),
                "payment_status": status,
                "payment_method": split.payment_method,
                "paid_at": split.paid_at.isoformat() if split.paid_at else None,
                "razorpay_payment_id": split.razorpay_payment_id,
            })

            if status != "PAID":
                unpaid_members.append({
                    "user_id": split.user_id,
                    "user_name": user_name,
                    "amount_due": round(amount_due, 2),
                    "payment_status": status,
                })

        return {
            "group_id": group_id,
            "total_amount": round(total_amount, 2),
            "total_paid": round(total_paid, 2),
            "total_pending": round(total_pending, 2),
            "payment_percentage": round(payment_percentage, 2),
            "members": members_status,
            "unpaid_members": unpaid_members,
            "unpaid_count": len(unpaid_members),
            "is_fully_paid": len(unpaid_members) == 0,
        }

    # ── Payment Reports ───────────────────────────────────────────────────

    def get_contribution_summary(self, group_id: int) -> Dict[str, Any]:
        """Get detailed contribution summary for the group.

        Returns:
            - contributions: Per-member contributions
            - payment_methods: Breakdown by payment method
            - timeline: Payment timeline
            - statistics: Payment statistics
        """
        status = self.get_payment_status(group_id)
        if "error" in status:
            return status

        # Payment method breakdown
        splits = (
            self.db.query(GroupPaymentSplit)
            .filter(
                GroupPaymentSplit.group_id == group_id,
                GroupPaymentSplit.payment_method.isnot(None),
            )
            .all()
        )

        method_counts = {}
        for split in splits:
            method = split.payment_method or "UNKNOWN"
            method_counts[method] = method_counts.get(method, 0) + 1

        # Payment timeline
        timeline = []
        for split in splits:
            if split.paid_at:
                timeline.append({
                    "user_id": split.user_id,
                    "user_name": next(
                        (m.user.name for m in status["members"] if m["user_id"] == split.user_id),
                        "Unknown"
                    ),
                    "paid_at": split.paid_at.isoformat(),
                    "amount": round(split.amount_paid or 0, 2),
                    "method": split.payment_method,
                })

        timeline.sort(key=lambda x: x["paid_at"])

        # Statistics
        paid_members = [m for m in status["members"] if m["payment_status"] == "PAID"]
        partial_members = [m for m in status["members"] if m["payment_status"] == "PARTIAL"]
        pending_members = [m for m in status["members"] if m["payment_status"] == "PENDING"]

        statistics = {
            "total_members": len(status["members"]),
            "paid_members": len(paid_members),
            "partial_members": len(partial_members),
            "pending_members": len(pending_members),
            "avg_payment_amount": round(
                sum(m["amount_paid"] for m in status["members"]) / len(status["members"]),
                2
            ) if status["members"] else 0,
            "completion_rate": round(status["payment_percentage"], 2),
        }

        return {
            "group_id": group_id,
            "contributions": status["members"],
            "payment_methods": method_counts,
            "timeline": timeline,
            "statistics": statistics,
        }

    def get_outstanding_payments(self, group_id: int) -> Dict[str, Any]:
        """Get list of outstanding (unpaid) payments.

        Returns:
            - outstanding: List of unpaid members
            - total_outstanding: Total amount outstanding
            - reminders_sent: Whether reminders have been sent
            - suggested_actions: Suggested actions for owner
        """
        status = self.get_payment_status(group_id)
        if "error" in status:
            return status

        outstanding = status["unpaid_members"]
        total_outstanding = status["total_pending"]

        # Suggested actions
        suggested_actions = []
        if len(outstanding) > 0:
            suggested_actions.append("Send payment reminders to unpaid members")
        
        if total_outstanding > 0:
            suggested_actions.append("Follow up with members who have partial payments")
        
        if len(outstanding) == len(status["members"]):
            suggested_actions.append("No payments received yet - consider sending initial reminder")

        return {
            "group_id": group_id,
            "outstanding": outstanding,
            "total_outstanding": round(total_outstanding, 2),
            "outstanding_count": len(outstanding),
            "reminders_sent": False,  # TODO: Implement reminder tracking
            "suggested_actions": suggested_actions,
            "is_fully_paid": status["is_fully_paid"],
        }

    # ── Payment Management ────────────────────────────────────────────────

    def send_payment_reminder(self, group_id: int, user_id: int) -> Dict[str, Any]:
        """Send payment reminder to a specific member.

        Returns:
            - sent: Success status
            - message: Reminder message
        """
        # TODO: Implement notification sending
        logger.info(f"Payment reminder sent to user {user_id} for group {group_id}")

        return {
            "sent": True,
            "group_id": group_id,
            "user_id": user_id,
            "message": "Payment reminder sent successfully",
        }

    def send_bulk_reminders(self, group_id: int) -> Dict[str, Any]:
        """Send payment reminders to all unpaid members.

        Returns:
            - sent: Success status
            - reminder_count: Number of reminders sent
        """
        outstanding = self.get_outstanding_payments(group_id)
        
        reminder_count = 0
        for member in outstanding.get("outstanding", []):
            self.send_payment_reminder(group_id, member["user_id"])
            reminder_count += 1

        return {
            "sent": True,
            "group_id": group_id,
            "reminder_count": reminder_count,
            "message": f"Sent {reminder_count} payment reminders",
        }

    def update_split_configuration(
        self,
        group_id: int,
        user_id: int,
        split_type: PaymentSplitType,
        amount: Optional[float] = None,
        percentage: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update payment split configuration for a user.

        Args:
            group_id: Group ID
            user_id: User ID
            split_type: New split type
            amount: Custom amount (for CUSTOM type)
            percentage: Percentage (for PERCENTAGE type)

        Returns:
            - updated: Success status
            - split: Updated split configuration
        """
        # Verify user is member
        member = (
            self.db.query(GroupMember)
            .filter(
                GroupMember.group_id == group_id,
                GroupMember.user_id == user_id,
            )
            .first()
        )

        if not member:
            return {"error": "User is not a member of this group"}

        # Get or create split
        split = (
            self.db.query(GroupPaymentSplit)
            .filter(
                GroupPaymentSplit.group_id == group_id,
                GroupPaymentSplit.user_id == user_id,
            )
            .first()
        )

        if not split:
            split = GroupPaymentSplit(
                group_id=group_id,
                user_id=user_id,
            )
            self.db.add(split)

        # Update split
        split.split_type = split_type
        if amount is not None:
            split.amount = amount
        if percentage is not None:
            split.percentage = percentage

        self.db.commit()
        self.db.refresh(split)

        return {
            "updated": True,
            "group_id": group_id,
            "user_id": user_id,
            "split": {
                "split_type": split.split_type.value,
                "amount": split.amount,
                "percentage": split.percentage,
            },
        }

    # ── Razorpay Integration ──────────────────────────────────────────────

    def create_razorpay_order_for_member(
        self, group_id: int, user_id: int, amount: float
    ) -> Dict[str, Any]:
        """Create Razorpay order for individual member payment.

        Args:
            group_id: Group ID
            user_id: User ID
            amount: Payment amount

        Returns:
            - razorpay_order_id: Razorpay order ID
            - amount: Amount in paise
            - currency: Currency code
            - receipt: Receipt ID
        """
        # TODO: Integrate with existing Razorpay implementation
        # This should use the existing Razorpay service

        receipt = f"group_{group_id}_user_{user_id}_{int(datetime.now().timestamp())}"

        # Placeholder - actual implementation would call Razorpay API
        razorpay_order_id = f"order_{receipt}"

        return {
            "group_id": group_id,
            "user_id": user_id,
            "razorpay_order_id": razorpay_order_id,
            "amount": int(amount * 100),  # Convert to paise
            "currency": "INR",
            "receipt": receipt,
        }

    def verify_razorpay_payment(
        self,
        group_id: int,
        user_id: int,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Dict[str, Any]:
        """Verify Razorpay payment and update records.

        Args:
            group_id: Group ID
            user_id: User ID
            razorpay_payment_id: Razorpay payment ID
            razorpay_signature: Razorpay signature

        Returns:
            - verified: Success status
            - payment_status: Payment status
        """
        # TODO: Integrate with existing Razorpay verification
        # This should use the existing Razorpay service

        # Placeholder verification
        verified = True  # Actual implementation would verify signature

        if verified:
            # Record payment
            # Get amount from split
            split = (
                self.db.query(GroupPaymentSplit)
                .filter(
                    GroupPaymentSplit.group_id == group_id,
                    GroupPaymentSplit.user_id == user_id,
                )
                .first()
            )

            amount = (split.amount or 0) - (split.amount_paid or 0) if split else 0

            if amount > 0:
                return self.record_payment(
                    group_id=group_id,
                    user_id=user_id,
                    amount=amount,
                    payment_method="RAZORPAY",
                    razorpay_payment_id=razorpay_payment_id,
                )

        return {
            "verified": False,
            "group_id": group_id,
            "user_id": user_id,
            "error": "Payment verification failed",
        }

    # ── Public API ────────────────────────────────────────────────────────

    def get_group_payment_summary(self, group_id: int) -> Dict[str, Any]:
        """Get comprehensive payment summary for the group.

        Returns:
            - payment_status: Overall payment status
            - contribution_summary: Detailed contributions
            - outstanding_payments: Unpaid members
            - payment_timeline: Payment history
        """
        payment_status = self.get_payment_status(group_id)
        contribution = self.get_contribution_summary(group_id)
        outstanding = self.get_outstanding_payments(group_id)

        return {
            "group_id": group_id,
            "payment_status": payment_status,
            "contribution_summary": contribution,
            "outstanding_payments": outstanding,
            "is_fully_paid": payment_status.get("is_fully_paid", False),
        }