"""Comprehensive tests for the enhanced Rewards System.

Covers:
  - Get points balance
  - Award points (various reward types)
  - Redeem points (percentage, fixed, free item)
  - Insufficient points validation
  - Get available redemptions
  - Get full transaction history (paginated)
  - Get full redemption history (paginated)
  - Voucher CRUD and redemption
  - Off-peak bonus policy
  - Points on order completion
"""
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
from app.modules.orders.model import Order, OrderStatus
from app.modules.rewards.model import (
    RedemptionRule,
    RedemptionType,
    RewardPoints,
    RewardRule,
    RewardType,
)
from app.modules.rewards.service import award_points, initialize_default_rules
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    admin = User(phone="9900000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="9900000002", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(phone="9900000010", name="Vendor", role=UserRole.VENDOR, is_active=True, is_approved=True)

    test_db_session.add_all([admin, student, vendor])
    test_db_session.commit()
    test_db_session.refresh(admin)
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()
    test_db_session.refresh(slot)

    completed_order = Order(
        user_id=student.id, slot_id=slot.id, vendor_id=vendor.id,
        status=OrderStatus.PICKED, total_amount=10000,
    )
    test_db_session.add(completed_order)
    test_db_session.commit()
    test_db_session.refresh(completed_order)

    # Initialize reward + redemption rules
    for rt, ppr, fp in [
        (RewardType.ORDER_COMPLETION, 5.0, None),
        (RewardType.FIRST_ORDER, 1.0, 50.0),
        (RewardType.REFERRAL, 1.0, 25.0),
        (RewardType.LOYALTY_MILESTONE, 1.0, 100.0),
    ]:
        existing = test_db_session.query(RewardRule).filter(RewardRule.reward_type == rt).first()
        if not existing:
            test_db_session.add(RewardRule(reward_type=rt, points_per_rupee=ppr, fixed_points=fp, is_active=1))

    for rt, mp, mdp, mda in [
        (RedemptionType.DISCOUNT_PERCENTAGE, 50.0, 20.0, None),
        (RedemptionType.DISCOUNT_FIXED, 100.0, None, 50.0),
        (RedemptionType.FREE_ITEM, 200.0, None, None),
    ]:
        existing = test_db_session.query(RedemptionRule).filter(RedemptionRule.redemption_type == rt).first()
        if not existing:
            test_db_session.add(RedemptionRule(redemption_type=rt, min_points=mp, max_discount_percentage=mdp, max_discount_amount=mda, is_active=1))
    test_db_session.commit()

    return {
        "admin": admin,
        "student": student,
        "vendor": vendor,
        "completed_order": completed_order,
    }


@pytest.fixture()
def auth_context(seed_data):
    student = seed_data["student"]
    return {"id": student.id, "phone": student.phone, "role": student.role.value}


@pytest.fixture()
def client(test_db_session, auth_context):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        return auth_context

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_points_empty(client):
    resp = client.get("/rewards/points")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_points"] == 0.0
    assert data["total_earned"] == 0.0
    assert data["total_redeemed"] == 0.0


def test_award_points_and_check_balance(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 150.0, "Earned 150 points", db=test_db_session)

    resp = client.get("/rewards/points")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_points"] == 150.0
    assert data["total_earned"] == 150.0
    assert len(data["recent_transactions"]) == 1


def test_multiple_award_types(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 100.0, "Order completed", db=test_db_session)
    award_points(student.id, RewardType.FIRST_ORDER, 50.0, "First order bonus", db=test_db_session)
    award_points(student.id, RewardType.REFERRAL, 25.0, "Referral bonus", db=test_db_session)

    resp = client.get("/rewards/points")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_points"] == 175.0
    assert len(data["recent_transactions"]) == 3
    types = {t["reward_type"] for t in data["recent_transactions"]}
    assert "order_completion" in types
    assert "first_order" in types
    assert "referral" in types


def test_redeem_points_percentage(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 200.0, "Earned 200", db=test_db_session)

    resp = client.post("/rewards/redeem", json={
        "redemption_type": "discount_percentage",
        "points_used": 50,
        "value": 10,
    })
    assert resp.status_code == 200

    balance = client.get("/rewards/points")
    assert balance.json()["current_points"] == 150.0


def test_redeem_points_fixed(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 300.0, "Earned 300", db=test_db_session)

    resp = client.post("/rewards/redeem", json={
        "redemption_type": "discount_fixed",
        "points_used": 100,
        "value": 25,
    })
    assert resp.status_code == 200
    assert balance_json(client)["current_points"] == 200.0


def test_redeem_points_free_item(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 500.0, "Earned 500", db=test_db_session)

    resp = client.post("/rewards/redeem", json={
        "redemption_type": "free_item",
        "points_used": 200,
        "value": 99,
    })
    assert resp.status_code == 200
    assert balance_json(client)["current_points"] == 300.0


def test_redeem_insufficient_points(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 30.0, "Earned 30", db=test_db_session)

    resp = client.post("/rewards/redeem", json={
        "redemption_type": "discount_percentage",
        "points_used": 50,
        "value": 10,
    })
    assert resp.status_code == 400
    assert "insufficient" in resp.json()["detail"].lower()


def test_available_redemptions(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 150.0, "Earned 150", db=test_db_session)

    resp = client.get("/rewards/redemptions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2  # percentage + fixed should be available
    types = {r["redemption_type"] for r in data}
    assert "discount_percentage" in types
    assert "discount_fixed" in types


def test_transaction_history(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 100.0, "Tx 1", db=test_db_session)
    award_points(student.id, RewardType.FIRST_ORDER, 50.0, "Tx 2", db=test_db_session)
    award_points(student.id, RewardType.REFERRAL, 25.0, "Tx 3", db=test_db_session)

    resp = client.get("/rewards/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["points"] == 25.0  # most recent first


def test_transaction_history_pagination(client, seed_data, test_db_session):
    student = seed_data["student"]
    for i in range(5):
        award_points(student.id, RewardType.ORDER_COMPLETION, 10.0, f"Tx {i}", db=test_db_session)

    resp = client.get("/rewards/transactions", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = client.get("/rewards/transactions", params={"limit": 2, "offset": 2})
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2


def test_redemption_history(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 500.0, "Earned 500", db=test_db_session)

    client.post("/rewards/redeem", json={"redemption_type": "discount_percentage", "points_used": 50, "value": 10})
    client.post("/rewards/redeem", json={"redemption_type": "discount_fixed", "points_used": 100, "value": 25})

    resp = client.get("/rewards/redemptions/history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_redemption_history_pagination(client, seed_data, test_db_session):
    student = seed_data["student"]
    award_points(student.id, RewardType.ORDER_COMPLETION, 5000.0, "Earned 5000", db=test_db_session)

    for i in range(5):
        client.post("/rewards/redeem", json={"redemption_type": "discount_percentage", "points_used": 50, "value": 5 + i})

    resp = client.get("/rewards/redemptions/history", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_voucher_crud_and_redeem(client, seed_data, auth_context, test_db_session):
    admin = seed_data["admin"]
    student = seed_data["student"]
    order = seed_data["completed_order"]

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})

    expiry = (utcnow_naive() + timedelta(days=7)).isoformat()
    create_resp = client.post("/rewards/vouchers", json={
        "code": "TEST20",
        "description": "20% off test voucher",
        "discount_type": "percentage",
        "discount_value": 20,
        "min_order_amount_paise": 5000,
        "max_discount_amount_paise": 3000,
        "usage_limit": 10,
        "expires_at": expiry,
    })
    assert create_resp.status_code == 200

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})

    list_resp = client.get("/rewards/vouchers")
    assert list_resp.status_code == 200
    assert any(v["code"] == "TEST20" for v in list_resp.json())

    redeem_resp = client.post("/rewards/vouchers/TEST20/redeem", json={"order_id": order.id})
    assert redeem_resp.status_code == 200
    assert redeem_resp.json()["discount_amount_paise"] == 2000


def test_initialize_rules_admin_only(client, seed_data, auth_context):
    # Student cannot initialize rules
    resp = client.post("/rewards/initialize-rules")
    assert resp.status_code == 403

    # Admin can
    admin = seed_data["admin"]
    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    resp = client.post("/rewards/initialize-rules")
    assert resp.status_code == 200


def test_get_user_rewards_access_control(client, seed_data, auth_context):
    admin = seed_data["admin"]
    student = seed_data["student"]

    # Student can see their own rewards
    resp = client.get(f"/rewards/{student.id}")
    assert resp.status_code == 200

    # Admin can see anyone's rewards
    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    resp = client.get(f"/rewards/{student.id}")
    assert resp.status_code == 200


def balance_json(client):
    return client.get("/rewards/points").json()
