from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot, SlotStatus
from app.modules.stationery.service_model import StationeryService
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
    approved_vendor = User(
        phone="7300000001",
        name="Approved Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    unapproved_vendor = User(
        phone="7300000002",
        name="Unapproved Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=False,
    )
    stationery_vendor = User(
        phone="7300000003",
        name="Stationery Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )

    test_db_session.add_all([approved_vendor, unapproved_vendor, stationery_vendor])
    test_db_session.commit()
    test_db_session.refresh(approved_vendor)
    test_db_session.refresh(stationery_vendor)

    menu_item = MenuItem(
        vendor_id=approved_vendor.id,
        name="Idli",
        description="Soft idli",
        price=40,
        image_url="https://example.com/idli.png",
        is_available=True,
    )
    slot = Slot(
        vendor_id=approved_vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=4,
        status=SlotStatus.AVAILABLE,
    )
    medium_slot = Slot(
        vendor_id=approved_vendor.id,
        start_time=utcnow_naive() + timedelta(hours=2),
        end_time=utcnow_naive() + timedelta(hours=3),
        max_orders=10,
        current_orders=5,
        status=SlotStatus.AVAILABLE,
    )
    high_slot = Slot(
        vendor_id=approved_vendor.id,
        start_time=utcnow_naive() + timedelta(hours=3),
        end_time=utcnow_naive() + timedelta(hours=4),
        max_orders=10,
        current_orders=8,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add_all([menu_item, slot, medium_slot, high_slot])

    stationery_service = StationeryService(
        vendor_id=stationery_vendor.id,
        name="Printing",
        service_type="bw_print",
        price_per_page=500,
        price_per_unit=5,
        unit="page",
        is_available=True,
    )
    test_db_session.add(stationery_service)
    test_db_session.commit()

    return {"food_vendor_id": approved_vendor.id, "stationery_vendor_id": stationery_vendor.id}


@pytest.fixture()
def client(test_db_session):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_vendors_contracts(client, seed_data):
    vendor_id = seed_data["food_vendor_id"]
    stationery_vendor_id = seed_data["stationery_vendor_id"]

    list_resp = client.get("/vendors?type=food")
    assert list_resp.status_code == 200
    data = list_resp.json()
    vendors = data["items"]
    assert len(vendors) == 1
    assert vendors[0]["id"] == vendor_id
    assert vendors[0]["vendor_type"] == "food"
    assert vendors[0]["live_load_label"] == "MEDIUM"
    assert vendors[0]["express_pickup_eligible"] is True

    stationery_resp = client.get("/vendors?type=stationery")
    assert stationery_resp.status_code == 200
    stationery_data = stationery_resp.json()
    stationery_vendors = stationery_data["items"]
    assert len(stationery_vendors) == 1
    assert stationery_vendors[0]["id"] == stationery_vendor_id
    assert stationery_vendors[0]["vendor_type"] == "stationery"

    details_resp = client.get(f"/vendors/{vendor_id}")
    assert details_resp.status_code == 200
    assert details_resp.json()["id"] == vendor_id
    assert details_resp.json()["live_load_label"] == "MEDIUM"
    assert details_resp.json()["express_pickup_eligible"] is True

    menu_resp = client.get(f"/vendors/{vendor_id}/menu")
    assert menu_resp.status_code == 200
    menu = menu_resp.json()
    assert len(menu) == 1
    assert menu[0]["name"] == "Idli"

    slots_resp = client.get(f"/vendors/{vendor_id}/slots")
    assert slots_resp.status_code == 200
    slots_data = slots_resp.json()
    slots = slots_data["slots"]
    assert len(slots) == 3
    labels = {slot_entry["load_label"] for slot_entry in slots}
    assert labels == {"LOW", "MEDIUM", "HIGH"}

    low_slot = next(slot_entry for slot_entry in slots if slot_entry["load_label"] == "LOW")
    medium_slot = next(slot_entry for slot_entry in slots if slot_entry["load_label"] == "MEDIUM")
    high_slot = next(slot_entry for slot_entry in slots if slot_entry["load_label"] == "HIGH")

    assert low_slot["express_pickup_eligible"] is True
    assert medium_slot["express_pickup_eligible"] is True
    assert high_slot["express_pickup_eligible"] is False
