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
    owner = User(phone="8400000001", name="Owner", role=UserRole.STUDENT, is_active=True)
    member = User(phone="8400000002", name="Member", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8400000010",
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
        name="Puff",
        description="Test item",
        price=50,
        image_url="https://example.com/puff.png",
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

    return {"owner": owner, "member": member, "menu_item": menu_item, "slot": slot}


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


def test_custom_split_total_mismatch_returns_400(client, seed_data, auth_context):
    owner = seed_data["owner"]
    member = seed_data["member"]
    menu_item = seed_data["menu_item"]
    slot = seed_data["slot"]

    create_resp = client.post("/groups/", json={"name": "Mismatch Split"})
    assert create_resp.status_code == 200
    group_id = create_resp.json()["id"]

    invite_resp = client.post(f"/groups/{group_id}/invite", json={"phone": member.phone})
    assert invite_resp.status_code == 200

    add_owner_item = client.post(
        f"/groups/{group_id}/cart",
        json={"menu_item_id": menu_item.id, "quantity": 1},
    )
    assert add_owner_item.status_code == 200

    auth_context.update({"id": member.id, "phone": member.phone, "role": member.role.value})
    add_member_item = client.post(
        f"/groups/{group_id}/cart",
        json={"menu_item_id": menu_item.id, "quantity": 1},
    )
    assert add_member_item.status_code == 200

    auth_context.update({"id": owner.id, "phone": owner.phone, "role": owner.role.value})
    lock_resp = client.post(f"/groups/{group_id}/slot/lock", json={"slot_id": slot.id})
    assert lock_resp.status_code == 200

    owner_split = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.CUSTOM.value, "amount": 70},
    )
    assert owner_split.status_code == 200

    auth_context.update({"id": member.id, "phone": member.phone, "role": member.role.value})
    member_split = client.post(
        f"/groups/{group_id}/payment-split",
        json={"split_type": PaymentSplitType.CUSTOM.value, "amount": 20},
    )
    assert member_split.status_code == 200

    auth_context.update({"id": owner.id, "phone": owner.phone, "role": owner.role.value})
    place_resp = client.post(f"/groups/{group_id}/order")
    assert place_resp.status_code == 400
    assert place_resp.json()["detail"] == "Custom split total must match group total amount"
