"""
Tests for menu endpoints:
  GET /menu/{vendor_id}       – list vendor's menu items (public)
  POST /menu/                 – vendor adds a menu item (file upload)
  PUT  /menu/{item_id}        – vendor updates a menu item
"""
import io
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.menu.model import MenuItem
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
    vendor = User(
        phone="8700000001",
        name="FoodVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
        vendor_type="food",
    )
    stationery_vendor = User(
        phone="8700000002",
        name="StatVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
        vendor_type="stationery",
    )
    unapproved = User(
        phone="8700000003",
        name="PendingVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=False,
        vendor_type="food",
    )
    student = User(phone="8700000010", name="Student", role=UserRole.STUDENT, is_active=True)
    test_db_session.add_all([vendor, stationery_vendor, unapproved, student])
    test_db_session.commit()
    for u in (vendor, stationery_vendor, unapproved, student):
        test_db_session.refresh(u)

    item = MenuItem(
        vendor_id=vendor.id,
        name="Biryani",
        description="Spicy rice",
        price=8000,
        image_url="/uploads/menu/test.jpg",
        is_available=True,
    )
    unavailable_item = MenuItem(
        vendor_id=vendor.id,
        name="Unavailable Dish",
        description="Not yet",
        price=500,
        image_url="/uploads/menu/na.jpg",
        is_available=False,
    )
    test_db_session.add_all([item, unavailable_item])
    test_db_session.commit()
    for obj in (item, unavailable_item):
        test_db_session.refresh(obj)

    return {
        "vendor": vendor,
        "stationery_vendor": stationery_vendor,
        "unapproved": unapproved,
        "student": student,
        "item": item,
        "unavailable_item": unavailable_item,
    }


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=False)


def _fake_image():
    """Return a minimal fake PNG binary wrapped in a BytesIO."""
    return io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)


# ---------------------------------------------------------------------------
# GET /menu/{vendor_id} – public, no auth required
# ---------------------------------------------------------------------------


def test_get_menu_returns_available_items(test_db_session, seed_data):
    with TestClient(app, raise_server_exceptions=False) as client:
        app.dependency_overrides[get_db] = lambda: test_db_session
        resp = client.get(f"/menu/{seed_data['vendor'].id}")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert seed_data["item"].id in ids
    # Unavailable items must be excluded
    assert seed_data["unavailable_item"].id not in ids


def test_get_menu_excludes_unavailable_items(test_db_session, seed_data):
    with TestClient(app, raise_server_exceptions=False) as client:
        app.dependency_overrides[get_db] = lambda: test_db_session
        resp = client.get(f"/menu/{seed_data['vendor'].id}")
    app.dependency_overrides.clear()

    names = [i["name"] for i in resp.json()]
    assert "Unavailable Dish" not in names


def test_get_menu_returns_404_for_unapproved_vendor(test_db_session, seed_data):
    with TestClient(app, raise_server_exceptions=False) as client:
        app.dependency_overrides[get_db] = lambda: test_db_session
        resp = client.get(f"/menu/{seed_data['unapproved'].id}")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_get_menu_returns_404_for_nonexistent_vendor(test_db_session, seed_data):
    with TestClient(app, raise_server_exceptions=False) as client:
        app.dependency_overrides[get_db] = lambda: test_db_session
        resp = client.get("/menu/99999")
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_get_menu_items_have_required_fields(test_db_session, seed_data):
    with TestClient(app, raise_server_exceptions=False) as client:
        app.dependency_overrides[get_db] = lambda: test_db_session
        resp = client.get(f"/menu/{seed_data['vendor'].id}")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    item = resp.json()[0]
    for field in ("id", "name", "price", "image_url"):
        assert field in item, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# POST /menu/ – vendor adds a menu item (multipart form + file upload)
# ---------------------------------------------------------------------------


def test_approved_food_vendor_can_add_menu_item(test_db_session, seed_data):
    with patch("app.modules.menu.router.save_menu_image", return_value="/uploads/menu/mocked.jpg"):
        client = _make_client(test_db_session, seed_data["vendor"])
        resp = client.post(
            "/menu/",
            data={"name": "Pasta", "price": 15000, "description": "Creamy pasta"},
            files={"image": ("pasta.jpg", _fake_image(), "image/jpeg")},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["name"] == "Pasta"
    assert resp.json()["price"] == 15000


def test_add_menu_item_persisted_in_db(test_db_session, seed_data):
    with patch("app.modules.menu.router.save_menu_image", return_value="/uploads/menu/mocked.jpg"):
        client = _make_client(test_db_session, seed_data["vendor"])
        resp = client.post(
            "/menu/",
            data={"name": "Sandwich", "price": 5000},
            files={"image": ("sandwich.jpg", _fake_image(), "image/jpeg")},
        )
    app.dependency_overrides.clear()

    item_id = resp.json()["id"]
    item = test_db_session.query(MenuItem).filter(MenuItem.id == item_id).first()
    assert item is not None
    assert item.name == "Sandwich"
    assert item.vendor_id == seed_data["vendor"].id


def test_unapproved_vendor_cannot_add_menu_item(test_db_session, seed_data):
    with patch("app.modules.menu.router.save_menu_image", return_value="/uploads/menu/mocked.jpg"):
        client = _make_client(test_db_session, seed_data["unapproved"])
        resp = client.post(
            "/menu/",
            data={"name": "Noodles", "price": 4000},
            files={"image": ("noodles.jpg", _fake_image(), "image/jpeg")},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_stationery_vendor_cannot_add_menu_item(test_db_session, seed_data):
    with patch("app.modules.menu.router.save_menu_image", return_value="/uploads/menu/mocked.jpg"):
        client = _make_client(test_db_session, seed_data["stationery_vendor"])
        resp = client.post(
            "/menu/",
            data={"name": "Pen", "price": 100},
            files={"image": ("pen.jpg", _fake_image(), "image/jpeg")},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_student_cannot_add_menu_item(test_db_session, seed_data):
    with patch("app.modules.menu.router.save_menu_image", return_value="/uploads/menu/mocked.jpg"):
        client = _make_client(test_db_session, seed_data["student"])
        resp = client.post(
            "/menu/",
            data={"name": "Burger", "price": 6000},
            files={"image": ("burger.jpg", _fake_image(), "image/jpeg")},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /menu/{item_id} – vendor updates a menu item
# ---------------------------------------------------------------------------


def test_vendor_can_update_own_menu_item_name(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.put(
        f"/menu/{seed_data['item'].id}",
        data={"name": "Special Biryani"},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    test_db_session.refresh(seed_data["item"])
    assert seed_data["item"].name == "Special Biryani"


def test_vendor_can_update_own_menu_item_price(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.put(
        f"/menu/{seed_data['item'].id}",
        data={"price": 9000},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    test_db_session.refresh(seed_data["item"])
    assert seed_data["item"].price == 9000


def test_vendor_can_toggle_item_availability(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.put(
        f"/menu/{seed_data['item'].id}",
        data={"is_available": "false"},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    test_db_session.refresh(seed_data["item"])
    assert seed_data["item"].is_available is False


def test_update_nonexistent_menu_item_returns_404(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.put("/menu/99999", data={"name": "Ghost"})
    app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_stationery_vendor_cannot_update_food_menu(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["stationery_vendor"])
    resp = client.put(
        f"/menu/{seed_data['item'].id}",
        data={"name": "Hacked item"},
    )
    app.dependency_overrides.clear()

    assert resp.status_code == 403
