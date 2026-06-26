"""Dashboard aggregation API for vendors."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus, OrderItem
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User
from app.modules.vendors.model import Vendor, VendorStaff
from app.modules.vendors.profile_models import VendorProfile
from app.modules.notifications.model import Notification

router = APIRouter(prefix="/vendors/dashboard", tags=["Vendor Dashboard"])


def _resolve_vendor_id(user: dict, db: Session) -> tuple[int, Vendor]:
    """Get vendor entity from the authenticated user dict."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    vendor = db.query(Vendor).filter(Vendor.owner_id == db_user.id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return db_user.id, vendor


@router.get("/")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Get aggregated dashboard metrics for the authenticated vendor.
    
    Returns:
    - Orders today
    - Revenue today
    - Pending orders
    - Completed orders
    - Average rating
    - Active slots
    - Recent orders
    - Recent notifications
    - Revenue trend (7 days)
    """
    vendor_user_id, vendor = _resolve_vendor_id(user, db)
    vendor_id = vendor_user_id  # Orders use User.id, not Vendor.vendor_id
    today = utcnow_naive().date()
    week_ago = today - timedelta(days=7)

    # Orders Today
    orders_today = db.query(Order).filter(
        Order.vendor_id == vendor_id,
        func.date(Order.created_at) == today,
    ).count()

    # Revenue Today (from successful payments)
    revenue_today = db.query(func.sum(Payment.amount)).join(
        Order, Order.id == Payment.order_id
    ).filter(
        Order.vendor_id == vendor_id,
        func.date(Payment.created_at) == today,
        Payment.status == PaymentStatus.SUCCESS,
    ).scalar() or 0
    revenue_today_rupees = revenue_today / 100  # Convert paise to rupees

    # Pending Orders (PLACED + CONFIRMED + PREPARING)
    pending_orders = db.query(Order).filter(
        Order.vendor_id == vendor_id,
        Order.status.in_([
            OrderStatus.PLACED,
            OrderStatus.CONFIRMED,
            OrderStatus.PREPARING,
        ]),
    ).count()

    # Completed Orders (PICKED + COMPLETED)
    completed_orders = db.query(Order).filter(
        Order.vendor_id == vendor_id,
        Order.status.in_([OrderStatus.PICKED, OrderStatus.COMPLETED]),
    ).count()

    # Average Rating from profile
    profile = db.query(VendorProfile).filter(VendorProfile.vendor_id == vendor.vendor_id).first()
    avg_rating = profile.rating if profile and profile.rating else 4.5

    # Active Slots (current and upcoming)
    now = utcnow_naive()
    active_slots = db.query(Slot).filter(
        Slot.vendor_id == vendor_id,
        Slot.start_time <= now + timedelta(hours=2),
        Slot.end_time >= now,
        Slot.status != "blocked",
    ).count()

    # Recent Orders (last 5)
    recent_orders = db.query(Order).filter(
        Order.vendor_id == vendor_id,
    ).order_by(Order.created_at.desc()).limit(5).all()
    
    recent_orders_data = [
        {
            "id": o.id,
            "user_id": o.user_id,
            "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
            "total_amount": o.total_amount,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in recent_orders
    ]

    # Recent Notifications (last 5)
    recent_notifications = db.query(Notification).filter(
        Notification.user_id == vendor_id,
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    recent_notifications_data = [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type.value if hasattr(n.notification_type, 'value') else str(n.notification_type),
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in recent_notifications
    ]

    # Revenue Trend (last 7 days)
    revenue_trend = []
    for i in range(7):
        date = today - timedelta(days=i)
        day_revenue = db.query(func.sum(Payment.amount)).join(
            Order, Order.id == Payment.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            func.date(Payment.created_at) == date,
            Payment.status == PaymentStatus.SUCCESS,
        ).scalar() or 0
        
        revenue_trend.append({
            "date": date.isoformat(),
            "revenue": round(float(day_revenue) / 100, 2),
        })
    
    revenue_trend.reverse()  # Oldest first

    return {
        "orders_today": orders_today,
        "revenue_today": round(revenue_today_rupees, 2),
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "avg_rating": round(avg_rating, 1),
        "active_slots": active_slots,
        "recent_orders": recent_orders_data,
        "recent_notifications": recent_notifications_data,
        "revenue_trend": revenue_trend,
    }


@router.get("/live-orders", summary="Get live orders for current slot")
def get_live_orders(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get current slot's orders with real-time status counts for the vendor dashboard."""
    vendor_user_id, _vendor = _resolve_vendor_id(user, db)
    vendor_id = vendor_user_id

    now = utcnow_naive()

    # Find current active slot
    current_slot = db.query(Slot).filter(
        Slot.vendor_id == vendor_id,
        Slot.start_time <= now,
        Slot.end_time >= now,
    ).first()

    slot_data = None
    if current_slot:
        slot_data = {
            "id": current_slot.id,
            "start_time": current_slot.start_time.isoformat(),
            "end_time": current_slot.end_time.isoformat(),
            "max_orders": current_slot.max_orders,
            "current_orders": current_slot.current_orders,
            "status": current_slot.status.value if hasattr(current_slot.status, 'value') else str(current_slot.status),
        }

    # Get all orders for this vendor grouped by status
    orders = db.query(Order).filter(
        Order.vendor_id == vendor_id,
    ).order_by(Order.created_at.desc()).limit(50).all()

    status_counts = {}
    orders_data = []
    for o in orders:
        status = o.status.value if hasattr(o.status, 'value') else str(o.status)
        status_counts[status] = status_counts.get(status, 0) + 1

        # Resolve user name
        order_user = db.query(User).filter(User.id == o.user_id).first()
        user_name = order_user.name if order_user else f"User #{o.user_id}"

        # Get items
        order_items = db.query(OrderItem).filter(OrderItem.order_id == o.id).all()
        items = []
        from app.modules.menu.model import MenuItem
        for oi in order_items:
            mi = db.query(MenuItem).filter(MenuItem.id == oi.menu_item_id).first()
            items.append({
                "id": oi.id,
                "menu_item_id": oi.menu_item_id,
                "name": mi.name if mi else f"Item {oi.menu_item_id}",
                "quantity": oi.quantity,
                "price_at_time": float(oi.price_at_time),
            })

        orders_data.append({
            "id": o.id,
            "user_id": o.user_id,
            "user_name": user_name,
            "status": status,
            "total_amount": o.total_amount,
            "eta_minutes": o.eta_minutes,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": items,
        })

    return {
        "current_slot": slot_data,
        "orders": orders_data,
        "status_counts": status_counts,
        "total_orders": len(orders),
    }


