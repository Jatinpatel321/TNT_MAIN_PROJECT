"""
Profile stats & account lifecycle — test_profile_stats.py

Covers:
  GET    /profile/stats — aggregated order/spend/rewards statistics
  DELETE /profile/me    — soft account deactivation
  PUT    /profile/update — new identity fields (email, campus, residence,
                           dietary preference)
"""

from __future__ import annotations

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
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.rewards.model import (
    RedemptionType,
    RewardPoints,
    RewardRedemption,
    Voucher,
    VoucherDiscountType,
    VoucherRedemption,
)
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _auth_for(user):
    return lambda: {"id": user.id, "phone": user.phone, "role": user.role.value, "is_active": True}


def _make_client(db_session, user):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = _auth_for(user)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=eng)
        eng.dispose()


@pytest.fixture()
def student(db):
    u = User(phone="9600000201", name="Stats Student", role=UserRole.STUDENT, is_active=True)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture()
def seeded_orders(db, student):
    """Two food orders (one cancelled), one stationery, one group order."""
    owner = User(phone="9600000202", role=UserRole.VENDOR, is_active=True, is_approved=True)
    db.add(owner)
    db.commit()
    db.refresh(owner)

    start = utcnow_naive() + timedelta(hours=1)
    slot = Slot(
        vendor_id=owner.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        max_orders=50,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    def _order(status, booking_type="food", group_id=None, amount=100):
        o = Order(
            user_id=student.id,
            vendor_id=owner.id,
            slot_id=slot.id,
            status=status,
            booking_type=booking_type,
            group_id=group_id,
            total_amount=amount,
        )
        db.add(o)
        db.commit()
        db.refresh(o)
        return o

    food = _order(OrderStatus.PICKED, "food", amount=150)
    cancelled = _order(OrderStatus.CANCELLED, "food", amount=80)
    stationery = _order(OrderStatus.PICKED, "stationery", amount=40)

    # Successful payment for the food order; failed one must not count.
    db.add(Payment(order_id=food.id, amount=150, status=PaymentStatus.SUCCESS))
    db.add(Payment(order_id=stationery.id, amount=40, status=PaymentStatus.FAILED))
    db.commit()

    return {"food": food, "cancelled": cancelled, "stationery": stationery, "owner": owner, "slot": slot}


class TestProfileStats:
    def test_empty_stats_for_new_user(self, db, student):
        client = _make_client(db, student)
        res = client.get("/profile/stats")
        assert res.status_code == 200
        body = res.json()
        assert body["total_orders"] == 0
        assert body["total_spent"] == 0
        assert body["loyalty_points"] == 0
        assert body["saved_via_offers"] == 0
        assert body["member_since"] is not None

    def test_counts_exclude_cancelled_and_split_by_type(self, db, student, seeded_orders):
        client = _make_client(db, student)
        body = client.get("/profile/stats").json()
        assert body["total_orders"] == 2  # cancelled excluded
        assert body["food_orders"] == 1
        assert body["stationery_orders"] == 1
        assert body["group_orders"] == 0

    def test_spend_counts_only_successful_payments(self, db, student, seeded_orders):
        client = _make_client(db, student)
        body = client.get("/profile/stats").json()
        assert body["total_spent"] == 150.0  # FAILED payment excluded

    def test_rewards_and_savings(self, db, student, seeded_orders):
        db.add(RewardPoints(user_id=student.id, points=42.5, total_earned=120.0, total_redeemed=77.5))
        admin = User(phone="9600000203", role=UserRole.ADMIN, is_active=True)
        db.add(admin)
        db.commit()
        voucher = Voucher(
            code="SAVE20",
            description="test",
            discount_type=VoucherDiscountType.FIXED,
            discount_value=20.0,
            expires_at=utcnow_naive() + timedelta(days=1),
            created_by_user_id=admin.id,
        )
        db.add(voucher)
        db.commit()
        db.add(
            VoucherRedemption(
                voucher_id=voucher.id,
                user_id=student.id,
                order_id=seeded_orders["food"].id,
                discount_amount=20,
            )
        )
        db.add(
            RewardRedemption(
                user_id=student.id,
                redemption_type=RedemptionType.DISCOUNT_FIXED,
                points_used=50,
                value=10.0,
                description="points discount",
            )
        )
        db.commit()

        client = _make_client(db, student)
        body = client.get("/profile/stats").json()
        assert body["loyalty_points"] == 42.5
        assert body["rewards_earned"] == 120.0
        assert body["saved_via_offers"] == 30.0

    def test_stats_requires_auth(self, db):
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app, raise_server_exceptions=False)
        assert client.get("/profile/stats").status_code in (401, 403)


class TestProfileIdentityFields:
    def test_update_new_identity_fields(self, db, student):
        client = _make_client(db, student)
        res = client.put(
            "/profile/update",
            json={
                "email": "student@univ.edu",
                "campus": "North Campus",
                "residence_type": "hostel",
                "dietary_preference": "vegetarian",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["email"] == "student@univ.edu"
        assert body["campus"] == "North Campus"
        assert body["residence_type"] == "hostel"
        assert body["dietary_preference"] == "vegetarian"

    def test_invalid_email_rejected(self, db, student):
        client = _make_client(db, student)
        res = client.put("/profile/update", json={"email": "not-an-email"})
        assert res.status_code == 422

    def test_invalid_dietary_preference_rejected(self, db, student):
        client = _make_client(db, student)
        res = client.put("/profile/update", json={"dietary_preference": "carnivore"})
        assert res.status_code == 422


class TestDeleteAccount:
    def test_delete_deactivates_account(self, db, student):
        client = _make_client(db, student)
        res = client.delete("/profile/me")
        assert res.status_code == 200
        db.refresh(student)
        assert student.is_active is False
        assert student.device_token is None
        assert student.push_enabled is False

    def test_order_history_retained_after_delete(self, db, student, seeded_orders):
        client = _make_client(db, student)
        client.delete("/profile/me")
        remaining = db.query(Order).filter(Order.user_id == student.id).count()
        assert remaining == 3
