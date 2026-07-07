import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.auditlog.model import AuditLog
from app.modules.auditlog.service import AuditAction
from app.modules.fraud.model import FraudAlert
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.rewards.model import RewardRedemption, VoucherRedemption
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus

logger = logging.getLogger("tnt.fraud.service")


def get_severity_level(score: float) -> str:
    if score < 30:
        return "low"
    elif score < 60:
        return "medium"
    elif score < 85:
        return "high"
    else:
        return "critical"


def check_and_create_alert(
    db: Session,
    alert_type: str,
    score: float,
    description: str,
    user_id: Optional[int] = None,
    vendor_id: Optional[int] = None,
    order_id: Optional[int] = None,
) -> Optional[FraudAlert]:
    """Helper to write a FraudAlert, avoiding duplicates within a 1-hour window."""
    now = utcnow_naive()
    one_hour_ago = now - timedelta(hours=1)

    # Check if a similar active alert was recently created to prevent spam
    existing = (
        db.query(FraudAlert)
        .filter(
            FraudAlert.alert_type == alert_type,
            FraudAlert.status == "pending",
            FraudAlert.created_at >= one_hour_ago,
        )
    )
    if user_id:
        existing = existing.filter(FraudAlert.user_id == user_id)
    if vendor_id:
        existing = existing.filter(FraudAlert.vendor_id == vendor_id)
    if order_id:
        existing = existing.filter(FraudAlert.order_id == order_id)

    existing_alert = existing.first()
    if existing_alert:
        # Update existing alert score/description if needed
        existing_alert.score = max(existing_alert.score, score)
        existing_alert.severity = get_severity_level(existing_alert.score)
        existing_alert.description = description
        existing_alert.updated_at = now
        db.flush()
        return existing_alert

    severity = get_severity_level(score)
    alert = FraudAlert(
        user_id=user_id,
        vendor_id=vendor_id,
        order_id=order_id,
        alert_type=alert_type,
        severity=severity,
        score=score,
        description=description,
        status="pending",
    )
    db.add(alert)
    db.flush()
    logger.warning("fraud_alert_created type=%s score=%s user_id=%s", alert_type, score, user_id)
    return alert