@router.get("/revenue-chart", summary="Get revenue chart data")
def get_revenue_chart(
    days: int = 30,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get daily revenue data for chart display."""
    vendor_user_id, _vendor = _resolve_vendor_id(user, db)
    vendor_id = vendor_user_id

    today = utcnow_naive().date()

    daily_data = []
    for i in range(days):
        day = today - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())

        # Online payments
        online = db.query(func.sum(Payment.amount)).join(
            Order, Order.id == Payment.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at.between(day_start, day_end),
        ).scalar() or 0

        # Cash orders (orders without payment)
        cash = db.query(func.sum(Order.total_amount)).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED,
            ~Order.id.in_(
                db.query(Payment.order_id).filter(Payment.status == PaymentStatus.SUCCESS)
            ),
            Order.created_at.between(day_start, day_end),
        ).scalar() or 0

        # Refunds
        refunds = db.query(func.sum(Payment.amount)).filter(
            Payment.order_id.in_(
                db.query(Order.id).filter(Order.vendor_id == vendor_id)
            ),
            Payment.status == PaymentStatus.REFUNDED,
            Payment.created_at.between(day_start, day_end),
        ).scalar() or 0

        order_count = db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at.between(day_start, day_end),
        ).scalar() or 0

        daily_data.append({
            "date": day.isoformat(),
            "day_name": day.strftime("%a"),
            "online": round(float(online) / 100, 2),
            "cash": round(float(cash), 2),
            "refunds": round(float(refunds) / 100, 2),
            "net": round(float(online + cash - refunds) / 100, 2),
            "orders": order_count,
        })

    daily_data.reverse()

    return {
        "daily_data": daily_data,
        "total_online": round(sum(d["online"] for d in daily_data), 2),
        "total_cash": round(sum(d["cash"] for d in daily_data), 2),
        "total_net": round(sum(d["net"] for d in daily_data), 2),
        "total_orders": sum(d["orders"] for d in daily_data),
    }


@router.get("/customer-insights", summary="Get customer insights")
def get_customer_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get customer insights including total customers, repeat rate, and top customers."""
    vendor_user_id, _vendor = _resolve_vendor_id(user, db)
    vendor_id = vendor_user_id

    thirty_days_ago = utcnow_naive() - timedelta(days=30)

    # Total unique customers
    total_customers = db.query(func.count(func.distinct(Order.user_id))).filter(
        Order.vendor_id == vendor_id,
    ).scalar() or 0

    # Customers in last 30 days
    recent_customers = db.query(func.count(func.distinct(Order.user_id))).filter(
        Order.vendor_id == vendor_id,
        Order.created_at >= thirty_days_ago,
        Order.status != OrderStatus.CANCELLED,
    ).scalar() or 0

    # Repeat customers (2+ orders)
    repeat_customers = (
        db.query(Order.user_id)
        .filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(Order.user_id)
        .having(func.count(Order.id) >= 2)
        .count()
    )

    repeat_rate = round(repeat_customers / max(total_customers, 1) * 100, 1)

    # New customers (first order in last 30 days)
    all_first_orders = (
        db.query(
            Order.user_id,
            func.min(Order.created_at).label("first_order"),
        )
        .filter(Order.vendor_id == vendor_id)
        .group_by(Order.user_id)
        .all()
    )

    new_customers_count = sum(
        1 for fo in all_first_orders
        if fo.first_order and fo.first_order >= thirty_days_ago
    )

    # Top customers by order count
    top_customers = (
        db.query(
            Order.user_id,
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_spent"),
            func.max(Order.created_at).label("last_order"),
        )
        .filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        )
        .group_by(Order.user_id)
        .order_by(func.count(Order.id).desc())
        .limit(10)
        .all()
    )

    top_customers_data = []
    for row in top_customers:
        cu = db.query(User).filter(User.id == row.user_id).first()
        top_customers_data.append({
            "user_id": row.user_id,
            "name": cu.name if cu else f"User #{row.user_id}",
            "phone": cu.phone if cu else None,
            "order_count": row.order_count,
            "total_spent": float(row.total_spent or 0),
            "last_order": row.last_order.isoformat() if row.last_order else None,
        })

    # Customer segments
    segments = {"loyal": 0, "repeat": 0, "new": 0, "at_risk": 0, "lapsed": 0}
    for fo in all_first_orders:
        last_order = db.query(func.max(Order.created_at)).filter(
            Order.vendor_id == vendor_id,
            Order.user_id == fo.user_id,
            Order.status != OrderStatus.CANCELLED,
        ).scalar()

        total_orders = db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.user_id == fo.user_id,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0

        days_since_last = (utcnow_naive() - last_order).days if last_order else 999

        if total_orders >= 5 and days_since_last <= 30:
            segments["loyal"] += 1
        elif total_orders >= 2 and days_since_last <= 30:
            segments["repeat"] += 1
        elif days_since_last <= 30:
            segments["new"] += 1
        elif days_since_last <= 60:
            segments["at_risk"] += 1
        else:
            segments["lapsed"] += 1

    return {
        "vendor_id": vendor_id,
        "total_customers": total_customers,
        "recent_customers": recent_customers,
        "new_customers": new_customers_count,
        "repeat_customers": repeat_customers,
        "repeat_rate": repeat_rate,
        "segments": segments,
        "top_customers": top_customers_data,
    }
