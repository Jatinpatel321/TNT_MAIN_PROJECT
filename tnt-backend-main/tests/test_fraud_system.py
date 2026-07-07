from datetime import UTC, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.fraud.model import FraudAlert
from app.modules.fraud.fraud_detection_service import FraudDetectionService, get_severity_level
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.rewards.model import RewardRedemption, VoucherRedemption, Voucher, VoucherDiscountType, RedemptionType
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.auditlog.model import AuditLog
from app.modules.auditlog.service import AuditAction, AuditCategory


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed(db_session):
    admin = User(
        phone="9300000001", name="Admin", role=UserRole.ADMIN, is_active=True
    )
    student = User(
        phone="9300000002", name="Student", role=UserRole.STUDENT, is_active=True
    )
    vendor_owner = User(
        phone="9300000003",
        name="VendorOwner",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    db_session.add_all([admin, student, vendor_owner])
    db_session.commit()
    for u in (admin, student, vendor_owner):
        db_session.refresh(u)

    vendor_biz = Vendor(
        vendor_name="Hot Samosas",
        category="food",
        owner_id=vendor_owner.id,
        password_hash="hashedpass",
        status=VendorStatus.ACTIVE,
    )
    db_session.add(vendor_biz)
    db_session.commit()
    db_session.refresh(vendor_biz)

    slot = Slot(
        vendor_id=vendor_owner.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)

    order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor_owner.id,
        status=OrderStatus.PLACED,
        total_amount=5000,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    return {
        "admin": admin,
        "student": student,
        "vendor_owner": vendor_owner,
        "vendor_biz": vendor_biz,
        "order": order,
        "slot": slot,
    }


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=True)


# ── Model Tests ──────────────────────────────────────────────────────────────

