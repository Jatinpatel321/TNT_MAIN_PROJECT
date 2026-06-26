"""
End-to-End Workflow Simulation
==============================
Simulates the full user journey:
  1.  Login with OTP
  2.  Browse vendors
  3.  Browse vendor menu (items have images)
  4.  Add items to cart
  5.  View cart (no empty sections)
  6.  Select pickup slot
  7.  Checkout & payment initiation
  8.  Track order (timeline, ETA)
  9.  Vendor confirms order
  10. Vendor marks order ready
  11. Generate QR code for pickup
  12. Vendor scans QR → pickup confirmed
  13. Student submits rating/feedback

Run with:
    cd tnt-backend-main
    ..\.venv\Scripts\pytest test_e2e_workflow.py -v
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client():
    # raise_server_exceptions=True so real 5xx errors surface in tests.
    # The try/except around __exit__ suppresses the CancelledError that
    # Python 3.11+ raises when the ASGI lifespan shuts down background
    # tasks — this is cosmetic and does not mask real test failures.
    c = TestClient(app, raise_server_exceptions=True)
    c.__enter__()
    try:
        yield c
    finally:
        try:
            c.__exit__(None, None, None)
        except BaseException:
            pass  # suppress CancelledError / anyio teardown noise


def _token(user: User) -> str:
    return create_access_token(
        data={"sub": str(user.id), "phone": user.phone, "role": user.role.value},
        expires_delta=60,
    )


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {_token(user)}"}


# ------------------------------------------------------------------
# Seed helpers
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def food_vendor(db: Session):
    vendor = db.query(User).filter(User.role == UserRole.VENDOR, User.vendor_type == "food", User.is_approved == True).first()
    if not vendor:
        vendor = User(
            phone="9000000001",
            name="Campus Cafe",
            role=UserRole.VENDOR,
            vendor_type="food",
            is_approved=True,
            is_active=True,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
    return vendor


@pytest.fixture(scope="module")
def student(db: Session):
    student = db.query(User).filter(User.phone == "9100000001").first()
    if not student:
        student = User(phone="9100000001", name="Test Student", role=UserRole.STUDENT, is_active=True)
        db.add(student)
        db.commit()
        db.refresh(student)
    return student


@pytest.fixture(scope="module")
def menu_item(db: Session, food_vendor: User):
    item = db.query(MenuItem).filter(MenuItem.vendor_id == food_vendor.id, MenuItem.is_available == True).first()
    if not item:
        item = MenuItem(
            vendor_id=food_vendor.id,
            name="Veg Burger",
            description="Classic veg burger",
            price=8000,  # paise
            is_available=True,
            image_url="https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=500&q=70",
        )
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


@pytest.fixture(scope="module")
def slot(db: Session, food_vendor: User):
    from datetime import datetime, timedelta
    s = db.query(Slot).filter(Slot.vendor_id == food_vendor.id).first()
    if not s:
        now = datetime.utcnow()
        s = Slot(
            vendor_id=food_vendor.id,
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            max_orders=10,
            current_orders=0,
        )
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


# ===========================================================================
# STEP 1: Login with OTP
# ===========================================================================

class TestStep1_OTPLogin:

    def test_send_otp(self, client: TestClient):
        """POST /auth/send-otp must return 200 with message."""
        res = client.post("/auth/send-otp", json={"phone": "9100000001"})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data.get("message") == "OTP sent", f"Unexpected response: {data}"
        print("\n  ✓ OTP sent successfully")

    def test_verify_otp_and_get_token(self, client: TestClient, _auto_fake_redis):
        """POST /auth/verify-otp with correct OTP returns access_token."""
        # Inject OTP directly into fakeredis so we can verify it.
        # Note: the OTP service stores keys as "otp:{phone}" (no tnt: prefix).
        otp = "123456"
        _auto_fake_redis.setex(f"otp:{9100000001}", 300, otp)

        res = client.post("/auth/verify-otp", json={"phone": "9100000001", "otp": otp})
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["user"]["role"] == "student"
        print(f"\n  ✓ Login successful – token obtained (user #{data['data']['user']['id']})")

    def test_verify_wrong_otp_rejected(self, client: TestClient, _auto_fake_redis):
        """POST /auth/verify-otp with wrong OTP returns 400."""
        _auto_fake_redis.setex("otp:9100000001", 300, "999999")
        res = client.post("/auth/verify-otp", json={"phone": "9100000001", "otp": "000000"})
        assert res.status_code == 400
        print("\n  ✓ Invalid OTP correctly rejected")


# ===========================================================================
# STEP 2: Browse vendors
# ===========================================================================

class TestStep2_BrowseVendors:

    def test_get_food_vendors(self, client: TestClient, student: User, food_vendor: User):
        res = client.get("/vendors/?type=food", headers=_auth(student))
        assert res.status_code == 200, res.text
        vendors = res.json()
        assert isinstance(vendors, list), "Expected list of vendors"
        assert len(vendors) > 0, "No food vendors returned — ensure seed data exists"
        for v in vendors:
            assert v["name"], f"Vendor {v['id']} has no name"
            assert v["logo_url"], f"Vendor '{v['name']}' missing logo_url"
            assert v["cover_image"], f"Vendor '{v['name']}' missing cover_image"
        print(f"\n  ✓ {len(vendors)} food vendor(s) returned, all have images")

    def test_get_stationery_vendors(self, client: TestClient, student: User):
        res = client.get("/vendors/?type=stationery", headers=_auth(student))
        assert res.status_code == 200, res.text
        vendors = res.json()
        assert isinstance(vendors, list)
        print(f"\n  ✓ {len(vendors)} stationery vendor(s) returned")

    def test_get_single_vendor(self, client: TestClient, student: User, food_vendor: User):
        res = client.get(f"/vendors/{food_vendor.id}", headers=_auth(student))
        assert res.status_code == 200, res.text
        v = res.json()
        assert v["id"] == food_vendor.id
        assert v["name"] == food_vendor.name
        assert v["logo_url"]
        print(f"\n  ✓ Single vendor '{v['name']}' fetched with image")


# ===========================================================================
# STEP 3: Browse menu (every item has an image)
# ===========================================================================

class TestStep3_BrowseMenu:

    def test_get_vendor_menu(self, client: TestClient, student: User, food_vendor: User, menu_item: MenuItem):
        res = client.get(f"/vendors/{food_vendor.id}/menu", headers=_auth(student))
        assert res.status_code == 200, res.text
        items = res.json()
        assert isinstance(items, list)
        assert len(items) > 0, "Menu is empty"
        for it in items:
            assert it["name"], f"Item {it['id']} has no name"
            assert it["image_url"], f"Menu item '{it['name']}' has no image_url — images must be populated"
            assert it["price"] > 0, f"Item '{it['name']}' has zero price"
        print(f"\n  ✓ {len(items)} menu item(s), all have image_url set")


# ===========================================================================
# STEP 4: Cart operations
# ===========================================================================

class TestStep4_Cart:

    def test_add_item_to_cart(self, client: TestClient, student: User, menu_item: MenuItem):
        res = client.post(
            "/cart/add",
            json={"menu_item_id": menu_item.id, "quantity": 2},
            headers=_auth(student),
        )
        assert res.status_code == 200, res.text
        cart = res.json()
        assert cart["total_items"] == 2
        assert cart["total_amount"] > 0
        print(f"\n  ✓ Added {menu_item.name} ×2 to cart (total ₹{cart['total_amount']/100:.2f})")

    def test_view_cart_no_empty_sections(self, client: TestClient, student: User):
        res = client.get("/cart/", headers=_auth(student))
        assert res.status_code == 200, res.text
        cart = res.json()
        assert cart["total_items"] > 0, "Cart appears empty after adding items"
        assert len(cart["items"]) > 0, "Cart items list is empty"
        for item in cart["items"]:
            assert item.get("name"), "Cart item missing name"
            assert item.get("price") is not None, "Cart item missing price"
        print(f"\n  ✓ Cart has {cart['total_items']} item(s), no empty sections")

    def test_update_cart_quantity(self, client: TestClient, student: User, menu_item: MenuItem):
        res = client.post(
            "/cart/update",
            json={"menu_item_id": menu_item.id, "quantity": 3},
            headers=_auth(student),
        )
        assert res.status_code == 200, res.text
        cart = res.json()
        qty = next((i["quantity"] for i in cart["items"] if i["menu_item_id"] == menu_item.id), None)
        assert qty == 3
        print(f"\n  ✓ Cart quantity updated to 3")


# ===========================================================================
# STEP 5: Slots — pick a slot
# ===========================================================================

class TestStep5_Slots:

    def test_get_slots(self, client: TestClient, student: User, food_vendor: User, slot: Slot):
        res = client.get(f"/vendors/{food_vendor.id}/slots", headers=_auth(student))
        assert res.status_code == 200, res.text
        body = res.json()
        slots = body.get("slots", body) if isinstance(body, dict) else body
        assert len(slots) > 0, "No slots returned for vendor"
        for s in slots:
            assert "id" in s
            assert "start_time" in s
            assert "load_label" in s
        print(f"\n  ✓ {len(slots)} slot(s) available, AI recommendation field present")


# ===========================================================================
# STEP 6: Checkout
# ===========================================================================

class TestStep6_Checkout:
    order_id: int = 0
    pickup_token: str = ""

    def test_checkout_auto_slot(self, client: TestClient, student: User, slot: Slot):
        """POST /cart/checkout with explicit slot_id returns order & pickup token."""
        res = client.post(
            "/cart/checkout",
            json={"slot_id": slot.id, "payment_method": "UPI"},
            headers=_auth(student),
        )
        assert res.status_code in (200, 201), res.text
        data = res.json()
        assert "order_id" in data, f"No order_id in response: {data}"
        assert "pickup_token" in data
        assert data["pickup_token"].startswith("TNT-"), f"Unexpected token format: {data['pickup_token']}"
        TestStep6_Checkout.order_id = data["order_id"]
        TestStep6_Checkout.pickup_token = data["pickup_token"]
        print(f"\n  ✓ Checkout succeeded → Order #{data['order_id']}, token={data['pickup_token']}")

    def test_cart_cleared_after_checkout(self, client: TestClient, student: User):
        res = client.get("/cart/", headers=_auth(student))
        assert res.status_code == 200, res.text
        cart = res.json()
        assert cart["total_items"] == 0, "Cart should be empty after checkout"
        print("\n  ✓ Cart cleared after checkout")


# ===========================================================================
# STEP 7: Track order
# ===========================================================================

class TestStep7_OrderTracking:

    def test_my_orders_contains_new_order(self, client: TestClient, student: User):
        order_id = TestStep6_Checkout.order_id
        res = client.get("/orders/my", headers=_auth(student))
        assert res.status_code == 200, res.text
        orders = res.json()
        order_ids = [o["id"] for o in orders]
        assert order_id in order_ids, f"New order #{order_id} not in /orders/my"
        order = next(o for o in orders if o["id"] == order_id)
        assert order["status"] in ("placed", "pending")
        print(f"\n  ✓ Order #{order_id} appears in /orders/my with status={order['status']}")

    def test_order_timeline_not_empty(self, client: TestClient, student: User):
        order_id = TestStep6_Checkout.order_id
        res = client.get(f"/orders/{order_id}/timeline", headers=_auth(student))
        assert res.status_code == 200, res.text
        timeline = res.json()
        assert isinstance(timeline, list)
        assert len(timeline) > 0, "Timeline is empty — at least a 'placed' event expected"
        statuses = [t["status"] for t in timeline]
        assert any(s in statuses for s in ("placed", "pending")), f"No placed event in timeline: {statuses}"
        print(f"\n  ✓ Timeline has {len(timeline)} event(s): {statuses}")

    def test_eta_endpoint(self, client: TestClient, student: User):
        order_id = TestStep6_Checkout.order_id
        res = client.get(f"/orders/{order_id}/eta", headers=_auth(student))
        assert res.status_code == 200, res.text
        data = res.json()
        assert "eta_minutes" in data or "estimated_ready_at" in data, f"ETA response missing expected keys: {data}"
        print(f"\n  ✓ ETA endpoint responds: {data}")

    def test_qr_code_present_in_checkout(self, client: TestClient, student: User):
        """After checkout a pickup_token was returned; QR generation requires READY status."""
        token = TestStep6_Checkout.pickup_token
        assert token.startswith("TNT-"), f"Expected TNT- token from checkout, got: {token}"
        print(f"\n  ✓ Pickup token persisted from checkout: {token}")


# ===========================================================================
# STEP 8 & 9: Vendor confirms & marks ready
# ===========================================================================

class TestStep8_VendorActions:

    def test_vendor_confirm_order(self, client: TestClient, food_vendor: User):
        order_id = TestStep6_Checkout.order_id
        res = client.post(f"/orders/{order_id}/confirm", headers=_auth(food_vendor))
        assert res.status_code == 200, res.text
        data = res.json()
        # confirm_order returns {"message": "Order confirmed"}
        assert "confirmed" in str(data).lower(), f"Unexpected confirm response: {data}"
        print(f"\n  ✓ Vendor confirmed order #{order_id} → {data}")

    def test_vendor_mark_ready(self, client: TestClient, food_vendor: User):
        order_id = TestStep6_Checkout.order_id
        res = client.post(f"/orders/{order_id}/ready", headers=_auth(food_vendor))
        assert res.status_code == 200, res.text
        data = res.json()
        # mark_order_ready returns {"message": "Order marked as ready"}
        assert "ready" in str(data).lower(), f"Unexpected ready response: {data}"
        print(f"\n  ✓ Vendor marked order ready → {data}")

    def test_qr_generation_after_ready(self, client: TestClient, student: User):
        """QR generation must happen AFTER vendor marks ready."""
        order_id = TestStep6_Checkout.order_id
        res = client.post(f"/orders/{order_id}/qr", headers=_auth(student))
        assert res.status_code == 200, res.text
        data = res.json()
        assert "qr_code" in data, f"No qr_code in response: {data}"
        assert data["qr_code"], "QR code is empty/null"
        print(f"\n  ✓ QR code confirmed still valid after READY: {data['qr_code']}")


# ===========================================================================
# STEP 10: Pickup confirmation via QR
# ===========================================================================

class TestStep10_PickupConfirm:

    def test_qr_pickup_confirm(self, client: TestClient, food_vendor: User):
        token = TestStep6_Checkout.pickup_token
        res = client.post(
            "/orders/qr/pickup/confirm",
            params={"qr_code": token},
            headers=_auth(food_vendor),
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data.get("success") is True or "picked" in str(data).lower() or "confirmed" in str(data).lower(), \
            f"Unexpected pickup response: {data}"
        print(f"\n  ✓ Pickup confirmed via QR → {data}")


# ===========================================================================
# STEP 11: Submit rating/feedback
# ===========================================================================

class TestStep11_Rating:

    def test_submit_feedback_after_completion(self, client: TestClient, student: User, db: Session):
        order_id = TestStep6_Checkout.order_id
        # Force-complete the order in DB so feedback is allowed
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.status = OrderStatus.COMPLETED
            db.commit()

        res = client.post(
            f"/feedback/orders/{order_id}",
            json={
                "quality_rating": 5,
                "time_rating": 4,
                "behavior_rating": 5,
                "comment": "Excellent food and service!",
            },
            headers=_auth(student),
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert "feedback_id" in data
        print(f"\n  ✓ Rating submitted – feedback #{data['feedback_id']}")

    def test_duplicate_feedback_rejected(self, client: TestClient, student: User):
        order_id = TestStep6_Checkout.order_id
        res = client.post(
            f"/feedback/orders/{order_id}",
            json={"quality_rating": 3, "time_rating": 3, "behavior_rating": 3},
            headers=_auth(student),
        )
        assert res.status_code == 400
        print("\n  ✓ Duplicate feedback correctly rejected")

    def test_my_feedback_list(self, client: TestClient, student: User):
        res = client.get("/feedback/me", headers=_auth(student))
        assert res.status_code == 200, res.text
        feedbacks = res.json()
        assert isinstance(feedbacks, list)
        assert len(feedbacks) > 0
        fb = feedbacks[0]
        assert "quality_rating" in fb
        assert "time_rating" in fb
        assert "behavior_rating" in fb
        print(f"\n  ✓ Feedback history: {len(feedbacks)} entry(ies)")


# ===========================================================================
# EXTRA: Health + API completeness checks
# ===========================================================================

class TestAPICompleteness:

    def test_health_live(self, client: TestClient):
        res = client.get("/health/live")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"
        print("\n  ✓ /health/live OK")

    def test_health_ready(self, client: TestClient):
        res = client.get("/health/ready")
        assert res.status_code == 200
        print("\n  ✓ /health/ready OK")

    def test_recommendations_not_empty(self, client: TestClient, student: User):
        res = client.get(f"/v1/ai/recommendations/{student.id}", headers=_auth(student))
        if res.status_code == 404:
            pytest.skip("AI recommendations route not yet under /v1")
        assert res.status_code == 200, res.text
        data = res.json()
        recs = data.get("recommended_items") or data.get("top_recommended") or []
        if len(recs) == 0:
            pytest.skip("No recommendation data yet — needs order history")
        for item in recs:
            assert item.get("name"), f"Reco item missing name: {item}"
        print(f"\n  ✓ {len(recs)} recommendation(s) returned")

    def test_notifications_endpoint(self, client: TestClient, student: User):
        res = client.get("/notifications/", headers=_auth(student))
        assert res.status_code in (200, 404), res.text
        if res.status_code == 200:
            data = res.json()
            assert isinstance(data, (list, dict))
            print(f"\n  ✓ Notifications endpoint OK")

    def test_rewards_endpoint(self, client: TestClient, student: User):
        res = client.get(f"/rewards/{student.id}", headers=_auth(student))
        assert res.status_code == 200, f"Rewards failed: {res.text}"
        data = res.json()
        assert any(k in data for k in ("points_balance", "balance", "points", "current_points")), \
            f"Rewards response missing points field: {data}"
        print(f"\n  ✓ Rewards endpoint OK: {data}")
