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
from app.modules.notifications.model import Notification
from app.modules.orders.model import Order
from app.modules.payments.model import Payment, PaymentStatus
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
    owner = User(phone="9000000001", name="Owner", role=UserRole.STUDENT, is_active=True)
    member = User(phone="9000000002", name="Member", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9000000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )

    test_db_session.add_all([owner, member, vendor])
    test_db_session.commit()
    test_db_session.refresh(owner)
    test_db_session.refresh(member)
    test_db_session.refresh(vendor)

    menu_item = MenuItem(
        vendor_id=vendor.id,
        name="Veg Sandwich",
        description="Test item",
        price=50,
        image_url="https://example.com/item.png",
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

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_group_cart_full_flow(client, seed_data, auth_context, test_db_session):
    owner = seed_data["owner"]
    member = seed_data["member"]
    menu_item = seed_data["menu_item"]
    slot = seed_data["slot"]

    create_resp = client.post("/groups/", json={"name": "Lunch Squad"})
    assert create_resp.status_code == 200
    group = create_resp.json()
    group_id = group["id"]

    invite_resp = client.post(f"/groups/{group_id}/invite", json={"phone": member.phone})
    assert invite_resp.status_code == 200

    add_item_resp = client.post(
        f"/groups/{group_id}/cart",
        json={"menu_item_id": menu_item.id, "quantity": 2},
    )
    assert add_item_resp.status_code == 200

    lock_resp = client.post(f"/groups/{group_id}/slot/lock", json={"slot_id": slot.id})
    assert lock_resp.status_code == 200

    split_resp = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.EQUAL.value},
    )
    assert split_resp.status_code == 200

    get_splits_resp = client.get(f"/groups/{group_id}/payment-splits")
    assert get_splits_resp.status_code == 200
    assert len(get_splits_resp.json()) == 1

    place_resp = client.post(f"/groups/{group_id}/order")
    assert place_resp.status_code == 200
    body = place_resp.json()
    assert body["group_id"] == group_id
    assert body["total_amount"] == 100
    assert len(body["orders"]) == 1
    assert "order_id" in body["orders"][0]
    assert "payment_id" in body["orders"][0]
    assert "payment_status" in body["orders"][0]
    assert body["payment_reconciliation"]["aggregate_status"] == "pending"

    persisted_order = test_db_session.query(Order).filter(Order.id == body["orders"][0]["order_id"]).first()
    assert persisted_order is not None
    assert persisted_order.total_amount == 100

    persisted_payment = test_db_session.query(Payment).filter(Payment.id == body["orders"][0]["payment_id"]).first()
    assert persisted_payment is not None
    assert persisted_payment.amount == 100
    assert persisted_payment.status == PaymentStatus.INITIATED

    notifications = (
        test_db_session.query(Notification)
        .filter(Notification.user_id.in_([owner.id, member.id]))
        .all()
    )
    assert len(notifications) >= 8
    owner_notifications = [n for n in notifications if n.user_id == owner.id]
    member_notifications = [n for n in notifications if n.user_id == member.id]
    assert owner_notifications
    assert member_notifications

    get_group_resp = client.get(f"/groups/{group_id}")
    assert get_group_resp.status_code == 200

    my_groups_resp = client.get("/groups/my-groups")
    assert my_groups_resp.status_code == 200
    group_ids = [entry["id"] for entry in my_groups_resp.json()]
    assert group_id in group_ids

    auth_context.update({"id": member.id, "phone": member.phone, "role": member.role.value})

    non_owner_place = client.post(f"/groups/{group_id}/order")
    assert non_owner_place.status_code == 403
