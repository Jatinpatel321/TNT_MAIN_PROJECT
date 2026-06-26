"""
Search endpoints — test_search_endpoints.py

Covers:
  GET /search              — unified search with filters and sorting
  GET /search/suggestions  — autocomplete suggestions
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.database.base import Base
from app.main import app
from app.modules.users.model import User, UserRole
from app.modules.menu.model import MenuItem
from app.modules.stationery.service_model import StationeryService


@pytest.fixture()
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng)
    # Create vendor_profiles table for the search module
    with eng.connect() as conn:
        try:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS vendor_profiles ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "vendor_id INTEGER UNIQUE NOT NULL, "
                "business_name TEXT NOT NULL DEFAULT 'Test Business', "
                "category TEXT, "
                "description TEXT, "
                "rating REAL DEFAULT 4.5, "
                "location TEXT)"
            ))
            conn.commit()
        except Exception:
            pass
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.pop(get_db, None)


_vendor_counter = 1000

def _add_vendor(db, name, vendor_type="food", **kwargs):
    global _vendor_counter
    _vendor_counter += 1
    v = User(
        phone=f"99{_vendor_counter}",
        name=name,
        role=UserRole.VENDOR,
        vendor_type=vendor_type,
        is_approved=True,
        is_active=True,
        **kwargs,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _add_vendor_profile(db, vendor_id, category="cafe", rating=4.5, description=None, location="Campus"):
    db.execute(text(
        "INSERT INTO vendor_profiles (vendor_id, category, description, rating, location, business_name) "
        "VALUES (:vid, :cat, :desc, :rating, :loc, :bus_name)"
    ), {"vid": vendor_id, "cat": category, "desc": description, "rating": rating, "loc": location, "bus_name": "Test Business"})
    db.commit()


def _add_menu_item(db, vendor_id, name, price=5000, is_available=True):
    item = MenuItem(
        vendor_id=vendor_id,
        name=name,
        description=f"Delicious {name}",
        price=price,
        image_url=f"/uploads/menu/{name.lower().replace(' ','_')}.jpg",
        is_available=is_available,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _add_stationery_service(db, vendor_id, name, price_per_unit=200, unit="page", is_available=True):
    svc = StationeryService(
        vendor_id=vendor_id,
        name=name,
        price_per_unit=price_per_unit,
        unit=unit,
        is_available=is_available,
        service_type="color_print",
        price_per_page=price_per_unit,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


# ── Search basic ────────────────────────────────────────────────────────────


class TestSearchBasic:
    def test_empty_search_returns_empty(self, client, db):
        resp = client.get("/search", params={"q": "nonexistent"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_vendors"] == 0
        assert data["total_items"] == 0

    def test_search_vendor_by_name(self, client, db):
        v = _add_vendor(db, "Campus Cafe", "food")
        _add_vendor_profile(db, v.id, "cafe", 4.8)
        _add_menu_item(db, v.id, "Espresso")

        resp = client.get("/search", params={"q": "Campus"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_vendors"] >= 1
        found = any(v2["name"] == "Campus Cafe" for v2 in data["vendors"])
        assert found

    def test_search_menu_item_by_name(self, client, db):
        v = _add_vendor(db, "Burger Hub", "food")
        _add_vendor_profile(db, v.id, "fast food", 4.2)
        _add_menu_item(db, v.id, "Classic Burger")

        resp = client.get("/search", params={"q": "Burger"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] >= 1
        found = any(it["name"] == "Classic Burger" for it in data["items"])
        assert found

    def test_search_stationery_service_by_name(self, client, db):
        v = _add_vendor(db, "Print Hub", "stationery")
        _add_vendor_profile(db, v.id, "printing", 4.0)
        _add_stationery_service(db, v.id, "Color Printing", 500, "page")

        resp = client.get("/search", params={"q": "Print"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] >= 1
        found = any(it["name"] == "Color Printing" for it in data["items"])
        assert found

    def test_search_no_query_returns_all(self, client, db):
        v = _add_vendor(db, "Pizza Station", "food")
        _add_vendor_profile(db, v.id, "italian", 4.6)
        _add_menu_item(db, v.id, "Margherita Pizza")

        resp = client.get("/search")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_vendors"] >= 1
        assert data["total_items"] >= 1


# ── Type filter ─────────────────────────────────────────────────────────────


class TestSearchTypeFilter:
    def test_type_food_excludes_stationery_items(self, client, db):
        vf = _add_vendor(db, "Food Vendor", "food")
        _add_vendor_profile(db, vf.id, "cafe")
        _add_menu_item(db, vf.id, "Sandwich")

        vs = _add_vendor(db, "Stationery Vendor", "stationery")
        _add_vendor_profile(db, vs.id, "printing")
        _add_stationery_service(db, vs.id, "Xerox Copy")

        resp = client.get("/search", params={"q": "", "type": "food"})
        assert resp.status_code == 200
        data = resp.json()
        food_items = [i for i in data["items"] if i["item_type"] == "food"]
        stat_items = [i for i in data["items"] if i["item_type"] == "stationery"]
        assert len(food_items) >= 1
        assert len(stat_items) == 0

    def test_type_stationery_excludes_food_items(self, client, db):
        vf = _add_vendor(db, "Food Vendor2", "food")
        _add_vendor_profile(db, vf.id, "cafe")
        _add_menu_item(db, vf.id, "Pasta")

        vs = _add_vendor(db, "Stationery Vendor2", "stationery")
        _add_vendor_profile(db, vs.id, "printing")
        _add_stationery_service(db, vs.id, "Binding")

        resp = client.get("/search", params={"q": "", "type": "stationery"})
        assert resp.status_code == 200
        data = resp.json()
        food_items = [i for i in data["items"] if i["item_type"] == "food"]
        stat_items = [i for i in data["items"] if i["item_type"] == "stationery"]
        assert len(food_items) == 0
        assert len(stat_items) >= 1

    def test_invalid_type_returns_400(self, client, db):
        resp = client.get("/search", params={"type": "invalid"})
        assert resp.status_code == 400


# ── Price filter ─────────────────────────────────────────────────────────────


class TestSearchPriceFilter:
    def test_price_min_filter(self, client, db):
        v = _add_vendor(db, "Price Vendor", "food")
        _add_vendor_profile(db, v.id, "cafe")
        _add_menu_item(db, v.id, "Cheap Item", price=2000)
        _add_menu_item(db, v.id, "Expensive Item", price=10000)

        resp = client.get("/search", params={"q": "", "price_min": 5000})
        assert resp.status_code == 200
        data = resp.json()
        for it in data["items"]:
            assert it["price"] >= 5000

    def test_price_max_filter(self, client, db):
        v = _add_vendor(db, "Price Vendor2", "food")
        _add_vendor_profile(db, v.id, "cafe")
        _add_menu_item(db, v.id, "Cheap Item2", price=2000)
        _add_menu_item(db, v.id, "Expensive Item2", price=10000)

        resp = client.get("/search", params={"q": "", "price_max": 5000})
        assert resp.status_code == 200
        data = resp.json()
        for it in data["items"]:
            assert it["price"] <= 5000

    def test_price_range_filter(self, client, db):
        v = _add_vendor(db, "Price Vendor3", "food")
        _add_vendor_profile(db, v.id, "cafe")
        _add_menu_item(db, v.id, "Low", price=1000)
        _add_menu_item(db, v.id, "Mid", price=5000)
        _add_menu_item(db, v.id, "High", price=15000)

        resp = client.get("/search", params={"q": "", "price_min": 3000, "price_max": 8000})
        assert resp.status_code == 200
        data = resp.json()
        for it in data["items"]:
            assert 3000 <= it["price"] <= 8000


# ── Rating filter ────────────────────────────────────────────────────────────


class TestSearchRatingFilter:
    def test_min_rating_filter(self, client, db):
        v1 = _add_vendor(db, "Good Vendor", "food")
        _add_vendor_profile(db, v1.id, "cafe", rating=4.8)
        _add_menu_item(db, v1.id, "Good Food")

        v2 = _add_vendor(db, "Bad Vendor", "food")
        _add_vendor_profile(db, v2.id, "cafe", rating=2.0)
        _add_menu_item(db, v2.id, "Bad Food")

        resp = client.get("/search", params={"q": "", "min_rating": 4.0})
        assert resp.status_code == 200
        data = resp.json()
        for it in data["items"]:
            assert it["vendor_rating"] >= 4.0

    def test_min_rating_filters_vendors(self, client, db):
        v1 = _add_vendor(db, "High Rated Vendor", "food")
        _add_vendor_profile(db, v1.id, "cafe", rating=4.9)

        v2 = _add_vendor(db, "Low Rated Vendor", "food")
        _add_vendor_profile(db, v2.id, "cafe", rating=2.5)

        resp = client.get("/search", params={"q": "", "min_rating": 4.0})
        assert resp.status_code == 200
        data = resp.json()
        for v in data["vendors"]:
            assert v["rating"] >= 4.0


# ── Sorting ─────────────────────────────────────────────────────────────────


class TestSearchSorting:
    def test_sort_price_low(self, client, db):
        v = _add_vendor(db, "Sort Vendor", "food")
        _add_vendor_profile(db, v.id, "cafe")
        _add_menu_item(db, v.id, "Item A", price=10000)
        _add_menu_item(db, v.id, "Item B", price=2000)
        _add_menu_item(db, v.id, "Item C", price=5000)

        resp = client.get("/search", params={"q": "", "sort": "price_low"})
        assert resp.status_code == 200
        data = resp.json()
        prices = [it["price"] for it in data["items"]]
        assert prices == sorted(prices)

    def test_sort_price_high(self, client, db):
        v = _add_vendor(db, "Sort Vendor2", "food")
        _add_vendor_profile(db, v.id, "cafe")
        _add_menu_item(db, v.id, "Item X", price=3000)
        _add_menu_item(db, v.id, "Item Y", price=9000)

        resp = client.get("/search", params={"q": "", "sort": "price_high"})
        assert resp.status_code == 200
        data = resp.json()
        prices = [it["price"] for it in data["items"]]
        assert prices == sorted(prices, reverse=True)

    def test_sort_rating(self, client, db):
        v1 = _add_vendor(db, "Top Vendor", "food")
        _add_vendor_profile(db, v1.id, "cafe", rating=4.9)
        _add_menu_item(db, v1.id, "Top Food")

        v2 = _add_vendor(db, "Mid Vendor", "food")
        _add_vendor_profile(db, v2.id, "cafe", rating=3.5)
        _add_menu_item(db, v2.id, "Mid Food")

        resp = client.get("/search", params={"q": "", "sort": "rating"})
        assert resp.status_code == 200
        data = resp.json()
        ratings = [it["vendor_rating"] for it in data["items"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_invalid_sort_returns_400(self, client, db):
        resp = client.get("/search", params={"sort": "invalid"})
        assert resp.status_code == 400


# ── Pagination ──────────────────────────────────────────────────────────────


class TestSearchPagination:
    def test_default_page_size(self, client, db):
        v = _add_vendor(db, "Page Vendor", "food")
        _add_vendor_profile(db, v.id, "cafe")
        for i in range(5):
            _add_menu_item(db, v.id, f"Item {i}", price=1000 + i * 100)

        resp = client.get("/search", params={"q": "", "page_size": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 3
        assert data["total_items"] >= 5

    def test_page_2(self, client, db):
        v = _add_vendor(db, "Page Vendor2", "food")
        _add_vendor_profile(db, v.id, "cafe")
        for i in range(5):
            _add_menu_item(db, v.id, f"PItem {i}", price=1000)

        resp = client.get("/search", params={"q": "", "page_size": 2, "page": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2


# ── Suggestions ─────────────────────────────────────────────────────────────


class TestSearchSuggestions:
    def test_suggestions_return_vendor_names(self, client, db):
        _add_vendor(db, "Campus Cafe", "food")
        resp = client.get("/search/suggestions", params={"q": "Camp"})
        assert resp.status_code == 200
        data = resp.json()
        assert "Campus Cafe" in data

    def test_suggestions_return_menu_item_names(self, client, db):
        v = _add_vendor(db, "Sug Vendor", "food")
        _add_menu_item(db, v.id, "Chicken Biryani")
        resp = client.get("/search/suggestions", params={"q": "Chicken"})
        assert resp.status_code == 200
        data = resp.json()
        assert "Chicken Biryani" in data

    def test_suggestions_return_stationery_names(self, client, db):
        v = _add_vendor(db, "Sug Stat Vendor", "stationery")
        _add_stationery_service(db, v.id, "Spiral Binding")
        resp = client.get("/search/suggestions", params={"q": "Spiral"})
        assert resp.status_code == 200
        data = resp.json()
        assert "Spiral Binding" in data

    def test_suggestions_limit(self, client, db):
        v = _add_vendor(db, "Limit Vendor A", "food")
        _add_menu_item(db, v.id, "Limit Food B")
        v2 = _add_vendor(db, "Limit Vendor C", "food")
        _add_menu_item(db, v2.id, "Limit Food D")

        resp = client.get("/search/suggestions", params={"q": "Limit", "limit": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 2

    def test_suggestions_missing_q_returns_422(self, client, db):
        resp = client.get("/search/suggestions")
        assert resp.status_code == 422


# ── Category filter ─────────────────────────────────────────────────────────


class TestSearchCategoryFilter:
    def test_category_filter(self, client, db):
        v1 = _add_vendor(db, "Cafe Vendor", "food")
        _add_vendor_profile(db, v1.id, "cafe", rating=4.5)
        _add_menu_item(db, v1.id, "Latte")

        v2 = _add_vendor(db, "FastFood Vendor", "food")
        _add_vendor_profile(db, v2.id, "fast food", rating=4.0)
        _add_menu_item(db, v2.id, "Burger")

        resp = client.get("/search", params={"q": "", "category": "cafe"})
        assert resp.status_code == 200
        data = resp.json()
        for v in data["vendors"]:
            assert v["category"] == "cafe"
        for it in data["items"]:
            assert it["vendor_category"] == "cafe"


# ── Combined filters ────────────────────────────────────────────────────────


class TestSearchCombinedFilters:
    def test_type_and_price_filter(self, client, db):
        v = _add_vendor(db, "Combined Food", "food")
        _add_vendor_profile(db, v.id, "cafe")
        _add_menu_item(db, v.id, "Cheap Sandwich", price=2000)
        _add_menu_item(db, v.id, "Pricy Steak", price=15000)

        vs = _add_vendor(db, "Combined Stat", "stationery")
        _add_vendor_profile(db, vs.id, "printing")
        _add_stationery_service(db, vs.id, "Color Print", 1000)

        resp = client.get("/search", params={"q": "", "type": "food", "price_max": 5000})
        assert resp.status_code == 200
        data = resp.json()
        for it in data["items"]:
            assert it["item_type"] == "food"
            assert it["price"] <= 5000

    def test_rating_and_category(self, client, db):
        v1 = _add_vendor(db, "Good Cafe", "food")
        _add_vendor_profile(db, v1.id, "cafe", rating=4.8)
        _add_menu_item(db, v1.id, "Good Latte")

        v2 = _add_vendor(db, "Bad Cafe", "food")
        _add_vendor_profile(db, v2.id, "cafe", rating=2.0)
        _add_menu_item(db, v2.id, "Bad Latte")

        resp = client.get("/search", params={"q": "", "min_rating": 4.0, "category": "cafe"})
        assert resp.status_code == 200
        data = resp.json()
        for it in data["items"]:
            assert it["vendor_rating"] >= 4.0
            assert it["vendor_category"] == "cafe"
