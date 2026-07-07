"""
Full Order Lifecycle E2E — ONLINE-ONLY money chain.

The platform is online-prepaid only (no cash payment / cash order feature), so
this drives the complete Workflow 2 through the real API using an ONLINE
payment and asserts the money propagates into vendor settlement AND admin
analytics:

  add-to-cart → checkout → ONLINE payment (SUCCESS) → vendor prepare/ready
      → QR pickup (PICKED) → settlement online revenue ↑ → admin analytics ↑

Uses unique per-run phone numbers so it is deterministic against the shared DB.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.main import app
from app.modules.menu.model import Inventory, MenuItem
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

_SUFFIX = str(int(time.time()))[-8:]
STUDENT_PHONE = "91" + _SUFFIX
VENDOR_PHONE = "92" + _SUFFIX
ADMIN_PHONE = "93" + _SUFFIX


def _auth(user: User) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "phone": user.phone, "role": user.role.value},
        expires_delta=60,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client():
    c = TestClient(app, raise_server_exceptions=True)
    c.__enter__()
    try:
        yield c
    finally:
        try:
            c.__exit__(None, None, None)
        except BaseException:
            pass


@pytest.fixture(scope="module")
def seed(db):
    vendor = User(phone=VENDOR_PHONE, name="E2E Cafe", role=UserRole.VENDOR,
                  vendor_type="food", is_approved=True, is_active=True)
    student = User(phone=STUDENT_PHONE, name="E2E Student", role=UserRole.STUDENT, is_active=True)
    admin = User(phone=ADMIN_PHONE, name="E2E Admin", role=UserRole.ADMIN, is_active=True)
    db.add_all([vendor, student, admin])
    db.commit()
    for u in (vendor, student, admin):
        db.refresh(u)

    item = MenuItem(vendor_id=vendor.id, name="E2E Burger", description="test",
                    price=80, is_available=True, available_quantity=100)  # rupees
    db.add(item)
    db.commit()
    db.refresh(item)
    db.add(Inventory(menu_item_id=item.id, current_stock=100, low_stock_threshold=5))

    now = datetime.utcnow()
    slot = Slot(vendor_id=vendor.id, start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=2), max_orders=10, current_orders=0)
    db.add(slot)
    db.commit()
    db.refresh(slot)

    created = {"vendor": vendor, "student": student, "admin": admin, "item": item, "slot": slot}
    yield created

    # ── best-effort cleanup ──
    try:
        order_ids = [o.id for o in db.query(Order).filter(Order.vendor_id == vendor.id).all()]
        if order_ids:
            db.query(Payment).filter(Payment.order_id.in_(order_ids)).delete(synchronize_session=False)
            db.query(Order).filter(Order.id.in_(order_ids)).delete(synchronize_session=False)
        db.query(Inventory).filter(Inventory.menu_item_id == item.id).delete(synchronize_session=False)
        db.query(MenuItem).filter(MenuItem.vendor_id == vendor.id).delete(synchronize_session=False)
        db.query(Slot).filter(Slot.vendor_id == vendor.id).delete(synchronize_session=False)
        db.query(User).filter(User.id.in_([vendor.id, student.id, admin.id])).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()


def _online_revenue(client, vendor) -> float:
    res = client.get("/v1/vendors/settlement/revenue", headers=_auth(vendor))
    assert res.status_code == 200, res.text
    return float(res.json()["today"]["online_payments"])


def _admin_revenue_paise(client, admin) -> int:
    res = client.get("/v1/admin/analytics", headers=_auth(admin))
    assert res.status_code == 200, res.text
    body = res.json()
    # totals.revenue_paise = sum of all SUCCESS (online) payments
    return int(body.get("totals", {}).get("revenue_paise", 0))


def _invalidate_analytics_cache() -> None:
    """Admin analytics is cached (ttl=300) and admin mutations don't bust it,
    so force a recompute to observe the new payment within the test."""
    import asyncio

    from app.core.redis_cache import cache_service

    asyncio.run(cache_service.delete("analytics", "admin_general_analytics"))


def test_full_online_order_lifecycle(client, db, seed):
    vendor, student, admin = seed["vendor"], seed["student"], seed["admin"]
    item, slot = seed["item"], seed["slot"]

    settle_before = _online_revenue(client, vendor)
    admin_before = _admin_revenue_paise(client, admin)

    # 1. add to cart (2 × ₹80 = ₹160)
    res = client.post("/cart/add", json={"menu_item_id": item.id, "quantity": 2}, headers=_auth(student))
    assert res.status_code == 200, res.text
    assert float(res.json()["total_amount"]) == 160.0

    # 2. checkout → order
    res = client.post("/cart/checkout", json={"slot_id": slot.id, "payment_method": "UPI"}, headers=_auth(student))
    assert res.status_code in (200, 201), res.text
    order_id = res.json()["order_id"]

    # 3. ONLINE payment → SUCCESS (also flips order to CONFIRMED)
    res = client.post("/payments/mock", json={"order_id": order_id, "method": "UPI"}, headers=_auth(student))
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "SUCCESS"

    pay = db.query(Payment).filter(Payment.order_id == order_id).order_by(Payment.id.desc()).first()
    db.refresh(pay)
    assert pay.status == PaymentStatus.SUCCESS
    amount_rupees = float(pay.amount)
    assert amount_rupees == 160.0

    # 4. vendor prepares → ready
    assert client.post(f"/orders/{order_id}/preparing", headers=_auth(vendor)).status_code == 200
    assert client.post(f"/orders/{order_id}/ready", headers=_auth(vendor)).status_code == 200

    # 5. student generates QR (order is READY)
    res = client.post(f"/orders/{order_id}/qr", headers=_auth(student))
    assert res.status_code == 200, res.text
    qr_code = res.json()["qr_code"]
    assert qr_code

    # 6. vendor confirms pickup → PICKED
    res = client.post("/orders/qr/pickup/confirm", params={"qr_code": qr_code}, headers=_auth(vendor))
    assert res.status_code == 200, res.text

    db.expire_all()
    order = db.query(Order).filter(Order.id == order_id).first()
    assert order.status == OrderStatus.PICKED, f"order status = {order.status}"

    # 7. cross-module propagation: settlement online revenue ↑ by ₹160
    settle_after = _online_revenue(client, vendor)
    assert round(settle_after - settle_before, 2) == 160.00, \
        f"settlement online delta {settle_after - settle_before} != 160.00"

    # 8. cross-module propagation: admin analytics revenue ↑ by the order amount.
    #    Admin analytics is cached (ttl=300) and mutations don't bust it, so we
    #    force a recompute to observe the new online payment.
    _invalidate_analytics_cache()
    admin_after = _admin_revenue_paise(client, admin)
    assert admin_after - admin_before == amount_rupees, \
        f"admin revenue delta {admin_after - admin_before} != {amount_rupees}"
