"""Tests for Menu & Inventory Module.

Covers:
- Menu item CRUD
- Inventory management
- Stationery services
- Low stock alerts
- Pagination and search
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.modules.users.model import User, UserRole
from app.modules.menu.model import MenuItem, Inventory
from app.modules.stationery.service_model import StationeryService
from app.modules.menu.schemas import (
    MenuItemCreate, MenuItemUpdate,
    InventoryCreate, InventoryUpdate,
    StationeryServiceCreate, StationeryServiceUpdate
)
from app.modules.menu.service import (
    create_menu_item, get_menu_item, get_menu_items_by_vendor, update_menu_item,
    delete_menu_item, toggle_menu_item,
    create_inventory, get_inventory, get_all_inventory,
    update_inventory, restock_inventory, get_low_stock_alerts,
    create_stationery_service, get_stationery_services_by_vendor,
    update_stationery_service, delete_stationery_service, get_stationery_service
)

# Ensure all models are imported
import app.database.init_db  # noqa: F401

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def vendor(db: Session) -> User:
    user = User(phone="+919999999999", role=UserRole.VENDOR, vendor_type="food", is_approved=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def stationery_vendor(db: Session) -> User:
    user = User(phone="+919888888888", role=UserRole.VENDOR, vendor_type="stationery", is_approved=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ══════════════════════════════════════════════════════════════════════════════
# Menu Item Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestMenuItems:
    def test_create_menu_item(self, db: Session, vendor: User):
        data = MenuItemCreate(
            name="Test Item",
            description="Test description",
            price=15000,
            category="food",
            prep_time_minutes=15,
            available_quantity=50
        )
        item = create_menu_item(db, vendor.id, data)
        assert item.id is not None
        assert item.name == "Test Item"
        assert item.price == 15000
        assert item.is_available is True
        assert item.category == "food"

    def test_get_menu_item(self, db: Session, vendor: User):
        data = MenuItemCreate(name="Test", price=1000, category="food")
        item = create_menu_item(db, vendor.id, data)
        fetched = get_menu_item(db, item.id)
        assert fetched is not None
        assert fetched.name == "Test"

    def test_get_menu_items_by_vendor(self, db: Session, vendor: User):
        create_menu_item(db, vendor.id, MenuItemCreate(name="Item 1", price=1000, category="food"))
        create_menu_item(db, vendor.id, MenuItemCreate(name="Item 2", price=2000, category="food"))
        
        result = get_menu_items_by_vendor(db, vendor.id)
        assert len(result["items"]) == 2
        assert result["total"] == 2

    def test_update_menu_item(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Old Name", price=1000, category="food"))
        updated = update_menu_item(db, item.id, vendor.id, MenuItemUpdate(name="New Name", price=2000))
        assert updated.name == "New Name"
        assert updated.price == 2000

    def test_toggle_menu_item(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Test", price=1000, category="food"))
        toggled = toggle_menu_item(db, item.id, vendor.id)
        assert toggled.is_available is False
        
        toggled_again = toggle_menu_item(db, item.id, vendor.id)
        assert toggled_again.is_available is True

    def test_delete_menu_item(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Test", price=1000, category="food"))
        result = delete_menu_item(db, item.id, vendor.id)
        assert result is True
        
        fetched = get_menu_item(db, item.id)
        assert fetched is None

    def test_search_menu_items(self, db: Session, vendor: User):
        create_menu_item(db, vendor.id, MenuItemCreate(name="Chicken Biryani", price=15000, category="food"))
        create_menu_item(db, vendor.id, MenuItemCreate(name="Veg Pulao", price=12000, category="food"))
        
        result = get_menu_items_by_vendor(db, vendor.id, search="Chicken")
        assert len(result["items"]) == 1
        assert result["items"][0].name == "Chicken Biryani"

    def test_pagination(self, db: Session, vendor: User):
        for i in range(25):
            create_menu_item(db, vendor.id, MenuItemCreate(name=f"Item {i}", price=1000, category="food"))
        
        result = get_menu_items_by_vendor(db, vendor.id, page=1, page_size=10)
        assert len(result["items"]) == 10
        assert result["total"] == 25
        assert result["total_pages"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# Inventory Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestInventory:
    def test_create_inventory(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Test", price=1000, category="food"))
        inv_data = InventoryCreate(menu_item_id=item.id, current_stock=50, low_stock_threshold=10)
        inventory = create_inventory(db, vendor.id, inv_data)
        assert inventory.current_stock == 50
        assert inventory.low_stock_threshold == 10

    def test_update_inventory(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Test", price=1000, category="food"))
        inv = create_inventory(db, vendor.id, InventoryCreate(menu_item_id=item.id, current_stock=50))
        
        updated = update_inventory(db, inv.id, vendor.id, InventoryUpdate(current_stock=75))
        assert updated.current_stock == 75
        assert updated.menu_item.available_quantity == 75

    def test_restock_inventory(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Test", price=1000, category="food"))
        inv = create_inventory(db, vendor.id, InventoryCreate(menu_item_id=item.id, current_stock=50))
        
        restocked = restock_inventory(db, inv.id, vendor.id, 25)
        assert restocked.current_stock == 75
        assert restocked.menu_item.is_available is True

    def test_auto_disable_out_of_stock(self, db: Session, vendor: User):
        item = create_menu_item(db, vendor.id, MenuItemCreate(name="Test", price=1000, category="food"))
        inv = create_inventory(db, vendor.id, InventoryCreate(menu_item_id=item.id, current_stock=50, auto_disable=True))
        
        # Reduce stock to 0
        update_inventory(db, inv.id, vendor.id, InventoryUpdate(current_stock=0))
        assert item.is_available is False

    def test_low_stock_alerts(self, db: Session, vendor: User):
        item1 = create_menu_item(db, vendor.id, MenuItemCreate(name="Low Stock", price=1000, category="food"))
        item2 = create_menu_item(db, vendor.id, MenuItemCreate(name="Out of Stock", price=1000, category="food"))
        
        create_inventory(db, vendor.id, InventoryCreate(menu_item_id=item1.id, current_stock=5, low_stock_threshold=10))
        create_inventory(db, vendor.id, InventoryCreate(menu_item_id=item2.id, current_stock=0, low_stock_threshold=10))
        
        alerts = get_low_stock_alerts(db, vendor.id)
        assert len(alerts) == 2
        assert any(a["urgency"] == "critical" for a in alerts)


# ══════════════════════════════════════════════════════════════════════════════
# Stationery Service Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestStationeryServices:
    def test_create_stationery_service(self, db: Session, stationery_vendor: User):
        data = StationeryServiceCreate(
            service_type="xerox",
            name="Xerox Service",
            price_per_page=500,
            max_capacity=1000
        )
        service = create_stationery_service(db, stationery_vendor.id, data)
        assert service.id is not None
        assert service.service_type == "xerox"
        assert service.max_capacity == 1000

    def test_get_stationery_services(self, db: Session, stationery_vendor: User):
        create_stationery_service(db, stationery_vendor.id, StationeryServiceCreate(
            service_type="bw_print", name="BW Print", price_per_page=300
        ))
        create_stationery_service(db, stationery_vendor.id, StationeryServiceCreate(
            service_type="color_print", name="Color Print", price_per_page=500
        ))
        
        result = get_stationery_services_by_vendor(db, stationery_vendor.id)
        assert len(result["items"]) == 2

    def test_update_stationery_service(self, db: Session, stationery_vendor: User):
        service = create_stationery_service(db, stationery_vendor.id, StationeryServiceCreate(
            service_type="xerox", name="Xerox", price_per_page=500
        ))
        
        updated = update_stationery_service(db, service.id, stationery_vendor.id, 
            StationeryServiceUpdate(price_per_page=600, max_capacity=2000))
        assert updated.price_per_page == 600
        assert updated.max_capacity == 2000

    def test_delete_stationery_service(self, db: Session, stationery_vendor: User):
        service = create_stationery_service(db, stationery_vendor.id, StationeryServiceCreate(
            service_type="xerox", name="Xerox", price_per_page=500
        ))
        
        result = delete_stationery_service(db, service.id, stationery_vendor.id)
        assert result is True
        
        fetched = get_stationery_service(db, service.id)
        assert fetched is None