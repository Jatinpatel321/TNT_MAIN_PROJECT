from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import get_db
from app.core.security import get_current_user, require_role
from app.modules.menu.model import MenuItem, Inventory
from app.modules.stationery.service_model import StationeryService
from app.modules.menu.schemas import (
    MenuItemCreate, MenuItemUpdate, MenuItemResponse,
    InventoryCreate, InventoryUpdate, InventoryResponse,
    StationeryServiceCreate, StationeryServiceUpdate, StationeryServiceResponse,
    PaginatedResponse
)
from app.modules.menu.service import (
    create_menu_item, get_menu_item, get_menu_items_by_vendor, update_menu_item,
    delete_menu_item, toggle_menu_item,
    create_inventory, get_inventory, get_inventory_by_item, get_all_inventory,
    update_inventory, restock_inventory, get_low_stock_alerts,
    create_stationery_service, get_stationery_service, get_stationery_services_by_vendor,
    update_stationery_service, delete_stationery_service, update_service_load
)
from app.modules.users.model import User, UserRole

router = APIRouter(prefix="/menu", tags=["Menu & Inventory"])


# ══════════════════════════════════════════════════════════════════════════════
# Menu Item Endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/items", response_model=MenuItemResponse)
def add_menu_item(
    name: str = Form(...),
    price: int = Form(...),
    description: str | None = Form(None),
    category: str = Form("food"),
    prep_time_minutes: int | None = Form(None),
    available_quantity: int | None = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Add a new menu item (food or stationery)."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not db_user.is_approved:
        raise HTTPException(status_code=403, detail="Vendor not approved")
    
    # Save image if provided
    image_url = None
    if image:
        from app.core.file_upload import save_menu_image
        image_url = save_menu_image(image)
    
    data = MenuItemCreate(
        name=name,
        description=description,
        price=price,
        category=category,
        prep_time_minutes=prep_time_minutes,
        available_quantity=available_quantity,
        image_url=image_url
    )
    
    item = create_menu_item(db, db_user.id, data)
    return item


@router.get("/items", response_model=PaginatedResponse)
def get_menu_items(
    vendor_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    category: str | None = Query(None),
    available_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get paginated menu items for a vendor with search and filters."""
    result = get_menu_items_by_vendor(
        db, vendor_id, page, page_size, search, category, available_only
    )
    return result


@router.get("/items/{item_id}", response_model=MenuItemResponse)
def get_menu_item_by_id(item_id: int, db: Session = Depends(get_db)):
    """Get a single menu item by ID."""
    item = get_menu_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.put("/items/{item_id}", response_model=MenuItemResponse)
def edit_menu_item(
    item_id: int,
    name: str | None = Form(None),
    price: int | None = Form(None),
    description: str | None = Form(None),
    is_available: bool | None = Form(None),
    prep_time_minutes: int | None = Form(None),
    available_quantity: int | None = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Edit a menu item."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Save image if provided
    image_url = None
    if image:
        from app.core.file_upload import save_menu_image
        image_url = save_menu_image(image)
    
    data = MenuItemUpdate(
        name=name,
        price=price,
        description=description,
        is_available=is_available,
        prep_time_minutes=prep_time_minutes,
        available_quantity=available_quantity,
        image_url=image_url
    )
    
    item = update_menu_item(db, item_id, db_user.id, data)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


@router.delete("/items/{item_id}")
def remove_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Delete a menu item."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = delete_menu_item(db, item_id, db_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return {"message": "Menu item deleted successfully"}


@router.put("/items/{item_id}/toggle", response_model=MenuItemResponse)
def toggle_item_availability(
    item_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Enable/disable a menu item."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    item = toggle_menu_item(db, item_id, db_user.id)
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item


# ══════════════════════════════════════════════════════════════════════════════
# Inventory Endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/inventory", response_model=InventoryResponse)
def create_inventory_record(
    menu_item_id: int = Form(...),
    current_stock: int = Form(...),
    low_stock_threshold: int = Form(10),
    auto_disable: bool = Form(True),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Create inventory record for a menu item."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = InventoryCreate(
        menu_item_id=menu_item_id,
        current_stock=current_stock,
        low_stock_threshold=low_stock_threshold,
        auto_disable=auto_disable
    )
    
    try:
        inventory = create_inventory(db, db_user.id, data)
        return inventory
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/inventory", response_model=PaginatedResponse)
def get_inventory_list(
    vendor_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    low_stock_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all inventory items for a vendor."""
    result = get_all_inventory(db, vendor_id, page, page_size, low_stock_only)
    return result


@router.get("/inventory/{inventory_id}", response_model=InventoryResponse)
def get_inventory_by_id(inventory_id: int, db: Session = Depends(get_db)):
    """Get inventory by ID."""
    inventory = get_inventory(db, inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory


@router.put("/inventory/{inventory_id}", response_model=InventoryResponse)
def update_inventory_record(
    inventory_id: int,
    current_stock: int | None = Form(None),
    low_stock_threshold: int | None = Form(None),
    auto_disable: bool | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Update inventory."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = InventoryUpdate(
        current_stock=current_stock,
        low_stock_threshold=low_stock_threshold,
        auto_disable=auto_disable
    )
    
    inventory = update_inventory(db, inventory_id, db_user.id, data)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory


@router.post("/inventory/{inventory_id}/restock", response_model=InventoryResponse)
def restock_inventory_item(
    inventory_id: int,
    quantity: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Restock inventory by adding quantity."""
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    inventory = restock_inventory(db, inventory_id, db_user.id, quantity)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory


@router.get("/inventory/alerts/low-stock")
def get_low_stock_alert_list(
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Get low stock alerts for the current vendor."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    alerts = get_low_stock_alerts(db, db_user.id)
    return {"alerts": alerts, "count": len(alerts)}


# ══════════════════════════════════════════════════════════════════════════════
# Stationery Service Endpoints
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/stationery", response_model=StationeryServiceResponse)
def add_stationery_service(
    service_type: str = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    price_per_page: int = Form(...),
    max_capacity: int | None = Form(None),
    is_available: bool = Form(True),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Add a new stationery service (xerox, color print, BW print)."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not db_user.is_approved:
        raise HTTPException(status_code=403, detail="Vendor not approved")
    
    data = StationeryServiceCreate(
        service_type=service_type,
        name=name,
        description=description,
        price_per_page=price_per_page,
        max_capacity=max_capacity,
        is_available=is_available
    )
    
    service = create_stationery_service(db, db_user.id, data)
    return service


@router.get("/stationery", response_model=PaginatedResponse)
def get_stationery_services(
    vendor_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service_type: str | None = Query(None),
    db: Session = Depends(get_db)
):
    """Get paginated stationery services for a vendor."""
    result = get_stationery_services_by_vendor(db, vendor_id, page, page_size, service_type)
    return result


@router.get("/stationery/{service_id}", response_model=StationeryServiceResponse)
def get_stationery_service_by_id(service_id: int, db: Session = Depends(get_db)):
    """Get a stationery service by ID."""
    service = get_stationery_service(db, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Stationery service not found")
    return service


@router.put("/stationery/{service_id}", response_model=StationeryServiceResponse)
def edit_stationery_service(
    service_id: int,
    name: str | None = Form(None),
    description: str | None = Form(None),
    price_per_page: int | None = Form(None),
    max_capacity: int | None = Form(None),
    current_load: int | None = Form(None),
    is_available: bool | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Edit a stationery service."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    data = StationeryServiceUpdate(
        name=name,
        description=description,
        price_per_page=price_per_page,
        max_capacity=max_capacity,
        current_load=current_load,
        is_available=is_available
    )
    
    service = update_stationery_service(db, service_id, db_user.id, data)
    if not service:
        raise HTTPException(status_code=404, detail="Stationery service not found")
    return service


@router.delete("/stationery/{service_id}")
def remove_stationery_service(
    service_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor"))
):
    """Delete a stationery service."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = delete_stationery_service(db, service_id, db_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Stationery service not found")
    return {"message": "Stationery service deleted successfully"}


@router.post("/stationery/{service_id}/load", response_model=StationeryServiceResponse)
def update_stationery_load(
    service_id: int,
    pages: int = Form(...),
    db: Session = Depends(get_db)
):
    """Update the current load of a stationery service (called when order is placed)."""
    if pages <= 0:
        raise HTTPException(status_code=400, detail="Pages must be positive")
    
    service = update_service_load(db, service_id, pages)
    if not service:
        raise HTTPException(status_code=404, detail="Stationery service not found")
    return service