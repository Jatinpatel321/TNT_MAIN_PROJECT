"""
QR pickup v2 — rotation, expiry, ownership, pickup-status, realtime event.

Covers the hardened pickup workflow:
  POST/GET /orders/{id}/qr          — owner-only, READY-only, rotating token
  POST     /orders/{id}/refresh-qr  — force-rotate, invalidates old token
  GET      /orders/{id}/pickup-status
  qr_service token signing + expiry (unit-level)
  publish_pickup_confirmed fires on scan
"""

from __future__ import annotations

import time
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
from app.modules.orders import qr_service
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed(db):
    student = User(phone="7200000001", name="Student", role=UserRole.STUDENT, is_active=True)
    other = User(phone="7200000002", name="Other", role=UserRole.STUDENT, is_active=True)
    vendor = User(phone="7200000010", name="Canteen", full_name="Canteen Stall",
                  role=UserRole.VENDOR, is_active=True, is_approved=True)
    db.add_all([student, other, vendor])
    db.commit()
    for u in (student, other, vendor):
        db.refresh(u)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    order = Order(
        user_id=student.id,
        vendor_id=vendor.id,
        slot_id=slot.id,
        status=OrderStatus.READY,
        total_amount=60,
        eta_minutes=5,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {"student": student, "other": other, "vendor": vendor, "slot": slot, "order": order}


@pytest.fixture()
def as_user(db):
    """Return a helper that binds the API client to a given user."""
    def _bind(user: User) -> TestClient:
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: {
            "id": user.id, "phone": user.phone, "role": user.role.value,
        }
        return TestClient(app, raise_server_exceptions=False)
    yield _bind
    app.dependency_overrides.clear()


# ── Token unit tests ─────────────────────────────────────────────────────────

class TestTokenSigningAndExpiry:
    def test_signed_token_roundtrips(self):
        token = qr_service._mint_token(42)
        assert qr_service._verify_qr_token(42, token) is True

    def test_wrong_order_id_rejected(self):
        token = qr_service._mint_token(42)
        assert qr_service._verify_qr_token(99, token) is False

    def test_tampered_token_rejected(self):
        token = qr_service._mint_token(42)
        raw, exp, sig = token.split(".")
        tampered = f"{raw}X.{exp}.{sig}"
        assert qr_service._verify_qr_token(42, tampered) is False

    def test_expired_token_rejected(self):
        raw = "abc123"
        past = int(time.time()) - 10
        token = qr_service._sign_qr_token(42, raw, past)
        assert qr_service._verify_qr_token(42, token) is False
        # ...but signature itself is valid when expiry is ignored
        assert qr_service._verify_qr_token(42, token, check_expiry=False) is True

    def test_legacy_two_part_token_still_verifies(self):
        # v1 format: raw.sig with no expiry segment
        import hashlib, hmac
        raw = "legacyraw"
        sig = hmac.new(qr_service._QR_SIGNING_KEY, f"42:{raw}".encode(), hashlib.sha256).hexdigest()[:16]
        legacy = f"{raw}.{sig}"
        assert qr_service._verify_qr_token(42, legacy) is True


# ── Generation: ownership + status gating ────────────────────────────────────

class TestQrGeneration:
    def test_owner_generates_qr_with_expiry_metadata(self, db, seed, as_user):
        client = as_user(seed["student"])
        res = client.post(f"/orders/{seed['order'].id}/qr")
        assert res.status_code == 200
        body = res.json()
        assert body["qr_code"].count(".") == 2
        assert body["expires_in_seconds"] > 0
        assert body["expires_at"] is not None

    def test_non_owner_cannot_generate(self, db, seed, as_user):
        client = as_user(seed["other"])
        res = client.post(f"/orders/{seed['order'].id}/qr")
        assert res.status_code == 404  # ownership masked as not-found

    def test_get_and_post_reuse_same_live_token(self, db, seed, as_user):
        client = as_user(seed["student"])
        first = client.post(f"/orders/{seed['order'].id}/qr").json()["qr_code"]
        second = client.get(f"/orders/{seed['order'].id}/qr").json()["qr_code"]
        assert first == second

    def test_qr_rejected_when_not_ready(self, db, seed, as_user):
        seed["order"].status = OrderStatus.PREPARING
        db.commit()
        client = as_user(seed["student"])
        res = client.post(f"/orders/{seed['order'].id}/qr")
        assert res.status_code == 400

    def test_qr_rejected_when_cancelled(self, db, seed, as_user):
        seed["order"].status = OrderStatus.CANCELLED
        db.commit()
        client = as_user(seed["student"])
        assert client.post(f"/orders/{seed['order'].id}/qr").status_code == 400


# ── Rotation ─────────────────────────────────────────────────────────────────

class TestQrRotation:
    def test_refresh_rotates_and_invalidates_old(self, db, seed, as_user):
        client = as_user(seed["student"])
        old = client.post(f"/orders/{seed['order'].id}/qr").json()["qr_code"]
        new = client.post(f"/orders/{seed['order'].id}/refresh-qr").json()["qr_code"]
        assert new != old
        # Old token is no longer stored on the order → cannot be confirmed
        assert qr_service.get_order_by_qr(old, db) is None
        assert qr_service.get_order_by_qr(new, db).id == seed["order"].id


# ── Pickup status ────────────────────────────────────────────────────────────

class TestPickupStatus:
    def test_status_shape_for_ready_order(self, db, seed, as_user):
        client = as_user(seed["student"])
        client.post(f"/orders/{seed['order'].id}/qr")  # make QR live
        res = client.get(f"/orders/{seed['order'].id}/pickup-status")
        assert res.status_code == 200
        body = res.json()
        assert body["is_ready_for_pickup"] is True
        assert body["vendor_name"] == "Canteen Stall"
        assert body["slot"]["start_time"] is not None
        assert body["eta_minutes"] == 5
        assert body["qr_available"] is True
        assert body["qr_expires_in_seconds"] > 0

    def test_status_non_owner_404(self, db, seed, as_user):
        client = as_user(seed["other"])
        assert client.get(f"/orders/{seed['order'].id}/pickup-status").status_code == 404

    def test_status_not_ready_hides_qr(self, db, seed, as_user):
        seed["order"].status = OrderStatus.PREPARING
        db.commit()
        client = as_user(seed["student"])
        body = client.get(f"/orders/{seed['order'].id}/pickup-status").json()
        assert body["is_ready_for_pickup"] is False
        assert body["qr_available"] is False
        assert body["can_generate_qr"] is False


# ── Realtime event on scan ───────────────────────────────────────────────────

class TestPickupRealtimeEvent:
    def test_confirm_publishes_pickup_event(self, db, seed, monkeypatch):
        events = []
        monkeypatch.setattr(
            "app.core.order_events.publish_pickup_confirmed",
            lambda order_id, vendor_id: events.append((order_id, vendor_id)) or True,
        )
        token = qr_service.generate_qr_code(seed["order"].id, db)
        ok = qr_service.confirm_pickup(token, seed["vendor"].id, db)
        assert ok is True
        db.refresh(seed["order"])
        assert seed["order"].status == OrderStatus.PICKED
        assert events == [(seed["order"].id, seed["vendor"].id)]

    def test_expired_token_cannot_confirm(self, db, seed):
        raw = "expiredraw"
        past = int(time.time()) - 5
        token = qr_service._sign_qr_token(seed["order"].id, raw, past)
        seed["order"].qr_code = token
        db.commit()
        assert qr_service.confirm_pickup(token, seed["vendor"].id, db) is False
        db.refresh(seed["order"])
        assert seed["order"].status == OrderStatus.READY  # unchanged
