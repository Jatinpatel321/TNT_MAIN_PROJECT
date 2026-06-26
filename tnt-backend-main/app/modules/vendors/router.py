from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.security import get_current_user
from app.core.time_utils import utcnow_naive
from app.modules.menu.image_utils import menu_image_for
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.orders.service import update_order_status
from app.modules.notifications.model import Notification
from app.modules.notifications.router import send_notification
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.slots.service import generate_stationery_slots
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole
from app.modules.vendors.inventory_service import VendorInventoryService
from app.modules.vendors.model import Vendor, VendorStaff
from app.modules.vendors.profile_models import VendorProfile
from app.modules.vendors.schemas import (
    VendorMenuItemResponse,
    VendorResponse,
    VendorSlotResponse,
    VendorSlotListResponse,
)

router = APIRouter(prefix="/vendors", tags=["Vendors"])

# ---------------------------------------------------------------------------
# Curated image map — resolved at runtime so no file I/O is needed.
# Keys mirror the vendor name slugs / menu item names produced by the seed.
# ---------------------------------------------------------------------------
_VENDOR_IMAGES: dict[str, dict[str, str]] = {
    "campus cafe": {
        "logo": "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1445116572660-236099ec97a0?auto=format&fit=crop&w=900&q=70",
    },
    "burger hub": {
        "logo": "https://images.unsplash.com/photo-1586190848861-99c8a3da726c?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1561758033-d89a9ad46330?auto=format&fit=crop&w=900&q=70",
    },
    "pizza station": {
        "logo": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=900&q=70",
    },
    "spice corner": {
        "logo": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1668236543090-d2f896914365?auto=format&fit=crop&w=900&q=70",
    },
    "green bowl": {
        "logo": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=900&q=70",
    },
    "xerox point": {
        "logo": "https://images.unsplash.com/photo-1563321703-a12f71694f42?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1562564055-71e051d33c19?auto=format&fit=crop&w=900&q=70",
    },
    "print hub": {
        "logo": "https://images.unsplash.com/photo-1562564055-71e051d33c19?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?auto=format&fit=crop&w=900&q=70",
    },
    "campus stationery": {
        "logo": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?auto=format&fit=crop&w=400&q=70",
        "cover": "https://images.unsplash.com/photo-1586075010923-2dd450853842?auto=format&fit=crop&w=900&q=70",
    },
}


def _vendor_images(name: str | None, vendor_type: str = "food") -> dict[str, str | None]:
    """Return logo_url and cover_image for a vendor by name with fallbacks."""
    key = (name or "").lower().strip()
    imgs = _VENDOR_IMAGES.get(key, {})
    if imgs:
        return {"logo_url": imgs.get("logo"), "cover_image": imgs.get("cover")}

    hint = "printing" if vendor_type == "stationery" else "campus cafe"
    query = key or "campus vendor"
    fallback = f"https://source.unsplash.com/800x600/?{hint},{query}"
    return {"logo_url": fallback, "cover_image": fallback}


def _vendor_profile(vendor_id: int, db: Session) -> dict[str, Any]:
    """Pull extra profile fields from vendor_profiles if the table exists."""
    try:
        row = db.execute(
            text("SELECT category, description, rating, location FROM vendor_profiles WHERE vendor_id = :vid"),
            {"vid": vendor_id},
        ).fetchone()
        if row:
            return {
                "category": row[0],
                "description": row[1],
                "rating": float(row[2]),
                "location": row[3],
            }
    except Exception:
        pass
    return {"category": None, "description": None, "rating": 4.5, "location": None}


def _vendor_load_summary(vendor_id: int, db: Session) -> tuple[str, bool]:
    slots = db.query(Slot).filter(Slot.vendor_id == vendor_id).all()
    if not slots:
        return "LOW", False

    total_capacity = sum(slot.max_orders for slot in slots)
    total_orders = sum(slot.current_orders for slot in slots)
    load_label = get_load_label(total_orders, total_capacity)
    express_eligible = is_express_pickup_eligible(total_orders, total_capacity)
    return load_label, express_eligible


