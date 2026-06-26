from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.modules.menu.model import MenuItem, Inventory
from app.modules.stationery.service_model import StationeryService
from app.modules.menu.schemas import (
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
    InventoryCreate, InventoryUpdate, InventoryResponse,
    StationeryServiceCreate, StationeryServiceUpdate, StationeryServiceResponse
)
from app.core.time_utils import utcnow_naive


# ══════════════════════════════════════════════════════════════════════════════
# Menu Item Services
# ══════════════════════════════════════════════════════════════════════════════


def create_menu_item(db: Session, vendor_id: int, data: MenuItemCreate) -> MenuItem:
    """Create a new menu item."""
    item = MenuItem(
        vendor_id=vendor_id,
        name=data.name,
        description=data.description,
        price=data.price,
        image_url=data.image_url,
        category=data.category,
        prep_time_minutes=data.prep_time_minutes,
        available_quantity=data.available_quantity or 0,
        is_available=True
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    
    # Create inventory record if stock tracking is enabled
    if data.category == "food" and data.available_quantity is not None:
        inventory = Inventory(
            menu_item_id=item.id,
            current_stock=data.available_quantity,
            auto_disable=True
        )
        db.add(inventory)
        db.commit()
    
    return item


def get_menu_item(db: Session, item_id: int) -> Optional[MenuItem]:
    """Get a single menu item by ID."""
    return db.query(MenuItem).filter(MenuItem.id == item_id).first()


def get_menu_items_by_vendor(
    db: Session,
    vendor_id: int,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    category: Optional[str] = None,
    available_only: bool = False
) -> Dict[str, Any]:
    """Get paginated menu items for a vendor with optional filters."""
    query = db.query(MenuItem).filter(MenuItem.vendor_id == vendor_id)
    
    if search:
        query = query.filter(MenuItem.name.ilike(f"%{search}%"))
    
    if category:
        query = query.filter(MenuItem.category == category)
    
    if available_only:
        query = query.filter(MenuItem.is_available == True)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.order_by(desc(MenuItem.created_at))\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


def update_menu_item(db: Session, item_id: int, vendor_id: int, data: MenuItemUpdate) -> Optional[MenuItem]:
    """Update a menu item."""
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.vendor_id == vendor_id
    ).first()
    
    if not item:
        return None
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = utcnow_naive()
    
    # Auto-disable if out of stock and auto_disable is enabled
    if item.inventory and item.inventory.auto_disable:
        if item.available_quantity is not None and item.available_quantity <= 0:
            item.is_available = False
        elif item.inventory.current_stock <= 0:
            item.is_available = False
    
    db.commit()
    db.refresh(item)
    return item


def delete_menu_item(db: Session, item_id: int, vendor_id: int) -> bool:
    """Delete a menu item."""
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.vendor_id == vendor_id
    ).first()
    
    if not item:
        return False
    
    db.delete(item)
    db.commit()
    return True


def toggle_menu_item(db: Session, item_id: int, vendor_id: int) -> Optional[MenuItem]:
    """Enable/disable a menu item."""
    item = db.query(MenuItem).filter(
        MenuItem.id == item_id,
        MenuItem.vendor_id == vendor_id
    ).first()
    
    if not item:
        return None
    
    item.is_available = not item.is_available
    item.updated_at = utcnow_naive()
    
    db.commit()
    db.refresh(item)
    return item


# ══════════════════════════════════════════════════════════════════════════════
# Inventory Services
# ══════════════════════════════════════════════════════════════════════════════


def create_inventory(db: Session, vendor_id: int, data: InventoryCreate) -> Inventory:
    """Create inventory record for a menu item."""
    # Verify menu item belongs to vendor
    item = db.query(MenuItem).filter(
        MenuItem.id == data.menu_item_id,
        MenuItem.vendor_id == vendor_id
    ).first()
    
    if not item:
        raise ValueError("Menu item not found or does not belong to vendor")
    
    # Check if inventory already exists
    existing = db.query(Inventory).filter(Inventory.menu_item_id == data.menu_item_id).first()
    if existing:
        raise ValueError("Inventory record already exists for this item")
    
    inventory = Inventory(
        menu_item_id=data.menu_item_id,
        current_stock=data.current_stock,
        low_stock_threshold=data.low_stock_threshold,
        auto_disable=data.auto_disable
    )
    
    # Update menu item quantity
    item.available_quantity = data.current_stock
    
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory


def get_inventory(db: Session, inventory_id: int) -> Optional[Inventory]:
    """Get inventory by ID."""
    return db.query(Inventory).filter(Inventory.id == inventory_id).first()


def get_inventory_by_item(db: Session, menu_item_id: int) -> Optional[Inventory]:
    """Get inventory by menu item ID."""
    return db.query(Inventory).filter(Inventory.menu_item_id == menu_item_id).first()