def test_fraud_alert_model(db_session):
    alert = FraudAlert(
        alert_type="duplicate_orders",
        severity="critical",
        score=90.0,
        description="Duplicate",
        status="pending",
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    assert alert.id is not None
    assert alert.status == "pending"


# ── Service Detectors Tests ──────────────────────────────────────────────────

def test_detect_duplicate_orders(db_session, seed):
    order1 = seed["order"]
    # Place a duplicate order
    order2 = Order(
        user_id=order1.user_id,
        slot_id=order1.slot_id,
        vendor_id=order1.vendor_id,
        status=OrderStatus.PLACED,
        total_amount=order1.total_amount,
        created_at=utcnow_naive() - timedelta(seconds=10),
    )
    db_session.add(order2)
    db_session.commit()

    alert = FraudDetectionService.detect_duplicate_orders(db_session, order2)
    assert alert is not None
    assert alert.alert_type == "duplicate_orders"
    assert alert.score == 90.0
    assert alert.severity == "critical"


def test_detect_repeated_refunds(db_session, seed):
    student = seed["student"]
    # Add 3 refunded payments in past 30 days
    for i in range(3):
        ord_temp = Order(
            user_id=student.id,
            slot_id=seed["slot"].id,
            vendor_id=seed["vendor_owner"].id,
            status=OrderStatus.PICKED,
            total_amount=1000,
        )
        db_session.add(ord_temp)
        db_session.commit()
        pmt = Payment(
            order_id=ord_temp.id,
            amount=1000,
            status=PaymentStatus.REFUNDED,
            created_at=utcnow_naive() - timedelta(days=2),
        )
        db_session.add(pmt)
    db_session.commit()

    alert = FraudDetectionService.detect_repeated_refunds(db_session, student.id)
    assert alert is not None
    assert alert.alert_type == "repeated_refunds"
    assert alert.severity == "high"


def test_detect_suspicious_logins(db_session, seed):
    # Add 5 failed logins for an IP
    ip = "192.168.1.50"
    for _ in range(5):
        log = AuditLog(
            action=AuditAction.LOGIN_FAILED,
            action_category=AuditCategory.AUTH,
            ip_address=ip,
            created_at=utcnow_naive() - timedelta(minutes=1),
        )
        db_session.add(log)
    db_session.commit()

    alert = FraudDetectionService.detect_suspicious_logins(db_session, ip_address=ip)
    assert alert is not None
    assert alert.alert_type == "suspicious_logins"
    assert alert.score == 80.0


def test_detect_abnormal_vendor(db_session, seed):
    vendor = seed["vendor_owner"]
    # completions under 2 minutes
    for _ in range(3):
        ord_temp = Order(
            user_id=seed["student"].id,
            slot_id=seed["slot"].id,
            vendor_id=vendor.id,
            status=OrderStatus.PICKED,
            total_amount=500,
            actual_completion_minutes=1,
            created_at=utcnow_naive() - timedelta(days=1),
        )
        db_session.add(ord_temp)
    db_session.commit()

    alert = FraudDetectionService.detect_abnormal_vendor(db_session, vendor.id)
    assert alert is not None
    assert alert.alert_type == "abnormal_vendor"
    assert alert.severity == "medium"


def test_detect_fake_accounts_sequential_phones(db_session, seed):
    student = seed["student"]  # phone is "9300000002"
    # Create sequential accounts created within 24h
    user2 = User(
        phone="9300000008",
        role=UserRole.STUDENT,
        created_at=utcnow_naive() - timedelta(hours=2),
    )
    user3 = User(
        phone="9300000009",
        role=UserRole.STUDENT,
        created_at=utcnow_naive() - timedelta(hours=3),
    )
    db_session.add_all([user2, user3])
    db_session.commit()

    alert = FraudDetectionService.detect_fake_accounts(db_session, student.id)
    assert alert is not None
    assert alert.alert_type == "fake_account"
    assert "sequential phone pattern" in alert.description


def test_detect_coupon_abuse(db_session, seed):
    student = seed["student"]
    # 3 redemptions within an hour
    v = Voucher(
        code="FREE50",
        description="free",
        discount_type=VoucherDiscountType.FIXED,
        discount_value=50.0,
        expires_at=utcnow_naive() + timedelta(days=2),
        created_by_user_id=seed["admin"].id,
    )
    db_session.add(v)
    db_session.commit()

    for i in range(3):
        red = VoucherRedemption(
            voucher_id=v.id,
            user_id=student.id,
            order_id=seed["order"].id,
            discount_amount_paise=5000,
            redeemed_at=utcnow_naive() - timedelta(minutes=5),
        )
        db_session.add(red)
    db_session.commit()

    alert = FraudDetectionService.detect_coupon_abuse(db_session, student.id)
    assert alert is not None
    assert alert.alert_type == "coupon_abuse"


def test_detect_reward_abuse(db_session, seed):
    student = seed["student"]
    # 5 point redemptions in 24 hours
    for _ in range(5):
        red = RewardRedemption(
            user_id=student.id,
            redemption_type=RedemptionType.DISCOUNT_FIXED,
            points_used=100.0,
            value=10.0,
            description="points redemption",
            created_at=utcnow_naive() - timedelta(hours=2),
        )
        db_session.add(red)
    db_session.commit()

    alert = FraudDetectionService.detect_reward_abuse(db_session, student.id)
    assert alert is not None
    assert alert.alert_type == "reward_abuse"


def test_detect_payment_abuse(db_session, seed):
    student = seed["student"]
    # 3 failed payments in 10 minutes
    for _ in range(3):
        ord_temp = Order(
            user_id=student.id,
            slot_id=seed["slot"].id,
            vendor_id=seed["vendor_owner"].id,
            status=OrderStatus.PLACED,
            total_amount=1000,
        )
        db_session.add(ord_temp)
        db_session.commit()
        pmt = Payment(
            order_id=ord_temp.id,
            amount=1000,
            status=PaymentStatus.FAILED,
            created_at=utcnow_naive() - timedelta(minutes=2),
        )
        db_session.add(pmt)
    db_session.commit()

    alert = FraudDetectionService.detect_payment_abuse(db_session, student.id)
    assert alert is not None
    assert alert.alert_type == "payment_abuse"


# ── Route API Tests ──────────────────────────────────────────────────────────

def test_api_list_alerts(db_session, seed):
    # Add an alert
    alert = FraudAlert(
        user_id=seed["student"].id,
        alert_type="coupon_abuse",
        severity="medium",
        score=55.0,
        description="Coupon abuse description",
        status="pending",
    )
    db_session.add(alert)
    db_session.commit()

    client = _make_client(db_session, seed["admin"])
    res = client.get("/v1/admin/fraud/alerts")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert data["alerts"][0]["alert_type"] == "coupon_abuse"


def test_api_resolve_and_false_positive(db_session, seed):
    alert = FraudAlert(
        user_id=seed["student"].id,
        alert_type="payment_abuse",
        severity="medium",
        score=50.0,
        status="pending",
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    client = _make_client(db_session, seed["admin"])
    # Resolve alert
    res1 = client.post(
        f"/v1/admin/fraud/alerts/{alert.id}/resolve",
        json={"notes": "Legitimate transaction issues"}
    )
    assert res1.status_code == 200
    db_session.refresh(alert)
    assert alert.status == "resolved"
    assert alert.resolution_notes == "Legitimate transaction issues"

    # Mark false positive
    res2 = client.post(
        f"/v1/admin/fraud/alerts/{alert.id}/false-positive",
        json={"notes": "System misfire"}
    )
    assert res2.status_code == 200
    db_session.refresh(alert)
    assert alert.status == "false_positive"
    assert alert.resolution_notes == "System misfire"


def test_api_blacklist_user(db_session, seed):
    student = seed["student"]
    assert student.is_active is True

    client = _make_client(db_session, seed["admin"])
    res = client.post(f"/v1/admin/fraud/users/{student.id}/blacklist")
    assert res.status_code == 200
    db_session.refresh(student)
    assert student.is_active is False


def test_api_blacklist_vendor(db_session, seed):
    vendor_owner = seed["vendor_owner"]
    vendor_biz = seed["vendor_biz"]
    assert vendor_owner.is_active is True
    assert vendor_biz.status == VendorStatus.ACTIVE

    client = _make_client(db_session, seed["admin"])
    res = client.post(f"/v1/admin/fraud/vendors/{vendor_owner.id}/blacklist")
    assert res.status_code == 200
    db_session.refresh(vendor_owner)
    db_session.refresh(vendor_biz)
    assert vendor_owner.is_active is False
    assert vendor_biz.status == VendorStatus.SUSPENDED


def test_api_fraud_metrics(db_session, seed):
    alert = FraudAlert(
        user_id=seed["student"].id,
        alert_type="reward_abuse",
        severity="medium",
        score=45.0,
        status="pending",
    )
    db_session.add(alert)
    db_session.commit()

    client = _make_client(db_session, seed["admin"])
    res = client.get("/v1/admin/fraud/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert data["summary"]["pending_alerts"] >= 1
    assert data["severity_distribution"]["medium"] >= 1
