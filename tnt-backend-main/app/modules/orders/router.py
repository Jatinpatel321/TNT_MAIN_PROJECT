from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user, require_role
from app.modules.orders import order_service
from app.modules.orders.history_schemas import OrderHistoryResponse
from app.modules.orders.item_schemas import OrderItemCreate
from app.modules.orders.schemas import OrderResponse

router = APIRouter(prefix="/orders", tags=["Orders"])


# 🧾 PLACE ORDER (WITH ITEMS)
@router.post("/{slot_id}")
def place_order(
    slot_id: int,
    items: list[OrderItemCreate],
    idempotency_key: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    return order_service.place_order(user, slot_id, items, idempotency_key, db)


# 👤 STUDENT — MY ORDERS
@router.get("/my")
def my_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    from app.modules.orders.model import Order
    from app.modules.users.model import User as UserModel
    db_user = db.query(UserModel).filter(UserModel.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    q = db.query(Order).filter(Order.user_id == db_user.id)
    total = q.count()
    orders = q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [order_service._order_to_response(o, db) for o in orders],
    }


#  VENDOR — ANALYTICS DASHBOARD
@router.get("/vendor/analytics")
def vendor_analytics(
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
) -> dict[str, Any]:
    """Return aggregated order analytics for the authenticated vendor.

    Includes total/pending/confirmed/ready/completed/cancelled counts,
    revenue, completion rate, average confirmation latency, and peak
    hour/day breakdowns.
    """
    return order_service.get_vendor_analytics(user, db)


# 🧑‍🍳 VENDOR — INCOMING ORDERS
@router.get("/vendor", response_model=list[OrderResponse])
def vendor_orders(db: Session = Depends(get_db), user=Depends(require_role("vendor"))) -> list[OrderResponse]:
    return order_service.get_vendor_orders(user, db)


# ✅ VENDOR — CONFIRM ORDER
@router.post("/{order_id}/confirm")
def confirm_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
) -> dict[str, Any]:
    return order_service.confirm_order(user, order_id, db)


# ✅ VENDOR — MARK ORDER PREPARING
@router.post("/{order_id}/preparing")
def preparing_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
) -> dict[str, Any]:
    return order_service.mark_order_preparing(user, order_id, db)


# ✅ VENDOR — MARK ORDER READY
@router.post("/{order_id}/ready")
def ready_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
) -> dict[str, Any]:
    return order_service.mark_order_ready(user, order_id, db)


# ❌ STUDENT — CANCEL ORDER
@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    return order_service.cancel_order(user, order_id, db)


# 🕒 ORDER TIMELINE
@router.get("/{order_id}/timeline", response_model=list[OrderHistoryResponse])
def order_timeline(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[OrderHistoryResponse]:
    return order_service.get_order_timeline(user, order_id, db)


@router.post("/{order_id}/reorder")
def reorder_order(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    return order_service.reorder(user, order_id, db)


@router.get("/{order_id}/eta")
def order_eta(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    return order_service.get_order_eta(user, order_id, db)


# 🧾 VENDOR — ORDER DETAILS
@router.get("/vendor/{order_id}")
def vendor_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
) -> dict[str, Any]:
    return order_service.get_vendor_order_detail(user, order_id, db)


# 📱 QR PICKUP ENDPOINTS

@router.post("/{order_id}/qr", response_model=dict)
def generate_qr_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate QR code for order pickup."""
    return order_service.generate_order_qr(order_id, db)


@router.post("/qr/pickup/confirm", response_model=dict)
@router.post("/qr/confirm", response_model=dict)
def confirm_pickup_endpoint(
    qr_code: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    """Confirm pickup using QR code."""
    return order_service.confirm_qr_pickup(user, qr_code, db)


@router.get("/qr/{qr_code}", response_model=dict)
def get_order_by_qr_endpoint(
    qr_code: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    """Get order details by QR code for vendor verification."""
    return order_service.get_order_by_qr_code(user, qr_code, db)


# 📋 ORDERS BY USER ID — must be registered LAST so static paths like /vendor,
# /my, /vendor/analytics, /qr/... take precedence over the dynamic {user_id} param.
@router.get("/{user_id}", response_model=list[OrderResponse], summary="Get orders for a specific user")
def orders_by_user_id(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[OrderResponse]:
    """Return all orders for *user_id*, newest-first, enriched with items and vendor name.

    Students may only query their own orders.  Vendors and admins may query
    any user (e.g. to inspect customer history).
    """
    from app.modules.menu.model import MenuItem
    from app.modules.orders.model import Order, OrderItem
    from app.modules.users.model import User as UserModel

    db_caller = db.query(UserModel).filter(UserModel.phone == user["phone"]).first()
    if not db_caller:
        raise HTTPException(status_code=404, detail="Authenticated user not found")

    allowed_roles = {"vendor", "admin", "superadmin"}
    caller_role = db_caller.role.value if hasattr(db_caller.role, "value") else str(db_caller.role)
    if db_caller.id != user_id and caller_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Cannot view another user's orders")

    target = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    orders = (
        db.query(Order)
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )

    # Enrich each order with vendor name and items
    result = []
    for order in orders:
        vendor = db.query(UserModel).filter(UserModel.id == order.vendor_id).first()
        vendor_name = vendor.name if vendor else f"Vendor #{order.vendor_id}"

        order_items_rows = (
            db.query(OrderItem)
            .filter(OrderItem.order_id == order.id)
            .all()
        )
        items = []
        for oi in order_items_rows:
            mi = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id).first()
            items.append({
                "menu_item_id": oi.menu_item_id,
                "name": mi.name if mi else "Unknown Item",
                "quantity": oi.quantity,
                "price_at_time": oi.price_at_time,
            })

        # Fetch stationery jobs linked to this order (for combined bookings)
        stationery_jobs = []
        if order.booking_type == "combined":
            from app.modules.stationery.job_model import StationeryJob
            sj_rows = (
                db.query(StationeryJob)
                .filter(
                    StationeryJob.user_id == order.user_id,
                    StationeryJob.vendor_id == order.vendor_id,
                )
                .all()
            )
            stationery_jobs = [
                {
                    "id": sj.id,
                    "service_id": sj.service_id,
                    "quantity": sj.quantity,
                    "amount": sj.amount or 0,
                    "status": sj.status.value if hasattr(sj.status, "value") else str(sj.status),
                }
                for sj in sj_rows
            ]

        status_val = order.status.value if hasattr(order.status, "value") else str(order.status)
        result.append(OrderResponse(
            id=order.id,
            user_id=order.user_id,
            slot_id=order.slot_id,
            vendor_id=order.vendor_id,
            vendor_name=vendor_name,
            status=status_val,
            created_at=order.created_at,
            total_amount=order.total_amount,
            qr_code=order.qr_code,
            items=items,
            booking_type=order.booking_type or "food",
            stationery_jobs=stationery_jobs if stationery_jobs else None,
        ))

    return result
