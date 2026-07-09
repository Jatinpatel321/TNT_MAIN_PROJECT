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
    search: str | None = Query(default=None, description="Match vendor or item name"),
    date_from: str | None = Query(default=None, description="ISO date/datetime lower bound (inclusive)"),
    date_to: str | None = Query(default=None, description="ISO date/datetime upper bound (inclusive)"),
    vendor_id: int | None = Query(default=None),
    status: str | None = Query(default=None, description="Order status filter"),
    order_type: str | None = Query(default=None, description="food | stationery | combined"),
    sort: str = Query(default="newest", description="newest | oldest | amount_desc | amount_asc"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    from app.modules.users.model import User as UserModel
    db_user = db.query(UserModel).filter(UserModel.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    items, total = order_service.get_my_orders(
        user,
        db,
        search=search,
        date_from=date_from,
        date_to=date_to,
        vendor_id=vendor_id,
        status=status,
        order_type=order_type,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# 💳 BATCH PAYMENT STATUS — for group order tracking (who has paid)
@router.post("/payment-status")
def batch_payment_status(
    payload: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    """Return a {order_id: "paid" | "unpaid"} map for the given order IDs.

    Used by the group-cart screen to show each member's payment state. An
    order counts as paid when it has a SUCCESS payment.
    """
    from app.modules.payments.model import Payment, PaymentStatus

    order_ids = payload.get("order_ids") or []
    if not isinstance(order_ids, list):
        raise HTTPException(status_code=400, detail="order_ids must be a list")
    order_ids = [int(oid) for oid in order_ids][:200]  # cap batch size
    if not order_ids:
        return {"statuses": {}}

    paid_rows = (
        db.query(Payment.order_id)
        .filter(
            Payment.order_id.in_(order_ids),
            Payment.status == PaymentStatus.SUCCESS,
        )
        .all()
    )
    paid_set = {row.order_id for row in paid_rows}
    return {"statuses": {str(oid): ("paid" if oid in paid_set else "unpaid") for oid in order_ids}}


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
@router.get("/{order_id}/qr", response_model=dict)
def generate_qr_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate (or reuse) the rotating pickup QR for the owning student.

    Both GET and POST are accepted: GET reads the current live code, POST is
    the idempotent generate. Ownership and READY status are enforced in the
    service layer.
    """
    return order_service.generate_order_qr(user, order_id, db)


@router.post("/{order_id}/refresh-qr", response_model=dict)
def refresh_qr_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Force-rotate the pickup QR, invalidating the previous token."""
    return order_service.generate_order_qr(user, order_id, db, force=True)


@router.get("/{order_id}/pickup-status", response_model=dict)
def pickup_status_endpoint(
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Live pickup status (status, vendor, slot window, ETA, QR countdown)."""
    return order_service.get_pickup_status(user, order_id, db)


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
                "price_at_time": float(oi.price_at_time),
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
                    "amount": float(sj.amount or 0),
                    "status": sj.status.value if hasattr(sj.status, "value") else str(sj.status),
                    "print_type": sj.print_type.value if hasattr(sj.print_type, "value") else sj.print_type,
                    "paper_size": sj.paper_size.value if hasattr(sj.paper_size, "value") else sj.paper_size,
                    "duplex": sj.duplex,
                    "page_range": sj.page_range,
                    "notes": sj.notes,
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


# 💸 REQUEST REFUND (user-initiated; admin approves/rejects)
@router.post("/{order_id}/refund-request", tags=["Refunds"])
def request_refund(
    order_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Create a pending refund request for one of the caller's own orders.

    An admin later approves (executing the gateway refund) or rejects it.
    """
    from app.modules.orders.model import Order
    from app.modules.payments.model import Payment, PaymentStatus, RefundRequest, RefundRequestStatus

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != user.get("id"):
        raise HTTPException(status_code=403, detail="Not your order")

    # Prevent duplicate pending requests.
    existing = db.query(RefundRequest).filter(
        RefundRequest.order_id == order_id,
        RefundRequest.status == RefundRequestStatus.PENDING,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A refund request is already pending for this order")

    # Link the latest successful payment for gateway execution on approval.
    payment = (
        db.query(Payment)
        .filter(Payment.order_id == order_id, Payment.status == PaymentStatus.SUCCESS)
        .order_by(Payment.id.desc())
        .first()
    )
    amount = (payload or {}).get("amount") or int(order.total_amount or 0)
    reason = ((payload or {}).get("reason") or "").strip() or None

    req = RefundRequest(
        order_id=order_id,
        payment_id=payment.id if payment else None,
        user_id=user.get("id"),
        amount=int(amount),
        reason=reason,
        status=RefundRequestStatus.PENDING,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"message": "Refund request submitted", "id": req.id, "status": "pending"}