def _build_vendor_response(vendor: User, db: Session, vendor_type: str = "food") -> dict[str, Any]:
    live_load_label, express_pickup_eligible = _vendor_load_summary(vendor.id, db)
    imgs = _vendor_images(vendor.name, vendor.vendor_type or vendor_type)
    profile = _vendor_profile(vendor.id, db)
    return {
        "id": vendor.id,
        "name": vendor.name,
        "description": profile["description"] or f"{vendor.name} — campus vendor",
        "vendor_type": vendor_type,
        "is_approved": vendor.is_approved,
        "phone": vendor.phone,
        "is_open": True,
        "logo_url": imgs["logo_url"],
        "cover_image": imgs["cover_image"],
        "rating": profile["rating"],
        "category": profile["category"],
        "location": profile["location"],
        "live_load_label": live_load_label,
        "express_pickup_eligible": express_pickup_eligible,
    }


# ── Vendor Public Endpoints ──────────────────────────────────────────────────


@router.get("/")
def get_vendors(
    type: str = "food",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all vendors by type (food or stationery) with pagination.
    """
    vendor_type = type.strip().lower()
    if vendor_type not in {"food", "stationery"}:
        raise HTTPException(status_code=400, detail="Invalid vendor type")

    vendors_query = db.query(User).filter(
        User.role == UserRole.VENDOR,
        User.is_approved == True,
        User.is_active == True,
    )

    if vendor_type == "food":
        food_vendor_ids = db.query(MenuItem.vendor_id).filter(MenuItem.is_available == True).distinct()
        vendors_query = vendors_query.filter(User.id.in_(food_vendor_ids))
    else:
        stationery_vendor_ids = (
            db.query(StationeryService.vendor_id)
            .filter(StationeryService.is_available == True)
            .distinct()
        )
        vendors_query = vendors_query.filter(User.id.in_(stationery_vendor_ids))

    total = vendors_query.count()
    vendors = vendors_query.order_by(User.id).offset(offset).limit(limit).all()

    response = []
    for vendor in vendors:
        data = _build_vendor_response(vendor, db, vendor_type)
        response.append(data)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": response,
    }


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    """
    Get single vendor details
    """
    vendor = db.query(User).filter(
        User.id == vendor_id,
        User.role == UserRole.VENDOR,
        User.is_approved == True,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return _build_vendor_response(vendor, db, "food")


@router.get("/{vendor_id}/menu", response_model=list[VendorMenuItemResponse])
def get_vendor_menu(vendor_id: int, db: Session = Depends(get_db)):
    """
    Get vendor menu items
    """
    vendor = db.query(User).filter(
        User.id == vendor_id,
        User.role == UserRole.VENDOR,
        User.is_approved == True,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    menu_items = db.query(MenuItem).filter(
        MenuItem.vendor_id == vendor_id,
        MenuItem.is_available == True,
    ).all()

    payload: list[dict[str, Any]] = []
    dirty_items: list[MenuItem] = []

    for item in menu_items:
        img_url = item.image_url
        if not img_url:
            img_url = menu_image_for(item.name, vendor.vendor_type or "food")
            item.image_url = img_url
            dirty_items.append(item)

        payload.append(
            {
                "id": item.id,
                "vendor_id": item.vendor_id,
                "name": item.name,
                "description": item.description or f"Delicious {item.name}",
                "price": item.price,
                "image_url": img_url,
                "is_available": item.is_available,
            }
        )

    if dirty_items:
        db.commit()

    return payload


@router.get("/{vendor_id}/slots", response_model=VendorSlotListResponse)
def get_vendor_slots(vendor_id: int, db: Session = Depends(get_db)):
    """Get vendor pickup slots with AI recommendation data."""
    vendor = db.query(User).filter(
        User.id == vendor_id,
        User.role == UserRole.VENDOR,
        User.is_approved == True,
    ).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    vendor_type = "food"
    is_stationery = db.query(StationeryService).filter(StationeryService.vendor_id == vendor_id).first() is not None
    if is_stationery:
        vendor_type = "stationery"
        generate_stationery_slots(vendor_id, db)

    slots = db.query(Slot).filter(Slot.vendor_id == vendor_id).order_by(Slot.start_time).all()

    # Compute queue size and estimated wait per slot
    prep_time = 1 if vendor_type == "stationery" else 3  # minutes per order
    slot_scores: list[tuple[Slot, float, int, int]] = []
    for slot in slots:
        queue_size = db.query(Order).filter(Order.slot_id == slot.id).count()
        estimated_wait = queue_size * prep_time
        slot_score = estimated_wait + (queue_size * 0.5)
        slot_scores.append((slot, slot_score, queue_size, estimated_wait))

    # Mark best score
    best_score = None if not slot_scores else min(s[1] for s in slot_scores)

    slot_payloads: list[VendorSlotResponse] = []
    for slot, score, queue_size, estimated_wait in slot_scores:
        slot_payloads.append(
            VendorSlotResponse(
                id=slot.id,
                vendor_id=slot.vendor_id,
                start_time=slot.start_time,
                end_time=slot.end_time,
                is_available=slot.status != SlotStatus.FULL and slot.current_orders < slot.max_orders,
                max_orders=slot.max_orders,
                current_orders=slot.current_orders,
                load_label=get_load_label(slot.current_orders, slot.max_orders),
                express_pickup_eligible=is_express_pickup_eligible(slot.current_orders, slot.max_orders),
                estimated_ready_time="5 minutes" if vendor_type == "stationery" else None,
                queue_size=queue_size,
                estimated_wait=estimated_wait,
                is_ai_recommended=best_score is not None and score == best_score,
            )
        )

    return VendorSlotListResponse(
        estimated_ready_time="5 minutes" if vendor_type == "stationery" else None,
        slots=slot_payloads,
    )


# ── Vendor Order Management ─────────────────────────────────────────────────


@router.get("/orders", tags=["Vendor Orders"])
def get_vendor_orders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get all orders for the authenticated vendor with metrics."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    orders = db.query(Order).filter(Order.vendor_id == db_user.id).order_by(Order.created_at.desc()).all()

    # Calculate metrics
    today = datetime.utcnow().date()
    orders_today = sum(1 for o in orders if o.created_at.date() == today)
    pending = sum(1 for o in orders if o.status == OrderStatus.PLACED)
    preparing = sum(1 for o in orders if o.status == OrderStatus.PREPARING)
    ready = sum(1 for o in orders if o.status == OrderStatus.READY)
    completed = sum(1 for o in orders if o.status in (OrderStatus.PICKED, OrderStatus.COMPLETED))
    cancelled = sum(1 for o in orders if o.status == OrderStatus.CANCELLED)

    return {
        "orders": [
            {
                "id": o.id,
                "user_id": o.user_id,
                "slot_id": o.slot_id,
                "status": o.status.value,
                "total_amount": o.total_amount,
                "created_at": o.created_at.isoformat(),
                "qr_code": o.qr_code,
                "fraud_flag": o.fraud_flag,
            }
            for o in orders
        ],
        "metrics": {
            "orders_today": orders_today,
            "pending": pending,
            "preparing": preparing,
            "ready": ready,
            "completed": completed,
            "cancelled": cancelled,
        },
    }


@router.get("/orders/current-slot", tags=["Vendor Orders"])
def get_current_slot_orders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get orders for the current active slot."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = utcnow_naive()
    current_slot = db.query(Slot).filter(
        Slot.vendor_id == db_user.id,
        Slot.start_time <= now,
        Slot.end_time >= now,
    ).first()

    if not current_slot:
        return {"orders": [], "slot": None}

    orders = db.query(Order).filter(Order.slot_id == current_slot.id).order_by(Order.created_at).all()

    return {
        "slot": {
            "id": current_slot.id,
            "start_time": current_slot.start_time.isoformat(),
            "end_time": current_slot.end_time.isoformat(),
        },
        "orders": [
            {
                "id": o.id,
                "user_id": o.user_id,
                "status": o.status.value,
                "total_amount": o.total_amount,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ],
    }


@router.get("/orders/upcoming", tags=["Vendor Orders"])
def get_upcoming_orders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get orders for upcoming slots."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = utcnow_naive()
    upcoming_slots = db.query(Slot).filter(
        Slot.vendor_id == db_user.id,
        Slot.start_time > now,
    ).order_by(Slot.start_time).limit(5).all()

    result = []
    for slot in upcoming_slots:
        orders = db.query(Order).filter(Order.slot_id == slot.id).order_by(Order.created_at).all()
        result.append({
            "slot": {
                "id": slot.id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
            },
            "orders": [
                {
                    "id": o.id,
                    "user_id": o.user_id,
                    "status": o.status.value,
                    "total_amount": o.total_amount,
                }
                for o in orders
            ],
        })

    return {"upcoming": result}


# ── Order Status Transitions with Inventory Integration ──────────────────────


@router.put("/orders/{order_id}/accept", tags=["Vendor Orders"])
def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Accept an order (PLACED -> CONFIRMED)."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PLACED:
        raise HTTPException(status_code=400, detail="Order cannot be accepted in current status")

    update_order_status(order, OrderStatus.CONFIRMED, "vendor", db)

    # Trigger notification
    try:
        send_notification(
            user_id=order.user_id,
            title="Order Accepted",
            message=f"Your order #{order.id} has been accepted by the vendor",
            notification_type="order_update",
        )
    except Exception:
        pass

    return {"message": "Order accepted", "order_id": order.id, "status": order.status.value}


@router.put("/orders/{order_id}/prepare", tags=["Vendor Orders"])
def prepare_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Start preparing an order (CONFIRMED -> PREPARING).
    Auto-deducts inventory stock upon preparation.
    """
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Order cannot be prepared in current status")

    update_order_status(order, OrderStatus.PREPARING, "vendor", db)

    # Auto-deduct stock on prepare
    try:
        inv_service = VendorInventoryService(db)
        deduction_result = inv_service.deduct_stock_on_prepare(order_id)
    except Exception:
        deduction_result = {"success": False, "error": "Stock deduction failed"}

    try:
        send_notification(
            user_id=order.user_id,
            title="Order Being Prepared",
            message=f"Your order #{order.id} is being prepared",
            notification_type="order_update",
        )
    except Exception:
        pass

    return {
        "message": "Order preparation started",
        "order_id": order.id,
        "status": order.status.value,
        "inventory_deduction": deduction_result,
    }


@router.put("/orders/{order_id}/ready", tags=["Vendor Orders"])
def ready_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Mark order as ready (PREPARING -> READY)."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PREPARING:
        raise HTTPException(status_code=400, detail="Order cannot be marked ready in current status")

    update_order_status(order, OrderStatus.READY, "vendor", db)

    try:
        send_notification(
            user_id=order.user_id,
            title="Order Ready!",
            message=f"Your order #{order.id} is ready for pickup",
            notification_type="order_ready",
        )
    except Exception:
        pass

    return {"message": "Order marked as ready", "order_id": order.id, "status": order.status.value}


@router.put("/orders/{order_id}/complete", tags=["Vendor Orders"])
def complete_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Complete an order (READY -> PICKED)."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    order = db.query(Order).filter(Order.id == order_id, Order.vendor_id == db_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.READY:
        raise HTTPException(status_code=400, detail="Order cannot be completed in current status")

    update_order_status(order, OrderStatus.PICKED, "vendor", db)

    try:
        send_notification(
            user_id=order.user_id,
            title="Order Completed",
            message=f"Your order #{order.id} has been picked up",
            notification_type="order_complete",
        )
    except Exception:
        pass

    return {"message": "Order completed", "order_id": order.id, "status": order.status.value}