class FraudDetectionService:

    @staticmethod
    def detect_duplicate_orders(db: Session, order: Order) -> Optional[FraudAlert]:
        """1. Duplicate Orders: Same user, vendor, and amount within 2 minutes."""
        now = utcnow_naive()
        two_minutes_ago = now - timedelta(minutes=2)

        duplicates = (
            db.query(Order)
            .filter(
                Order.user_id == order.user_id,
                Order.vendor_id == order.vendor_id,
                Order.total_amount == order.total_amount,
                Order.created_at >= two_minutes_ago,
                Order.id != order.id,
            )
            .all()
        )

        if duplicates:
            count = len(duplicates) + 1
            desc = (
                f"Duplicate Orders: user placed {count} identical orders of "
                f"₹{order.total_amount / 100:.2f} with same vendor in 2 mins."
            )
            return check_and_create_alert(
                db=db,
                alert_type="duplicate_orders",
                score=90.0,  # Critical
                description=desc,
                user_id=order.user_id,
                vendor_id=order.vendor_id,
                order_id=order.id,
            )
        return None

    @staticmethod
    def detect_repeated_refunds(db: Session, user_id: int) -> Optional[FraudAlert]:
        """2. Repeated Refund Requests: Users with 3+ refunded payments in 30 days."""
        now = utcnow_naive()
        thirty_days_ago = now - timedelta(days=30)

        refund_count = (
            db.query(Payment)
            .join(Order, Payment.order_id == Order.id)
            .filter(
                Order.user_id == user_id,
                Payment.status == PaymentStatus.REFUNDED,
                Payment.created_at >= thirty_days_ago,
            )
            .count()
        )

        if refund_count >= 3:
            desc = f"Repeated Refund Requests: user had {refund_count} refunds in last 30 days."
            return check_and_create_alert(
                db=db,
                alert_type="repeated_refunds",
                score=70.0,  # High
                description=desc,
                user_id=user_id,
            )
        return None

    @staticmethod
    def detect_suspicious_logins(db: Session, user_id: Optional[int] = None, ip_address: Optional[str] = None) -> Optional[FraudAlert]:
        """3. Suspicious Login Attempts: IPs or Users with 5+ failed logins in 10 minutes."""
        now = utcnow_naive()
        ten_minutes_ago = now - timedelta(minutes=10)

        if not user_id and not ip_address:
            return None

        query = db.query(AuditLog).filter(
            AuditLog.action == AuditAction.LOGIN_FAILED,
            AuditLog.created_at >= ten_minutes_ago,
        )

        if user_id:
            query_user = query.filter(
                or_(
                    AuditLog.actor_id == user_id,
                    AuditLog.entity_id == str(user_id)
                )
            )
            user_failed_count = query_user.count()
            if user_failed_count >= 5:
                desc = f"Suspicious Login Attempts: user account has {user_failed_count} failed login attempts in 10 mins."
                return check_and_create_alert(
                    db=db,
                    alert_type="suspicious_logins",
                    score=75.0,  # High
                    description=desc,
                    user_id=user_id,
                )

        if ip_address:
            query_ip = query.filter(AuditLog.ip_address == ip_address)
            ip_failed_count = query_ip.count()
            if ip_failed_count >= 5:
                desc = f"Suspicious Login Attempts: IP address {ip_address} has {ip_failed_count} failed login attempts in 10 mins."
                return check_and_create_alert(
                    db=db,
                    alert_type="suspicious_logins",
                    score=80.0,  # High/Critical
                    description=desc,
                    user_id=user_id,  # Associate with last tried user if known
                )
        return None

    @staticmethod
    def detect_abnormal_vendor(db: Session, vendor_id: int) -> Optional[FraudAlert]:
        """4. Abnormal Vendor Activity: Marking completions < 2 mins OR cancellation rate > 30%."""
        now = utcnow_naive()
        thirty_days_ago = now - timedelta(days=30)

        # 4a. Quick completions in last 7 days
        seven_days_ago = now - timedelta(days=7)
        quick_completions = (
            db.query(Order)
            .filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.PICKED,
                Order.actual_completion_minutes < 2,
                Order.actual_completion_minutes.isnot(None),
                Order.created_at >= seven_days_ago,
            )
            .count()
        )

        if quick_completions >= 3:
            desc = f"Abnormal Vendor Activity: vendor marked {quick_completions} orders as completed in < 2 mins."
            return check_and_create_alert(
                db=db,
                alert_type="abnormal_vendor",
                score=50.0,  # Medium
                description=desc,
                vendor_id=vendor_id,
            )

        # 4b. High cancellation rate (minimum 10 orders)
        total_orders = (
            db.query(Order)
            .filter(Order.vendor_id == vendor_id, Order.created_at >= thirty_days_ago)
            .count()
        )
        if total_orders >= 10:
            cancelled_orders = (
                db.query(Order)
                .filter(
                    Order.vendor_id == vendor_id,
                    Order.status == OrderStatus.CANCELLED,
                    Order.created_at >= thirty_days_ago,
                )
                .count()
            )
            cancellation_rate = cancelled_orders / total_orders
            if cancellation_rate > 0.30:
                desc = (
                    f"Abnormal Vendor Activity: high cancellation rate "
                    f"({cancellation_rate * 100:.1f}%) over last {total_orders} orders."
                )
                return check_and_create_alert(
                    db=db,
                    alert_type="abnormal_vendor",
                    score=60.0,  # High
                    description=desc,
                    vendor_id=vendor_id,
                )

        return None

    @staticmethod
    def detect_fake_accounts(db: Session, user_id: int) -> Optional[FraudAlert]:
        """5. Fake Accounts: Users sharing same IP OR sequential phone numbers."""
        now = utcnow_naive()
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.phone:
            return None

        # 5a. Check sequential/similar phones created within 24h of each other
        phone_digits = re.sub(r"\D", "", user.phone)
        if len(phone_digits) >= 10:
            raw_10 = phone_digits[-10:]
            prefix_8 = raw_10[:8]

            one_day_ago = now - timedelta(days=1)
            similar_users = (
                db.query(User)
                .filter(
                    User.created_at >= one_day_ago,
                    User.phone.like(f"%{prefix_8}%"),
                    User.id != user_id,
                )
                .all()
            )

            # If there are 3+ accounts matching prefix_8 created in 24 hours
            if len(similar_users) >= 2:
                desc = (
                    f"Fake Accounts: sequential phone pattern detected. "
                    f"{len(similar_users) + 1} accounts with prefix {prefix_8} registered in 24h."
                )
                return check_and_create_alert(
                    db=db,
                    alert_type="fake_account",
                    score=45.0,  # Medium
                    description=desc,
                    user_id=user_id,
                )

        # 5b. Check shared login IP across 3+ distinct users in 7 days
        # Get last IP of current user
        last_log = (
            db.query(AuditLog)
            .filter(
                AuditLog.action == AuditAction.LOGIN_SUCCESS,
                or_(
                    AuditLog.actor_id == user_id,
                    AuditLog.entity_id == str(user_id)
                )
            )
            .order_by(AuditLog.created_at.desc())
            .first()
        )

        if last_log and last_log.ip_address:
            ip = last_log.ip_address
            seven_days_ago = now - timedelta(days=7)

            distinct_users_count = (
                db.query(AuditLog.actor_id)
                .filter(
                    AuditLog.action == AuditAction.LOGIN_SUCCESS,
                    AuditLog.ip_address == ip,
                    AuditLog.created_at >= seven_days_ago,
                    AuditLog.actor_id.isnot(None),
                )
                .distinct()
                .count()
            )

            if distinct_users_count >= 3:
                desc = f"Fake Accounts: IP address {ip} shared by {distinct_users_count} different user accounts."
                return check_and_create_alert(
                    db=db,
                    alert_type="fake_account",
                    score=40.0,  # Medium
                    description=desc,
                    user_id=user_id,
                )

        return None

    @staticmethod
    def detect_coupon_abuse(db: Session, user_id: int) -> Optional[FraudAlert]:
        """6. Coupon Abuse: High velocity voucher redemptions (>=3 in 1 hour)."""
        now = utcnow_naive()
        one_hour_ago = now - timedelta(hours=1)

        redemptions = (
            db.query(VoucherRedemption)
            .filter(
                VoucherRedemption.user_id == user_id,
                VoucherRedemption.redeemed_at >= one_hour_ago,
            )
            .count()
        )

        if redemptions >= 3:
            desc = f"Coupon Abuse: user redeemed {redemptions} vouchers in 1 hour."
            return check_and_create_alert(
                db=db,
                alert_type="coupon_abuse",
                score=55.0,  # Medium
                description=desc,
                user_id=user_id,
            )
        return None

    @staticmethod
    def detect_reward_abuse(db: Session, user_id: int) -> Optional[FraudAlert]:
        """7. Reward Abuse: High points redemption velocity (>=5 in 24 hours)."""
        now = utcnow_naive()
        one_day_ago = now - timedelta(days=1)

        redemptions = (
            db.query(RewardRedemption)
            .filter(
                RewardRedemption.user_id == user_id,
                RewardRedemption.created_at >= one_day_ago,
            )
            .count()
        )

        if redemptions >= 5:
            desc = f"Reward Abuse: user made {redemptions} points redemptions in 24 hours."
            return check_and_create_alert(
                db=db,
                alert_type="reward_abuse",
                score=45.0,  # Medium
                description=desc,
                user_id=user_id,
            )
        return None

    @staticmethod
    def detect_payment_abuse(db: Session, user_id: int) -> Optional[FraudAlert]:
        """8. Payment Abuse: Repeated failed transactions (>=3 in 10 minutes)."""
        now = utcnow_naive()
        ten_minutes_ago = now - timedelta(minutes=10)

        failed_payments = (
            db.query(Payment)
            .join(Order, Payment.order_id == Order.id)
            .filter(
                Order.user_id == user_id,
                Payment.status == PaymentStatus.FAILED,
                Payment.created_at >= ten_minutes_ago,
            )
            .count()
        )

        if failed_payments >= 3:
            desc = f"Payment Abuse: user triggered {failed_payments} failed payments in 10 mins."
            return check_and_create_alert(
                db=db,
                alert_type="payment_abuse",
                score=50.0,  # Medium
                description=desc,
                user_id=user_id,
            )
        return None

    @classmethod
    def run_all_detectors_for_order(cls, db: Session, order: Order) -> List[FraudAlert]:
        """Runs the context detectors for a placed order."""
        alerts = []
        try:
            a = cls.detect_duplicate_orders(db, order)
            if a:
                alerts.append(a)

            a = cls.detect_coupon_abuse(db, order.user_id)
            if a:
                alerts.append(a)

            a = cls.detect_reward_abuse(db, order.user_id)
            if a:
                alerts.append(a)

            a = cls.detect_payment_abuse(db, order.user_id)
            if a:
                alerts.append(a)

            a = cls.detect_fake_accounts(db, order.user_id)
            if a:
                alerts.append(a)

            a = cls.detect_repeated_refunds(db, order.user_id)
            if a:
                alerts.append(a)

            a = cls.detect_abnormal_vendor(db, order.vendor_id)
            if a:
                alerts.append(a)

        except Exception as e:
            logger.exception("error_during_order_fraud_detect order_id=%s error=%s", order.id, str(e))
        return alerts

    @classmethod
    def calculate_user_fraud_score(cls, db: Session, user_id: int) -> float:
        """Calculate cumulative fraud score for user, capped at 100.0."""
        active_alerts = (
            db.query(FraudAlert)
            .filter(FraudAlert.user_id == user_id, FraudAlert.status == "pending")
            .all()
        )
        if not active_alerts:
            return 0.0
        return min(100.0, sum(a.score for a in active_alerts))

    @classmethod
    def run_full_system_scan(cls, db: Session) -> int:
        """Scan historical tables for recent suspicious activity and generate alerts."""
        alert_count = 0
        now = utcnow_naive()

        # Scan active users in past 30 days
        recent_users = (
            db.query(User.id)
            .filter(User.is_active == True)
            .all()
        )
        for row in recent_users:
            u_id = row[0]
            try:
                a1 = cls.detect_repeated_refunds(db, u_id)
                a2 = cls.detect_fake_accounts(db, u_id)
                a3 = cls.detect_coupon_abuse(db, u_id)
                a4 = cls.detect_reward_abuse(db, u_id)
                a5 = cls.detect_payment_abuse(db, u_id)
                a6 = cls.detect_suspicious_logins(db, user_id=u_id)

                for alert in (a1, a2, a3, a4, a5, a6):
                    if alert:
                        alert_count += 1
            except Exception as e:
                logger.error("error_scanning_user user_id=%s err=%s", u_id, str(e))

        # Scan active vendors
        active_vendors = (
            db.query(User.id)
            .filter(User.role == UserRole.VENDOR, User.is_active == True)
            .all()
        )
        for row in active_vendors:
            v_id = row[0]
            try:
                a_vendor = cls.detect_abnormal_vendor(db, v_id)
                if a_vendor:
                    alert_count += 1
            except Exception as e:
                logger.error("error_scanning_vendor vendor_id=%s err=%s", v_id, str(e))

        # Scan failed logins from IP addresses
        recent_failed_ips = (
            db.query(AuditLog.ip_address)
            .filter(
                AuditLog.action == AuditAction.LOGIN_FAILED,
                AuditLog.created_at >= now - timedelta(hours=1),
                AuditLog.ip_address.isnot(None),
            )
            .distinct()
            .all()
        )
        for row in recent_failed_ips:
            ip = row[0]
            try:
                a_ip = cls.detect_suspicious_logins(db, ip_address=ip)
                if a_ip:
                    alert_count += 1
            except Exception as e:
                logger.error("error_scanning_ip ip=%s err=%s", ip, str(e))

        db.commit()
        return alert_count
