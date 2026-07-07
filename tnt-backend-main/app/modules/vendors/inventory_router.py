"""Vendor Inventory Automation API Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.inventory_service import VendorInventoryService

router = APIRouter(prefix="/vendors/inventory", tags=["Vendor Inventory"])


def _resolve_vendor(user: dict, db: Session) -> int:
    """Get vendor user ID from authenticated user."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


@router.get("/dashboard", summary="Get inventory dashboard")
def get_inventory_dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get complete inventory status dashboard with stock levels and alerts."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    return service.get_inventory_dashboard(vendor_id)


@router.get("/low-stock", summary="Detect low stock items")
def get_low_stock(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Find all items with stock below their low-stock threshold."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    return {"low_stock_items": service.detect_low_stock_items(vendor_id)}


@router.get("/out-of-stock", summary="Detect out of stock items")
def get_out_of_stock(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Find and auto-disable out of stock items."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    alerts = service.detect_out_of_stock_items(vendor_id)
    if alerts:
        db.commit()
    return {"out_of_stock_items": alerts}


@router.post("/deduct/{order_id}", summary="Auto deduct stock for order")
def deduct_stock(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Manually trigger stock deduction for an order."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    result = service.auto_deduct_stock(order_id)
    return result


@router.post("/restock/{item_id}", summary="Restock an item")
def restock_item(
    item_id: int,
    quantity: int = Query(..., ge=1, description="Quantity to add"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Restock a menu item and auto re-enable if applicable."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    return service.restock_item(vendor_id, item_id, quantity)


@router.post("/auto-enable", summary="Auto re-enable restocked items")
def auto_enable(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Re-enable items that have been restocked above threshold."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    reenabled = service.auto_enable_items(vendor_id)
    if reenabled:
        db.commit()
    return {"reenabled_items": reenabled}


@router.post("/send-alerts", summary="Send inventory alert notifications")
def send_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send inventory alert notifications to vendor."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorInventoryService(db)
    return service.send_inventory_alerts(vendor_id)