def get_all_inventory(
    db: Session,
    vendor_id: int,
    page: int = 1,
    page_size: int = 20,
    low_stock_only: bool = False
) -> Dict[str, Any]:
    """Get all inventory items for a vendor."""
    query = db.query(Inventory).join(MenuItem).filter(MenuItem.vendor_id == vendor_id)
    
    if low_stock_only:
        query = query.filter(Inventory.current_stock <= Inventory.low_stock_threshold)
    
    total = query.count()
    
    items = query.order_by(Inventory.updated_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


def update_inventory(db: Session, inventory_id: int, vendor_id: int, data: InventoryUpdate) -> Optional[Inventory]:
    """Update inventory."""
    inventory = db.query(Inventory).join(MenuItem).filter(
        Inventory.id == inventory_id,
        MenuItem.vendor_id == vendor_id
    ).first()
    
    if not inventory:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inventory, field, value)
    
    # Update menu item quantity
    if data.current_stock is not None:
        inventory.menu_item.available_quantity = data.current_stock
        inventory.last_restocked_at = utcnow_naive()
    
    inventory.updated_at = utcnow_naive()
    
    # Auto-disable if out of stock
    if inventory.auto_disable and inventory.current_stock <= 0:
        inventory.menu_item.is_available = False
    
    db.commit()
    db.refresh(inventory)
    return inventory


def restock_inventory(db: Session, inventory_id: int, vendor_id: int, quantity: int) -> Optional[Inventory]:
    """Restock inventory by adding quantity."""
    inventory = db.query(Inventory).join(MenuItem).filter(
        Inventory.id == inventory_id,
        MenuItem.vendor_id == vendor_id
    ).first()
    
    if not inventory:
        return None
    
    inventory.current_stock += quantity
    inventory.menu_item.available_quantity = inventory.current_stock
    inventory.last_restocked_at = utcnow_naive()
    inventory.updated_at = utcnow_naive()
    
    # Re-enable if it was disabled due to stock
    if inventory.auto_disable and inventory.current_stock > 0:
        inventory.menu_item.is_available = True
    
    db.commit()
    db.refresh(inventory)
    return inventory


def get_low_stock_alerts(db: Session, vendor_id: int) -> List[Dict[str, Any]]:
    """Get items with low stock."""
    inventories = db.query(Inventory).join(MenuItem).filter(
        MenuItem.vendor_id == vendor_id,
        Inventory.current_stock <= Inventory.low_stock_threshold
    ).all()
    
    alerts = []
    for inv in inventories:
        alerts.append({
            "inventory_id": inv.id,
            "menu_item_id": inv.menu_item_id,
            "item_name": inv.menu_item.name,
            "current_stock": inv.current_stock,
            "threshold": inv.low_stock_threshold,
            "is_available": inv.menu_item.is_available,
            "urgency": "critical" if inv.current_stock == 0 else "low"
        })
    
    return alerts


# ══════════════════════════════════════════════════════════════════════════════
# Stationery Service Services
# ══════════════════════════════════════════════════════════════════════════════


def create_stationery_service(db: Session, vendor_id: int, data: StationeryServiceCreate) -> StationeryService:
    """Create a new stationery service."""
    service = StationeryService(
        vendor_id=vendor_id,
        service_type=data.service_type,
        name=data.name,
        description=data.description,
        price_per_page=data.price_per_page,
        max_capacity=data.max_capacity,
        is_available=data.is_available
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def get_stationery_service(db: Session, service_id: int) -> Optional[StationeryService]:
    """Get a stationery service by ID."""
    return db.query(StationeryService).filter(StationeryService.id == service_id).first()


def get_stationery_services_by_vendor(
    db: Session,
    vendor_id: int,
    page: int = 1,
    page_size: int = 20,
    service_type: Optional[str] = None
) -> Dict[str, Any]:
    """Get paginated stationery services for a vendor."""
    query = db.query(StationeryService).filter(StationeryService.vendor_id == vendor_id)
    
    if service_type:
        query = query.filter(StationeryService.service_type == service_type)
    
    total = query.count()
    
    services = query.order_by(StationeryService.created_at.desc())\
        .offset((page - 1) * page_size)\
        .limit(page_size)\
        .all()
    
    return {
        "items": services,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


def update_stationery_service(
    db: Session,
    service_id: int,
    vendor_id: int,
    data: StationeryServiceUpdate
) -> Optional[StationeryService]:
    """Update a stationery service."""
    service = db.query(StationeryService).filter(
        StationeryService.id == service_id,
        StationeryService.vendor_id == vendor_id
    ).first()
    
    if not service:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    service.updated_at = utcnow_naive()
    
    db.commit()
    db.refresh(service)
    return service


def delete_stationery_service(db: Session, service_id: int, vendor_id: int) -> bool:
    """Delete a stationery service."""
    service = db.query(StationeryService).filter(
        StationeryService.id == service_id,
        StationeryService.vendor_id == vendor_id
    ).first()
    
    if not service:
        return False
    
    db.delete(service)
    db.commit()
    return True


def update_service_load(db: Session, service_id: int, pages: int) -> Optional[StationeryService]:
    """Update the current load of a stationery service."""
    service = db.query(StationeryService).filter(StationeryService.id == service_id).first()
    
    if not service:
        return None
    
    service.current_load += pages
    service.updated_at = utcnow_naive()
    
    # Disable if at capacity
    if service.max_capacity and service.current_load >= service.max_capacity:
        service.is_available = False
    
    db.commit()
    db.refresh(service)
    return service