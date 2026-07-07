"""
Group Payment Splits Tests
===========================
Covers split-specific scenarios for group cart orders that complement
the existing test_group_cart_integration.py and test_group_cart_split_validation.py.

Scenarios:
  CUSTOM split validation (pre-reconciliation, via set_payment_split):
    • Negative amount → 400
  CUSTOM split reconciliation (at place_group_order time):
    • Member without a configured split → 400
  EQUAL split:
    • 2 members, even total → each pays half; Payment rows created with correct amounts
  UNIFIED split:
    • Owner's payment INITIATED; member's payment SUCCESS (payable = 0)
  get_payment_splits:
    • Returns all configured splits for the group
  Guard tests:
    • Non-owner calling place_group_order → 403
    • place_group_order with empty cart → 400
    • place_group_order without slot lock → 400

Phone number range: 8800000xxx
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
from app.modules.group_cart.model import PaymentSplitType
from app.modules.menu.model import MenuItem
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_db_session():
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
def seed_data(test_db_session):
    owner = User(phone="8800000001", name="Owner", role=UserRole.STUDENT, is_active=True)
    member = User(phone="8800000002", name="Member", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8800000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([owner, member, vendor])
    test_db_session.commit()
    for u in [owner, member, vendor]:
        test_db_session.refresh(u)

    menu_item = MenuItem(
        vendor_id=vendor.id,
        name="Sandwich",
        description="Test",
        price=50,
        image_url="https://example.com/s.png",
        is_available=True,
    )
    test_db_session.add(menu_item)
    test_db_session.commit()
    test_db_session.refresh(menu_item)

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

    return {
        "owner": owner,
        "member": member,
        "vendor": vendor,
        "menu_item": menu_item,
        "slot": slot,
    }


@pytest.fixture()
def auth_context(seed_data):
    owner = seed_data["owner"]
    return {"id": owner.id, "phone": owner.phone, "role": owner.role.value}


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

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_group_with_items(client, seed_data, auth_context, *, lock_slot: bool = True):
    """Create group, invite member, add 1 item each, optionally lock slot.

    Returns group_id.
    """
    owner = seed_data["owner"]
    member = seed_data["member"]
    menu_item = seed_data["menu_item"]
    slot = seed_data["slot"]

    # Owner creates group
    auth_context.update({"id": owner.id, "phone": owner.phone, "role": owner.role.value})
    create_resp = client.post("/groups/", json={"name": "Split Test Group"})
    assert create_resp.status_code == 200
    group_id = create_resp.json()["id"]

    # Invite member
    invite = client.post(f"/groups/{group_id}/invite", json={"phone": member.phone})
    assert invite.status_code == 200

    # Owner adds item
    add = client.post(f"/groups/{group_id}/cart", json={"menu_item_id": menu_item.id, "quantity": 1})
    assert add.status_code == 200

    # Member adds item
    auth_context.update({"id": member.id, "phone": member.phone, "role": member.role.value})
    add2 = client.post(f"/groups/{group_id}/cart", json={"menu_item_id": menu_item.id, "quantity": 1})
    assert add2.status_code == 200

    # Switch back to owner
    auth_context.update({"id": owner.id, "phone": owner.phone, "role": owner.role.value})

    if lock_slot:
        lock = client.post(f"/groups/{group_id}/slot/lock", json={"slot_id": slot.id})
        assert lock.status_code == 200

    return group_id


# ---------------------------------------------------------------------------
# CUSTOM split — pre-reconciliation validation via set_payment_split
# ---------------------------------------------------------------------------

def test_custom_split_negative_amount_returns_400(client, seed_data, auth_context):
    """set_payment_split with a negative CUSTOM amount must be rejected immediately."""
    group_id = _setup_group_with_items(client, seed_data, auth_context)

    resp = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.CUSTOM.value, "amount": -10},
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# CUSTOM split — reconciliation-time validation via place_group_order
# ---------------------------------------------------------------------------

def test_custom_split_missing_member_returns_400(client, seed_data, auth_context):
    """If only the owner configures a CUSTOM split, placing the order must fail
    because the member's split is not covered."""
    group_id = _setup_group_with_items(client, seed_data, auth_context)

    # Owner configures CUSTOM split for themselves only (member not configured)
    owner_split = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.CUSTOM.value, "amount": 100},
    )
    assert owner_split.status_code == 200

    # Placing the order should fail: member has no CUSTOM split entry
    place_resp = client.post(f"/groups/{group_id}/order")
    assert place_resp.status_code == 400


# ---------------------------------------------------------------------------
# EQUAL split
# ---------------------------------------------------------------------------

def test_equal_split_creates_correct_payment_amounts(client, seed_data, auth_context, test_db_session):
    """2 members × 1 sandwich (50 each) = total 100.
    EQUAL split → each owes 50. Both payments should be INITIATED (non-zero)."""
    group_id = _setup_group_with_items(client, seed_data, auth_context)

    # No explicit split config needed — EQUAL is the default
    place_resp = client.post(f"/groups/{group_id}/order")
    assert place_resp.status_code == 200, place_resp.json()

    # Verify both payment rows in the DB
    test_db_session.expire_all()
    payments = test_db_session.query(Payment).all()

    # Filter to payments related to this place_group_order call (non-stationery)
    order_payments = [p for p in payments if p.order_id is not None]
    assert len(order_payments) == 2

    amounts = sorted(p.amount for p in order_payments)
    # total = 100, n = 2 → each 50
    assert amounts == [50, 50]

    # Both are still INITIATED (need actual Razorpay payment)
    statuses = {p.status for p in order_payments}
    assert statuses == {PaymentStatus.INITIATED}


# ---------------------------------------------------------------------------
# UNIFIED split
# ---------------------------------------------------------------------------

def test_unified_split_owner_pays_all_member_is_success(client, seed_data, auth_context, test_db_session):
    """UNIFIED split: owner pays total (100), member owes 0 → member payment SUCCESS."""
    owner = seed_data["owner"]
    member = seed_data["member"]
    group_id = _setup_group_with_items(client, seed_data, auth_context)

    # Owner sets UNIFIED split
    split_resp = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.UNIFIED.value},
    )
    assert split_resp.status_code == 200

    place_resp = client.post(f"/groups/{group_id}/order")
    assert place_resp.status_code == 200, place_resp.json()

    test_db_session.expire_all()
    payments = test_db_session.query(Payment).filter(Payment.order_id.isnot(None)).all()
    assert len(payments) == 2

    owner_payments = [p for p in payments if p.amount > 0]
    member_payments = [p for p in payments if p.amount == 0]

    assert len(owner_payments) == 1
    assert len(member_payments) == 1
    assert owner_payments[0].status == PaymentStatus.INITIATED
    assert member_payments[0].status == PaymentStatus.SUCCESS


# ---------------------------------------------------------------------------
# get_payment_splits
# ---------------------------------------------------------------------------

def test_get_payment_splits_returns_configured_splits(client, seed_data, auth_context):
    """After setting a CUSTOM split, get_payment_splits should return it."""
    group_id = _setup_group_with_items(client, seed_data, auth_context)

    set_resp = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.CUSTOM.value, "amount": 60},
    )
    assert set_resp.status_code == 200

    get_resp = client.get(f"/groups/{group_id}/payment-splits")
    assert get_resp.status_code == 200
    splits = get_resp.json()
    assert isinstance(splits, list)
    assert len(splits) >= 1
    owner_split = next(s for s in splits if s["split_type"] == PaymentSplitType.CUSTOM.value)
    assert owner_split["amount"] == 60


# ---------------------------------------------------------------------------
# Guard tests
# ---------------------------------------------------------------------------

def test_non_owner_cannot_place_group_order(client, seed_data, auth_context):
    owner = seed_data["owner"]
    member = seed_data["member"]
    group_id = _setup_group_with_items(client, seed_data, auth_context)

    # Switch to member and try to place
    auth_context.update({"id": member.id, "phone": member.phone, "role": member.role.value})
    resp = client.post(f"/groups/{group_id}/order")
    assert resp.status_code == 403


def test_place_group_order_without_slot_lock_returns_400(client, seed_data, auth_context):
    # Build group WITHOUT locking the slot
    group_id = _setup_group_with_items(client, seed_data, auth_context, lock_slot=False)

    resp = client.post(f"/groups/{group_id}/order")
    assert resp.status_code == 400


def test_place_group_order_with_empty_cart_returns_400(client, seed_data, auth_context):
    """Owner creates a group but adds no items → empty cart → 400."""
    owner = seed_data["owner"]
    member = seed_data["member"]
    slot = seed_data["slot"]

    auth_context.update({"id": owner.id, "phone": owner.phone, "role": owner.role.value})
    create_resp = client.post("/groups/", json={"name": "Empty Cart Group"})
    assert create_resp.status_code == 200
    group_id = create_resp.json()["id"]

    # Invite member (so group has members)
    client.post(f"/groups/{group_id}/invite", json={"phone": member.phone})

    # Lock slot without adding any items
    client.post(f"/groups/{group_id}/slot/lock", json={"slot_id": slot.id})

    resp = client.post(f"/groups/{group_id}/order")
    assert resp.status_code == 400
