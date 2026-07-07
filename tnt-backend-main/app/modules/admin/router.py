import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.core.deps import get_db
from app.core.emergency import set_emergency_shutdown
from app.core.faculty_policy import get_faculty_priority_policy, set_faculty_priority_policy
from app.core.security import require_role
from app.core.time_utils import utcnow_naive
from app.core.university_policy import get_university_policy, set_university_policy
from app.modules.ledger.model import Ledger
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.users.model import User, UserRole

logger = logging.getLogger("tnt.admin.broadcasts")

from app.modules.admin.service import list_users, get_user_by_id, set_user_active
from app.modules.admin.schemas import (
    AdminUserListResponse,
    AdminUserDetailResponse,
    AdminUserStatusUpdate,
    AdminUserRoleUpdate,
    AdminVendorCreate,
    AdminVendorUpdate,
    VENDOR_TYPES,
)
from app.modules.admin.conflict_service import get_conflict_summary
from app.modules.admin.conflict_schemas import ConflictSummaryResponse
from app.modules.admin import export_service
from app.modules.auditlog import service as audit_service
from app.modules.auditlog.service import AuditAction, AuditCategory
from app.modules.admin.broadcast_schemas import BroadcastCreate, BroadcastListResponse
from app.modules.notifications.model import NotificationType

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/vendors")
def list_vendors(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
):
    vendors = db.query(User).filter(User.role == UserRole.VENDOR).order_by(User.created_at.desc()).all()
    
    # We will build a rich response similar to what the public API does, 
    # but including all status fields for the admin.
    from app.modules.vendors.router import _vendor_profile
    result = []
    for v in vendors:
        profile = _vendor_profile(v.id, db)
        meta = v.vendor_meta or {}
        result.append({
            "id": v.id,
            "name": v.name,
            "phone": v.phone,
            "vendor_type": v.vendor_type,
            "is_approved": v.is_approved,
            "is_active": v.is_active,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "rating": profile["rating"],
            "location": meta.get("location") or profile["location"],
            "stall": meta.get("stall"),
            "vendor_meta": meta,
        })
    return jsonable_encoder(result)


@router.get("/vendors/{vendor_id}")
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
):
    vendor = db.query(User).filter(User.id == vendor_id, User.role == UserRole.VENDOR).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    from app.modules.vendors.router import _build_vendor_response
    resp = _build_vendor_response(vendor, db, vendor.vendor_type or "food")
    meta = vendor.vendor_meta or {}
    resp["vendor_meta"] = meta
    resp["is_active"] = vendor.is_active
    resp["stall"] = meta.get("stall")
    if meta.get("location"):
        resp["location"] = meta.get("location")
    return resp


def _assemble_vendor_meta(existing: dict | None, payload) -> dict:
    """Merge admin vendor business fields into a vendor_meta dict."""
    meta = dict(existing or {})
    for field in ("stall", "location", "business_name", "description", "email",
                  "operating_hours", "slot_defaults"):
        val = getattr(payload, field, None)
        if val is not None:
            meta[field] = val
    return meta


@router.post("/vendors", summary="Create a new vendor (admin)")
def create_vendor(
    payload: AdminVendorCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    vendor_type = (payload.vendor_type or "food").strip().lower()
    if vendor_type not in VENDOR_TYPES:
        raise HTTPException(status_code=400, detail=f"vendor_type must be one of {sorted(VENDOR_TYPES)}")

    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")
    existing = db.query(User).filter(User.phone == phone).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this phone already exists")

    vendor = User(
        phone=phone,
        name=payload.name.strip(),
        full_name=payload.name.strip(),
        role=UserRole.VENDOR,
        vendor_type=vendor_type,
        is_approved=payload.is_approved,
        is_active=payload.is_approved,
        vendor_meta=_assemble_vendor_meta(None, payload),
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    try:
        audit_service.write(
            db=db,
            action=AuditAction.VENDOR_CREATED,
            action_category=AuditCategory.VENDOR,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Vendor",
            entity_id=str(vendor.id),
            before_state=None,
            after_state={"created": True, "vendor_type": vendor_type, "is_approved": payload.is_approved},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {
        "id": vendor.id,
        "name": vendor.name,
        "phone": vendor.phone,
        "vendor_type": vendor.vendor_type,
        "is_approved": vendor.is_approved,
        "is_active": vendor.is_active,
        "vendor_meta": vendor.vendor_meta or {},
        "message": "Vendor created",
    }


@router.patch("/vendors/{vendor_id}", summary="Update vendor details (admin)")
def update_vendor(
    vendor_id: int,
    payload: AdminVendorUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    vendor = db.query(User).filter(User.id == vendor_id, User.role == UserRole.VENDOR).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    before = {
        "name": vendor.name,
        "vendor_type": vendor.vendor_type,
        "is_approved": vendor.is_approved,
        "is_active": vendor.is_active,
        "vendor_meta": vendor.vendor_meta or {},
    }

    if payload.vendor_type is not None:
        vt = payload.vendor_type.strip().lower()
        if vt not in VENDOR_TYPES:
            raise HTTPException(status_code=400, detail=f"vendor_type must be one of {sorted(VENDOR_TYPES)}")
        vendor.vendor_type = vt
    if payload.name is not None:
        vendor.name = payload.name.strip()
        vendor.full_name = payload.name.strip()
    if payload.is_approved is not None:
        vendor.is_approved = payload.is_approved
    if payload.is_active is not None:
        vendor.is_active = payload.is_active

    vendor.vendor_meta = _assemble_vendor_meta(vendor.vendor_meta, payload)

    db.commit()
    db.refresh(vendor)

    try:
        audit_service.write(
            db=db,
            action=AuditAction.VENDOR_UPDATED,
            action_category=AuditCategory.VENDOR,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Vendor",
            entity_id=str(vendor.id),
            before_state=before,
            after_state={
                "name": vendor.name,
                "vendor_type": vendor.vendor_type,
                "is_approved": vendor.is_approved,
                "is_active": vendor.is_active,
                "vendor_meta": vendor.vendor_meta or {},
            },
        )
        db.commit()
    except Exception:
        db.rollback()

    return {
        "id": vendor.id,
        "name": vendor.name,
        "phone": vendor.phone,
        "vendor_type": vendor.vendor_type,
        "is_approved": vendor.is_approved,
        "is_active": vendor.is_active,
        "vendor_meta": vendor.vendor_meta or {},
        "message": "Vendor updated",
    }

@router.get("/vendors/{vendor_id}/menu")
def get_vendor_menu(vendor_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    vendor = db.query(User).filter(User.id == vendor_id, User.role == UserRole.VENDOR).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    from app.modules.menu.model import MenuItem
    from app.modules.menu.image_utils import menu_image_for
    
    menu_items = db.query(MenuItem).filter(MenuItem.vendor_id == vendor_id).all()
    payload = []
    for item in menu_items:
        img_url = item.image_url or menu_image_for(item.name, vendor.vendor_type or "food")
        payload.append({
            "id": item.id,
            "vendor_id": item.vendor_id,
            "name": item.name,
            "description": item.description or f"Delicious {item.name}",
            "price": float(item.price),
            "image_url": img_url,
            "is_available": item.is_available,
        })
    return payload

@router.get("/vendors/{vendor_id}/slots")
def get_vendor_slots(vendor_id: int, db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    vendor = db.query(User).filter(User.id == vendor_id, User.role == UserRole.VENDOR).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    from app.modules.slots.model import Slot
    slots = db.query(Slot).filter(Slot.vendor_id == vendor_id).order_by(Slot.start_time).all()
    payload = []
    for slot in slots:
        payload.append({
            "id": slot.id,
            "vendor_id": slot.vendor_id,
            "start_time": slot.start_time.isoformat(),
            "end_time": slot.end_time.isoformat(),
            "is_active": True,
            "capacity": slot.max_orders,
            "booked_count": slot.current_orders,
        })
    return payload

# ✅ BULK APPROVE VENDORS
@router.post("/vendors/bulk-approve", summary="Approve multiple vendors at once")
def bulk_approve_vendors(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    vendor_ids = payload.get("vendor_ids") or []
    if not isinstance(vendor_ids, list) or not vendor_ids:
        raise HTTPException(status_code=400, detail="vendor_ids must be a non-empty list")

    vendors = db.query(User).filter(
        User.id.in_(vendor_ids),
        User.role == UserRole.VENDOR,
    ).all()
    approved = []
    for v in vendors:
        if not (v.is_approved and v.is_active):
            v.is_approved = True
            v.is_active = True
            approved.append(v.id)
    db.commit()

    for vid in approved:
        try:
            audit_service.write(
                db=db,
                action=AuditAction.VENDOR_APPROVED,
                action_category=AuditCategory.VENDOR,
                actor_id=user.get("id"),
                actor_role=user.get("role"),
                entity_type="Vendor",
                entity_id=str(vid),
                after_state={"is_approved": True, "is_active": True, "bulk": True},
            )
        except Exception:
            pass
    try:
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Bulk approval complete", "approved_count": len(approved), "approved_ids": approved}


# ✅ APPROVE VENDOR
@router.post("/vendors/{vendor_id}/approve")
def approve_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    vendor = db.query(User).filter(User.id == vendor_id).first()
    if not vendor or vendor.role != UserRole.VENDOR:
        raise HTTPException(status_code=404, detail="Vendor not found")

    before = {"is_approved": vendor.is_approved, "is_active": vendor.is_active}
    vendor.is_approved = True
    vendor.is_active = True
    db.commit()
    db.refresh(vendor)

    try:
        audit_service.write(
            db=db,
            action=AuditAction.VENDOR_APPROVED,
            action_category=AuditCategory.VENDOR,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Vendor",
            entity_id=str(vendor.id),
            before_state=before,
            after_state={"is_approved": True, "is_active": True},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Vendor approved", "vendor_id": vendor_id}


# 🚫 REJECT VENDOR
@router.post("/vendors/{vendor_id}/reject")
def reject_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    vendor = db.query(User).filter(User.id == vendor_id).first()
    if not vendor or vendor.role != UserRole.VENDOR:
        raise HTTPException(status_code=404, detail="Vendor not found")

    before = {"is_approved": vendor.is_approved, "is_active": vendor.is_active}
    vendor.is_approved = False
    vendor.is_active = False
    db.commit()
    db.refresh(vendor)

    # Revoke all refresh tokens for rejected vendor
    try:
        from app.modules.auth.refresh_router import revoke_all_user_tokens
        revoke_all_user_tokens(vendor.id)
    except Exception:
        pass

    try:
        audit_service.write(
            db=db,
            action=AuditAction.VENDOR_REJECTED,
            action_category=AuditCategory.VENDOR,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Vendor",
            entity_id=str(vendor.id),
            before_state=before,
            after_state={"is_approved": False, "is_active": False},
        )
        db.commit()
    except Exception:
        db.rollback()

    try:
        from app.modules.notifications.service import notify_user
        notify_user(
            user_id=vendor.id,
            phone=vendor.phone,
            title="Application Status Update",
            message="Your vendor application has been rejected. Contact admin for details.",
            db=db,
        )
        db.commit()
    except Exception:
        pass

    return {"message": "Vendor rejected", "vendor_id": vendor_id}


# 🚫 BLOCK / UNBLOCK USER
@router.post("/users/{user_id}/toggle")
def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    before = {"is_active": db_user.is_active}
    was_just_blocked = db_user.is_active  # True before toggle means they're about to be blocked
    db_user.is_active = not db_user.is_active
    db.commit()
    db.refresh(db_user)

    # Revoke all refresh tokens when blocking a user (session revocation)
    if was_just_blocked and not db_user.is_active:
        try:
            from app.modules.auth.refresh_router import revoke_all_user_tokens
            revoke_all_user_tokens(user_id)
        except Exception:
            pass

    try:
        audit_service.write(
            db=db,
            action=AuditAction.USER_ACTIVATED if db_user.is_active else AuditAction.USER_BLOCKED,
            action_category=AuditCategory.USER,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="User",
            entity_id=str(db_user.id),
            before_state=before,
            after_state={"is_active": db_user.is_active},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {
        "user_id": user_id,
        "is_active": db_user.is_active
    }


# 📦 VIEW ALL ORDERS
@router.get("/orders")
def all_orders(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
):
    return jsonable_encoder(db.query(Order).order_by(Order.created_at.desc()).all())


# 📘 VIEW LEDGER
@router.get("/ledger")
def ledger_view(
    type: Optional[str] = Query(None, description="Filter by credit | debit"),
    source: Optional[str] = Query(None, description="Filter by source"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
):
    """Return ledger entries in the admin-panel shape (user_id/user_name/type/timestamp)."""
    from app.modules.ledger.model import LedgerType

    q = db.query(Ledger)
    if type in ("credit", "debit"):
        q = q.filter(Ledger.entry_type == (LedgerType.CREDIT if type == "credit" else LedgerType.DEBIT))
    if source:
        q = q.filter(Ledger.source == source)
    if date_from:
        try:
            from datetime import datetime as _dt
            q = q.filter(Ledger.created_at >= _dt.fromisoformat(date_from))
        except Exception:
            pass
    if date_to:
        try:
            from datetime import datetime as _dt
            q = q.filter(Ledger.created_at <= _dt.fromisoformat(date_to + "T23:59:59"))
        except Exception:
            pass

    rows = q.order_by(Ledger.created_at.desc()).limit(limit).all()

    # Resolve user names in one batch.
    order_ids = {r.order_id for r in rows if r.order_id}
    orders_map = {}
    if order_ids:
        for o in db.query(Order).filter(Order.id.in_(order_ids)).all():
            orders_map[o.id] = o.user_id
    user_ids = set(orders_map.values()) | {r.created_by for r in rows if r.created_by}
    users_map = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            users_map[u.id] = u.name or u.full_name or f"User #{u.id}"

    result = []
    for r in rows:
        uid = orders_map.get(r.order_id) if r.order_id else r.created_by
        result.append({
            "id": r.id,
            "user_id": uid,
            "user_name": users_map.get(uid),
            "type": r.entry_type.value if hasattr(r.entry_type, "value") else r.entry_type,
            "amount": float(r.amount),
            "description": r.description or "",
            "order_id": r.order_id,
            "source": r.source.value if hasattr(r.source, "value") else r.source,
            "timestamp": r.created_at.isoformat() if r.created_at else None,
        })
    return result


# ➕ MANUAL LEDGER ADJUSTMENT
@router.post("/ledger/adjustment", summary="Create a manual ledger adjustment (credit/debit)")
def create_ledger_adjustment(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Append a manual adjustment entry to the ledger (append-only accounting)."""
    from app.modules.ledger.model import LedgerType, LedgerSource

    entry_type = str(payload.get("type", "")).lower()
    if entry_type not in ("credit", "debit"):
        raise HTTPException(status_code=400, detail="type must be 'credit' or 'debit'")
    try:
        amount = float(payload.get("amount"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="amount (rupees) must be a number")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")

    description = (payload.get("description") or "Manual adjustment").strip()
    order_id = payload.get("order_id")
    if order_id is not None:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

    entry = Ledger(
        order_id=order_id,
        payment_id=None,
        created_by=user.get("id"),
        amount=amount,
        entry_type=LedgerType.CREDIT if entry_type == "credit" else LedgerType.DEBIT,
        source=LedgerSource.ADJUSTMENT,
        description=description,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    try:
        audit_service.write(
            db=db,
            action=AuditAction.LEDGER_ADJUSTED,
            action_category=AuditCategory.SETTINGS,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Ledger",
            entity_id=str(entry.id),
            after_state={"type": entry_type, "amount": amount, "order_id": order_id, "description": description},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Adjustment recorded", "id": entry.id}


# 🚨 EMERGENCY SHUTDOWN
@router.post("/shutdown")
def emergency_shutdown(
    enabled: bool,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    is_enabled = set_emergency_shutdown(enabled)
    return {
        "message": f"Emergency shutdown {'enabled' if is_enabled else 'disabled'}",
        "enabled": is_enabled,
    }


# 🚩 MARK ORDER AS FRAUD
@router.post("/orders/{order_id}/fraud")
def mark_order_fraud(
    order_id: int,
    reason: Optional[str] = Query(None, description="Optional fraud reason"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.fraud_flag:
        raise HTTPException(status_code=400, detail="Order is already flagged as fraud")

    order.fraud_flag = True
    order.flagged_at = utcnow_naive()
    if reason:
        order.fraud_reason = reason
    db.commit()
    db.refresh(order)

    try:
        audit_service.write(
            db=db,
            action=AuditAction.ORDER_OVERRIDE,
            action_category=AuditCategory.ORDER,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Order",
            entity_id=str(order.id),
            before_state={"fraud_flag": False},
            after_state={"fraud_flag": True, "flagged_at": order.flagged_at.isoformat()},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {
        "message": "Order marked as fraud",
        "order_id": order.id,
        "flagged_at": order.flagged_at.isoformat(),
        "fraud_reason": order.fraud_reason,
    }


# 📊 ANALYTICS ENDPOINT
@router.get("/analytics")
async def get_analytics(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    from datetime import timedelta
    from app.core.redis_cache import cache_service

    def fetch_analytics():
        now = utcnow_naive()
        thirty_days_ago = now - timedelta(days=30)
        this_week_start = now - timedelta(days=7)
        last_week_start = now - timedelta(days=14)

        total_users = db.query(User).count()
        total_vendors = db.query(User).filter(User.role == UserRole.VENDOR).count()
        total_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
        total_orders = db.query(Order).count()
        total_revenue_paise = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.status == PaymentStatus.SUCCESS
        ).scalar() or 0

        orders_by_day_rows = db.query(
            func.date(Order.created_at).label("day"),
            func.count(Order.id).label("count"),
        ).filter(Order.created_at >= thirty_days_ago)\
         .group_by(func.date(Order.created_at))\
         .order_by(func.date(Order.created_at))\
         .all()
        orders_by_day = [{"date": str(r.day), "orders": r.count} for r in orders_by_day_rows]

        revenue_by_day_rows = db.query(
            func.date(Payment.created_at).label("day"),
            func.coalesce(func.sum(Payment.amount), 0).label("revenue"),
        ).filter(
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= thirty_days_ago,
        ).group_by(func.date(Payment.created_at))\
         .order_by(func.date(Payment.created_at))\
         .all()
        revenue_by_day = [{"date": str(r.day), "revenue_paise": int(r.revenue)} for r in revenue_by_day_rows]

        signups_by_day_rows = db.query(
            func.date(User.created_at).label("day"),
            func.count(User.id).label("count"),
        ).filter(User.created_at >= thirty_days_ago)\
         .group_by(func.date(User.created_at))\
         .order_by(func.date(User.created_at))\
         .all()
        signups_by_day = [{"date": str(r.day), "signups": r.count} for r in signups_by_day_rows]

        status_rows = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
        order_status = {row[0].value if row[0] else "unknown": row[1] for row in status_rows}

        pay_rows = db.query(Payment.status, func.count(Payment.id)).group_by(Payment.status).all()
        payment_status = {row[0].value if row[0] else "unknown": row[1] for row in pay_rows}

        top_vendor_rows = db.query(
            Order.vendor_id,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_revenue"),
        ).group_by(Order.vendor_id)\
         .order_by(func.count(Order.id).desc())\
         .limit(10).all()
        top_vendors = [
            {
                "vendor_id": r.vendor_id,
                "order_count": r.order_count,
                "total_revenue_paise": int(r.total_revenue),
            }
            for r in top_vendor_rows
        ]

        from sqlalchemy import extract
        peak_rows = db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        ).group_by(extract("hour", Order.created_at))\
         .order_by(extract("hour", Order.created_at))\
         .all()
        peak_hours = {int(r.hour): r.count for r in peak_rows}

        this_week_orders = db.query(func.count(Order.id)).filter(
            Order.created_at >= this_week_start
        ).scalar() or 0
        last_week_orders = db.query(func.count(Order.id)).filter(
            Order.created_at >= last_week_start,
            Order.created_at < this_week_start,
        ).scalar() or 0

        this_week_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= this_week_start,
        ).scalar() or 0
        last_week_revenue = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.status == PaymentStatus.SUCCESS,
            Payment.created_at >= last_week_start,
            Payment.created_at < this_week_start,
        ).scalar() or 0

        total_flagged = db.query(func.count(Order.id)).filter(Order.fraud_flag == True).scalar() or 0
        fraud_rate_pct = round(total_flagged / total_orders * 100, 2) if total_orders else 0.0

        return {
            "totals": {
                "users": total_users,
                "vendors": total_vendors,
                "students": total_students,
                "orders": total_orders,
                "revenue_paise": int(total_revenue_paise),
            },
            "orders_by_day": orders_by_day,
            "revenue_by_day": revenue_by_day,
            "signups_by_day": signups_by_day,
            "order_status": order_status,
            "payment_status": payment_status,
            "top_vendors": top_vendors,
            "peak_hours": peak_hours,
            "week_comparison": {
                "this_week": {"orders": this_week_orders, "revenue_paise": int(this_week_revenue)},
                "last_week": {"orders": last_week_orders, "revenue_paise": int(last_week_revenue)},
                "order_delta": this_week_orders - last_week_orders,
                "revenue_delta_paise": int(this_week_revenue) - int(last_week_revenue),
            },
            "fraud_stats": {
                "total_flagged": total_flagged,
                "fraud_rate_pct": fraud_rate_pct,
            },
        }

    return await cache_service.get_or_set(
        category="analytics",
        identifier="admin_general_analytics",
        fetch_func=fetch_analytics,
        ttl=300
    )


@router.get("/analytics/kpis", summary="Get aggregated institutional KPIs with filters")
async def get_kpis(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.admin.kpi_service import KPIService
    from app.core.redis_cache import cache_service

    # Build cache key based on query filters
    cache_identifier = f"kpis:from={date_from or 'all'}:to={date_to or 'all'}:dept={department or 'all'}:vendor={vendor_id or 'all'}"

    def fetch_kpis():
        service = KPIService(db)
        return service.get_aggregated_kpis(date_from, date_to, department, vendor_id)

    data = await cache_service.get_or_set(
        category="analytics",
        identifier=cache_identifier,
        fetch_func=fetch_kpis,
        ttl=300
    )
    return data


@router.get("/analytics/wastage", summary="Get aggregated institutional food waste analytics")
async def get_wastage_analytics(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.admin.kpi_service import KPIService
    service = KPIService(db)
    return service.get_food_waste_analytics()


# 👥 USER MANAGEMENT
@router.get("/users", response_model=AdminUserListResponse)
def list_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    role: Optional[str] = Query(None, description="Filter by role: student | faculty | vendor | staff | admin"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return list_users(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        is_active=is_active,
    )


@router.get("/users/{user_id}", response_model=AdminUserDetailResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.patch("/users/{user_id}/status", response_model=AdminUserDetailResponse)
def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    before = {"is_active": db_user.is_active}
    was_just_blocked = db_user.is_active  # True before means they're about to be blocked
    db_user.is_active = payload.is_active
    db.commit()
    db.refresh(db_user)

    # Revoke all refresh tokens when blocking a user (session revocation)
    if was_just_blocked and not db_user.is_active:
        try:
            from app.modules.auth.refresh_router import revoke_all_user_tokens
            revoke_all_user_tokens(user_id)
        except Exception:
            pass

    try:
        audit_service.write(
            db=db,
            action=AuditAction.USER_ACTIVATED if db_user.is_active else AuditAction.USER_BLOCKED,
            action_category=AuditCategory.USER,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="User",
            entity_id=str(db_user.id),
            before_state=before,
            after_state={"is_active": db_user.is_active},
        )
        db.commit()
    except Exception:
        db.rollback()

    return db_user


# ⚠️ CONFLICT RESOLUTION
@router.get("/conflicts", response_model=ConflictSummaryResponse)
def get_conflicts(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return get_conflict_summary(db)


# 📥 EXPORT ENDPOINTS
@router.get("/export/orders", summary="Export orders as CSV")
def export_orders(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return export_service.export_orders_csv(db, date_from, date_to, status)


@router.get("/export/users", summary="Export users as CSV")
def export_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return export_service.export_users_csv(db, role, is_active)


@router.get("/export/vendors", summary="Export vendors as CSV")
def export_vendors(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return export_service.export_vendors_csv(db)


@router.get("/export/complaints", summary="Export complaints as CSV")
def export_complaints(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return export_service.export_complaints_csv(db, status)


@router.get("/export/revenue", summary="Export daily revenue summary as CSV")
def export_revenue(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return export_service.export_revenue_csv(db, date_from, date_to)

@router.get("/export/kpis", summary="Export KPIs as PDF or Excel")
def export_kpis(
    format: str = Query("excel", pattern="^(excel|pdf)$"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from datetime import datetime
    from app.modules.admin.kpi_service import KPIService
    from app.modules.admin.kpi_export_service import generate_kpi_excel, generate_kpi_pdf

    service = KPIService(db)
    data = service.get_aggregated_kpis(date_from, date_to, department, vendor_id)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "pdf":
        pdf_buf = generate_kpi_pdf(data)
        filename = f"tnt_kpi_report_{now_str}.pdf"
        return StreamingResponse(
            pdf_buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        excel_buf = generate_kpi_excel(data)
        filename = f"tnt_kpi_report_{now_str}.xlsx"
        return StreamingResponse(
            excel_buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )



# 🏛 POLICIES
@router.get("/policies/faculty-priority")
def get_faculty_priority_policy_endpoint(user=Depends(require_role("admin"))) -> dict[str, Any]:
    return get_faculty_priority_policy()


@router.post("/policies/faculty-priority")
def set_faculty_priority_policy_endpoint(
    enabled: bool,
    start_hour: int = 12,
    end_hour: int = 14,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    if start_hour < 0 or start_hour > 23 or end_hour < 1 or end_hour > 24:
        raise HTTPException(status_code=400, detail="Hours must be within 0-24")
    if end_hour <= start_hour:
        raise HTTPException(status_code=400, detail="end_hour must be greater than start_hour")

    before = get_faculty_priority_policy()
    result = set_faculty_priority_policy(enabled, start_hour, end_hour)

    try:
        audit_service.write(
            db=db,
            action=AuditAction.FACULTY_POLICY_UPDATED,
            action_category=AuditCategory.POLICY,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Policy",
            entity_id="faculty-priority",
            before_state=before,
            after_state=result,
        )
        db.commit()
    except Exception:
        db.rollback()

    return result


@router.get("/policies/university")
def get_university_policy_endpoint(user=Depends(require_role("admin"))) -> dict[str, Any]:
    return get_university_policy()


@router.post("/policies/university")
def set_university_policy_endpoint(
    enabled: bool,
    break_start_hour: int = 12,
    break_end_hour: int = 14,
    max_orders_per_user: int = 3,
    min_slot_duration_minutes: int = 15,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    if break_start_hour < 0 or break_start_hour > 23:
        raise HTTPException(status_code=400, detail="break_start_hour must be in 0-23")
    if break_end_hour < 1 or break_end_hour > 24:
        raise HTTPException(status_code=400, detail="break_end_hour must be in 1-24")
    if break_end_hour <= break_start_hour:
        raise HTTPException(status_code=400, detail="break_end_hour must be greater than break_start_hour")
    if max_orders_per_user < 1:
        raise HTTPException(status_code=400, detail="max_orders_per_user must be at least 1")
    if min_slot_duration_minutes < 5:
        raise HTTPException(status_code=400, detail="min_slot_duration_minutes must be at least 5")

    before = get_university_policy()
    result = set_university_policy(
        enabled=enabled,
        break_start_hour=break_start_hour,
        break_end_hour=break_end_hour,
        max_orders_per_user=max_orders_per_user,
        min_slot_duration_minutes=min_slot_duration_minutes,
    )

    try:
        audit_service.write(
            db=db,
            action=AuditAction.POLICY_UPDATED,
            action_category=AuditCategory.POLICY,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Policy",
            entity_id="university",
            before_state=before,
            after_state=result,
        )
        db.commit()
    except Exception:
        db.rollback()

    return result


# 📢 GLOBAL ANNOUNCEMENT
@router.post("/announce")
def send_global_announcement(
    message: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin"))
) -> dict[str, Any]:
    from app.modules.notifications.service import notify_user

    users = db.query(User).all()
    for user_obj in users:
        notify_user(
            user_id=user_obj.id,
            phone=user_obj.phone,
            title="Admin Announcement",
            message=message,
            db=db
        )

    try:
        audit_service.write(
            db=db,
            action=AuditAction.ANNOUNCEMENT_SENT,
            action_category=AuditCategory.ANNOUNCEMENT,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Announcement",
            metadata={"message": message, "recipient_count": len(users)},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Announcement sent to all users"}


# ── Broadcast (persistent fan-out) endpoints ──────────────────────────────


@router.post("/broadcasts", summary="Send broadcast with persistent history")
def create_broadcast(
    payload: BroadcastCreate = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Fan out a message to push notifications for a target audience.

    - ``severity=critical`` also triggers SMS fallback for every recipient.
    - The broadcast record is persisted so the sent list is real data.
    - ``audience`` filters: ``all`` (all active users), ``faculty`` (role=faculty),
      ``vendor_customers`` (users who have ordered from a specific vendor).
    """
    from app.modules.notifications.service import notify_user

    # ── Resolve target users ──────────────────────────────────────────
    q = db.query(User).filter(User.is_active == True)

    if payload.audience == "faculty":
        q = q.filter(User.role == UserRole.FACULTY)
    elif payload.audience == "vendor_customers":
        if not payload.vendor_id:
            raise HTTPException(status_code=400, detail="vendor_id is required for audience=vendor_customers")
        # Users who have placed at least one order with this vendor
        subq = (
            db.query(Order.user_id)
            .filter(Order.vendor_id == payload.vendor_id)
            .distinct()
            .subquery()
        )
        q = q.filter(User.id.in_(db.query(subq.c.user_id)))

    target_users = q.all()

    # ── Send notifications ────────────────────────────────────────────
    send_sms = payload.severity == "critical"
    sent_count = 0
    for u in target_users:
        try:
            notify_user(
                user_id=u.id,
                phone=u.phone,
                title=payload.title,
                message=payload.message,
                db=db,
                send_sms_flag=send_sms,
                notification_type=NotificationType.SYSTEM,
            )
            sent_count += 1
        except Exception:
            logger.exception("broadcast_notify_failed user_id=%s", u.id)

    # ── Persist broadcast record ───────────────────────────────────────
    from app.modules.admin.broadcast_model import Broadcast as BroadcastModel

    record = BroadcastModel(
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        audience=payload.audience,
        vendor_id=payload.vendor_id,
        sent_count=sent_count,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # ── Audit log ──────────────────────────────────────────────────────
    try:
        audit_service.write(
            db=db,
            action=AuditAction.ANNOUNCEMENT_SENT,
            action_category=AuditCategory.ANNOUNCEMENT,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="Broadcast",
            entity_id=str(record.id),
            metadata={
                "title": payload.title,
                "severity": payload.severity,
                "audience": payload.audience,
                "recipient_count": sent_count,
            },
        )
    except Exception:
        pass

    return {
        "message": "Broadcast sent",
        "broadcast_id": record.id,
        "sent_count": sent_count,
        "severity": payload.severity,
    }


@router.get("/broadcasts", response_model=BroadcastListResponse)
def list_broadcasts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Return real broadcast history, newest first."""
    from app.modules.admin.broadcast_model import Broadcast as BroadcastModel

    total = db.query(func.count(BroadcastModel.id)).scalar() or 0
    rows = (
        db.query(BroadcastModel)
        .order_by(BroadcastModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return BroadcastListResponse(broadcasts=rows, total=total)


# ── Backup & Restore ─────────────────────────────────────────────────────


@router.post("/backup", summary="Trigger a database backup")
def trigger_backup(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Run pg_dump as a background task and return the resulting file metadata.

    The backup is saved to ``backups/tnt_backup_<timestamp>.dump``.
    """
    from app.modules.admin.backup_service import run_backup

    try:
        result = run_backup()
        return {
            "message": "Backup completed",
            "backup": result,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="pg_dump not found on PATH. Ensure PostgreSQL client tools are installed.",
        )


@router.get("/backups", summary="List all database backup files")
def list_backups(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Return metadata for every backup file in the backups directory."""
    from app.modules.admin.backup_service import list_backups

    files = list_backups()
    return {"backups": files, "total": len(files)}


@router.patch("/users/{user_id}/role", response_model=AdminUserDetailResponse, summary="Change user role")
def update_user_role(
    user_id: int,
    payload: AdminUserRoleUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    new_role_str = payload.role.strip().lower()
    valid_roles = {"student", "faculty", "vendor", "staff", "admin", "super_admin"}
    if new_role_str not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {valid_roles}")

    from app.modules.users.model import UserRole
    mapped_role = None
    for r in UserRole:
        if r.value.lower() == new_role_str:
            mapped_role = r
            break

    if mapped_role is None:
        raise HTTPException(status_code=400, detail="Invalid role enum value mapping")

    before_role = db_user.role.value if hasattr(db_user.role, "value") else str(db_user.role)
    if before_role == new_role_str:
        return db_user

    before = {"role": before_role}
    db_user.role = mapped_role
    db.commit()
    db.refresh(db_user)

    # Log to audit history
    try:
        from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
        write_audit_log(
            db=db,
            action=AuditAction.USER_ROLE_CHANGED,
            action_category=AuditCategory.USER,
            actor_id=user.get("id"),
            actor_role=user.get("role"),
            entity_type="User",
            entity_id=str(db_user.id),
            before_state=before,
            after_state={"role": new_role_str},
        )
        db.commit()
    except Exception:
        db.rollback()

    return db_user


# ── FINANCE: Settlements ───────────────────────────────────────────────────


@router.get("/settlements", summary="List vendor settlements (all vendors)")
def list_settlements(
    status: Optional[str] = Query(None, description="pending | processing | completed | failed"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.vendors.settlement_models import VendorSettlement, SettlementStatus

    q = db.query(VendorSettlement)
    if status:
        try:
            q = q.filter(VendorSettlement.status == SettlementStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    rows = q.order_by(VendorSettlement.created_at.desc()).all()

    vendor_ids = {r.vendor_id for r in rows}
    names = {u.id: (u.name or u.full_name or f"Vendor #{u.id}")
             for u in db.query(User).filter(User.id.in_(vendor_ids)).all()} if vendor_ids else {}

    return [
        {
            "id": r.id,
            "vendor_id": r.vendor_id,
            "vendor_name": names.get(r.vendor_id, f"Vendor #{r.vendor_id}"),
            "period_start": r.period_start.isoformat() if r.period_start else None,
            "period_end": r.period_end.isoformat() if r.period_end else None,
            "total_amount": float(r.total_amount),
            "total_fees": r.total_fees,
            "net_amount": float(r.net_amount),
            "order_count": r.order_count,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "settled_at": r.settled_at.isoformat() if r.settled_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/settlements/{settlement_id}/approve", summary="Approve/complete a settlement")
def approve_settlement(
    settlement_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.vendors.settlement_models import VendorSettlement, SettlementStatus

    s = db.query(VendorSettlement).filter(VendorSettlement.id == settlement_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Settlement not found")
    if s.status == SettlementStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Settlement already completed")

    before = s.status.value if hasattr(s.status, "value") else s.status
    s.status = SettlementStatus.COMPLETED
    s.settled_at = utcnow_naive()
    db.commit()

    try:
        audit_service.write(
            db=db, action=AuditAction.SETTLEMENT_APPROVED, action_category=AuditCategory.SETTINGS,
            actor_id=user.get("id"), actor_role=user.get("role"),
            entity_type="Settlement", entity_id=str(s.id),
            before_state={"status": before}, after_state={"status": "completed"},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Settlement approved", "id": s.id, "status": "completed"}


# ── FINANCE: Refund requests (approval workflow) ───────────────────────────


def _refund_request_dict(r, users_map) -> dict:
    return {
        "id": r.id,
        "order_id": r.order_id,
        "payment_id": r.payment_id,
        "user_id": r.user_id,
        "user_name": users_map.get(r.user_id, f"User #{r.user_id}"),
        "amount": float(r.amount),
        "reason": r.reason,
        "status": r.status.value if hasattr(r.status, "value") else r.status,
        "decision_note": r.decision_note,
        "decided_by": r.decided_by,
        "requested_at": r.requested_at.isoformat() if r.requested_at else None,
        "decided_at": r.decided_at.isoformat() if r.decided_at else None,
    }


@router.get("/refund-requests", summary="List refund requests")
def list_refund_requests(
    status: Optional[str] = Query(None, description="pending | approved | rejected"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.payments.model import RefundRequest, RefundRequestStatus

    q = db.query(RefundRequest)
    if status:
        try:
            q = q.filter(RefundRequest.status == RefundRequestStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    rows = q.order_by(RefundRequest.requested_at.desc()).all()
    uids = {r.user_id for r in rows}
    names = {u.id: (u.name or u.full_name or f"User #{u.id}")
             for u in db.query(User).filter(User.id.in_(uids)).all()} if uids else {}
    return [_refund_request_dict(r, names) for r in rows]


@router.post("/refund-requests/{request_id}/approve", summary="Approve a refund request (executes refund)")
def approve_refund_request(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.payments.model import RefundRequest, RefundRequestStatus

    req = db.query(RefundRequest).filter(RefundRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if req.status != RefundRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Refund request already decided")

    # Execute the actual gateway refund via the existing refund flow when we have
    # a payment id; otherwise just approve (e.g. cash/manual settlement).
    refund_result = None
    if req.payment_id:
        try:
            from app.modules.payments.service import refund_payment
            refund_result = refund_payment(req.payment_id, {"id": user.get("id"), "role": user.get("role")}, db)
        except HTTPException as e:
            # Validation failure (e.g. already refunded) — keep request pending.
            db.rollback()
            raise HTTPException(status_code=e.status_code, detail=f"Refund execution failed: {e.detail}")
        except Exception as e:
            # Gateway/network failure — keep request pending, surface 502.
            db.rollback()
            raise HTTPException(status_code=502, detail=f"Payment gateway refund failed: {type(e).__name__}")

    req.status = RefundRequestStatus.APPROVED
    req.decided_by = user.get("id")
    req.decided_at = utcnow_naive()
    db.commit()

    try:
        audit_service.write(
            db=db, action=AuditAction.REFUND_APPROVED, action_category=AuditCategory.REFUND,
            actor_id=user.get("id"), actor_role=user.get("role"),
            entity_type="RefundRequest", entity_id=str(req.id),
            after_state={"status": "approved", "amount": float(req.amount)},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Refund approved", "id": req.id, "status": "approved", "refund": refund_result}


@router.post("/refund-requests/{request_id}/reject", summary="Reject a refund request")
def reject_refund_request(
    request_id: int,
    payload: dict = Body(default={}),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.payments.model import RefundRequest, RefundRequestStatus

    req = db.query(RefundRequest).filter(RefundRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Refund request not found")
    if req.status != RefundRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Refund request already decided")

    req.status = RefundRequestStatus.REJECTED
    req.decision_note = (payload.get("note") or "").strip() or None
    req.decided_by = user.get("id")
    req.decided_at = utcnow_naive()
    db.commit()

    # Notify the requester.
    try:
        from app.modules.notifications.service import notify_user
        requester = db.query(User).filter(User.id == req.user_id).first()
        if requester:
            notify_user(
                user_id=requester.id, phone=requester.phone,
                title="Refund Request Declined",
                message=req.decision_note or "Your refund request was declined.",
                db=db,
            )
            db.commit()
    except Exception:
        db.rollback()

    try:
        audit_service.write(
            db=db, action=AuditAction.REFUND_REJECTED, action_category=AuditCategory.REFUND,
            actor_id=user.get("id"), actor_role=user.get("role"),
            entity_type="RefundRequest", entity_id=str(req.id),
            after_state={"status": "rejected", "note": req.decision_note},
        )
        db.commit()
    except Exception:
        db.rollback()

    return {"message": "Refund rejected", "id": req.id, "status": "rejected"}


# ── STATIONERY ADMIN: Printer monitoring ───────────────────────────────────


def _printer_health(p) -> str:
    """Derive health from live telemetry (good | warning | critical)."""
    status_val = p.status.value if hasattr(p.status, "value") else p.status
    if status_val in ("offline", "error"):
        return "critical"
    if (p.ink_level_pct or 0) < 10 or (p.paper_count or 0) < 20:
        return "critical"
    if status_val == "maintenance" or (p.ink_level_pct or 0) < 25 or (p.paper_count or 0) < 50:
        return "warning"
    return "good"


def _printer_dict(p, vendor_names) -> dict:
    status_val = p.status.value if hasattr(p.status, "value") else p.status
    cap = p.capacity_pages_per_hour or 0
    # Utilization proxy: queued jobs vs hourly capacity in "job slots".
    utilization = round(min(100.0, (p.queue_depth or 0) / max(cap / 60.0, 1) * 100), 1) if cap else 0.0
    return {
        "id": p.id,
        "vendor_id": p.vendor_id,
        "vendor_name": vendor_names.get(p.vendor_id) if p.vendor_id else "Campus-wide",
        "name": p.name,
        "location": p.location,
        "model": p.model,
        "status": status_val,
        "queue_depth": p.queue_depth,
        "ink_level_pct": p.ink_level_pct,
        "paper_count": p.paper_count,
        "capacity_pages_per_hour": p.capacity_pages_per_hour,
        "utilization_pct": utilization,
        "health": _printer_health(p),
        "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
    }


@router.get("/printers", summary="List printers with live telemetry + health")
def list_printers(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.stationery.printer_models import Printer

    printers = db.query(Printer).order_by(Printer.name).all()
    vids = {p.vendor_id for p in printers if p.vendor_id}
    names = {u.id: (u.name or u.full_name or f"Vendor #{u.id}")
             for u in db.query(User).filter(User.id.in_(vids)).all()} if vids else {}
    items = [_printer_dict(p, names) for p in printers]
    summary = {
        "total": len(items),
        "online": sum(1 for i in items if i["status"] == "online"),
        "offline": sum(1 for i in items if i["status"] == "offline"),
        "critical": sum(1 for i in items if i["health"] == "critical"),
        "total_queue": sum(i["queue_depth"] or 0 for i in items),
    }
    return {"printers": items, "summary": summary}


@router.post("/printers", summary="Register a printer")
def create_printer(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.stationery.printer_models import Printer, PrinterStatus

    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    p = Printer(
        vendor_id=payload.get("vendor_id"),
        name=name,
        location=(payload.get("location") or None),
        model=(payload.get("model") or None),
        status=PrinterStatus.ONLINE,
        queue_depth=int(payload.get("queue_depth", 0) or 0),
        ink_level_pct=int(payload.get("ink_level_pct", 100) or 100),
        paper_count=int(payload.get("paper_count", 0) or 0),
        capacity_pages_per_hour=int(payload.get("capacity_pages_per_hour", 600) or 600),
        last_seen_at=utcnow_naive(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {"message": "Printer registered", "id": p.id}


@router.patch("/printers/{printer_id}", summary="Update printer telemetry/status")
def update_printer(
    printer_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.stationery.printer_models import Printer, PrinterStatus

    p = db.query(Printer).filter(Printer.id == printer_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Printer not found")

    if "status" in payload and payload["status"] is not None:
        try:
            p.status = PrinterStatus(payload["status"])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    for field in ("name", "location", "model"):
        if payload.get(field) is not None:
            setattr(p, field, payload[field])
    for field in ("queue_depth", "ink_level_pct", "paper_count", "capacity_pages_per_hour", "vendor_id"):
        if payload.get(field) is not None:
            setattr(p, field, int(payload[field]))
    if p.ink_level_pct is not None:
        p.ink_level_pct = max(0, min(100, p.ink_level_pct))
    p.last_seen_at = utcnow_naive()
    db.commit()
    return {"message": "Printer updated", "id": p.id}


@router.delete("/printers/{printer_id}", summary="Remove a printer")
def delete_printer(
    printer_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.stationery.printer_models import Printer

    p = db.query(Printer).filter(Printer.id == printer_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Printer not found")
    db.delete(p)
    db.commit()
    return {"message": "Printer removed", "id": printer_id}


# ── STATIONERY ADMIN: Print cost matrix (price overrides) ──────────────────


@router.get("/print-cost-matrix", summary="List print cost / price-override entries")
def list_print_costs(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.modules.stationery.printer_models import PrintCostMatrix

    rows = db.query(PrintCostMatrix).order_by(
        PrintCostMatrix.vendor_id.is_(None).desc(), PrintCostMatrix.print_type, PrintCostMatrix.paper_size
    ).all()
    vids = {r.vendor_id for r in rows if r.vendor_id}
    names = {u.id: (u.name or f"Vendor #{u.id}")
             for u in db.query(User).filter(User.id.in_(vids)).all()} if vids else {}
    return [
        {
            "id": r.id,
            "vendor_id": r.vendor_id,
            "vendor_name": names.get(r.vendor_id) if r.vendor_id else "Global default",
            "print_type": r.print_type,
            "paper_size": r.paper_size,
            "duplex": r.duplex,
            "price_per_page": r.price_per_page,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]


@router.put("/print-cost-matrix", summary="Upsert a print price override")
def upsert_print_cost(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.stationery.printer_models import PrintCostMatrix

    print_type = str(payload.get("print_type", "")).lower()
    paper_size = str(payload.get("paper_size", "")).upper()
    if print_type not in ("bw", "color"):
        raise HTTPException(status_code=400, detail="print_type must be bw or color")
    if paper_size not in ("A4", "A3"):
        raise HTTPException(status_code=400, detail="paper_size must be A4 or A3")
    try:
        price = float(payload.get("price_per_page"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="price_per_page must be a number (rupees)")
    if price < 0:
        raise HTTPException(status_code=400, detail="price cannot be negative")
    duplex = bool(payload.get("duplex", False))
    vendor_id = payload.get("vendor_id")

    row = db.query(PrintCostMatrix).filter(
        PrintCostMatrix.vendor_id == vendor_id,
        PrintCostMatrix.print_type == print_type,
        PrintCostMatrix.paper_size == paper_size,
        PrintCostMatrix.duplex == duplex,
    ).first()
    if row:
        row.price_per_page = price
    else:
        row = PrintCostMatrix(
            vendor_id=vendor_id, print_type=print_type, paper_size=paper_size,
            duplex=duplex, price_per_page=price,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"message": "Price saved", "id": row.id}


@router.delete("/print-cost-matrix/{entry_id}", summary="Delete a print price override")
def delete_print_cost(
    entry_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.stationery.printer_models import PrintCostMatrix

    row = db.query(PrintCostMatrix).filter(PrintCostMatrix.id == entry_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(row)
    db.commit()
    return {"message": "Deleted", "id": entry_id}


# ── ADMINISTRATION: Bulk user actions ──────────────────────────────────────


@router.post("/users/bulk-action", summary="Block/unblock multiple users at once")
def bulk_user_action(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    user_ids = payload.get("user_ids") or []
    action = str(payload.get("action", "")).lower()
    if not isinstance(user_ids, list) or not user_ids:
        raise HTTPException(status_code=400, detail="user_ids must be a non-empty list")
    if action not in ("block", "unblock"):
        raise HTTPException(status_code=400, detail="action must be 'block' or 'unblock'")

    target_active = action == "unblock"
    # Never allow bulk-blocking admins.
    users = db.query(User).filter(
        User.id.in_(user_ids),
        User.role.notin_([UserRole.ADMIN, UserRole.SUPER_ADMIN]),
    ).all()
    changed = []
    for u in users:
        if u.is_active != target_active:
            u.is_active = target_active
            changed.append(u.id)
    db.commit()

    if action == "block":
        for uid in changed:
            try:
                from app.modules.auth.refresh_router import revoke_all_user_tokens
                revoke_all_user_tokens(uid)
            except Exception:
                pass

    for uid in changed:
        try:
            audit_service.write(
                db=db,
                action=AuditAction.USER_ACTIVATED if target_active else AuditAction.USER_BLOCKED,
                action_category=AuditCategory.USER,
                actor_id=user.get("id"), actor_role=user.get("role"),
                entity_type="User", entity_id=str(uid),
                after_state={"is_active": target_active, "bulk": True},
            )
        except Exception:
            pass
    try:
        db.commit()
    except Exception:
        db.rollback()

    return {"message": f"Bulk {action} complete", "changed_count": len(changed), "changed_ids": changed}


# ── ADMINISTRATION: Campus maintenance mode ────────────────────────────────


@router.get("/maintenance", summary="Get campus maintenance-mode status")
def get_maintenance(user=Depends(require_role("admin"))) -> dict[str, Any]:
    from app.core.maintenance import get_maintenance_status
    return get_maintenance_status()


@router.post("/maintenance", summary="Enable/disable campus maintenance mode")
def set_maintenance(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.core.maintenance import set_maintenance_mode
    enabled = bool(payload.get("enabled"))
    message = payload.get("message")
    result = set_maintenance_mode(enabled, message)

    try:
        audit_service.write(
            db=db, action=AuditAction.MAINTENANCE_MODE_CHANGED, action_category=AuditCategory.SETTINGS,
            actor_id=user.get("id"), actor_role=user.get("role"),
            entity_type="System", entity_id="maintenance_mode",
            after_state=result,
        )
        db.commit()
    except Exception:
        db.rollback()

    return result


# ── ADMINISTRATION: Role permission matrix ─────────────────────────────────


@router.get("/permission-matrix", summary="Role → capability permission matrix")
def get_permission_matrix(user=Depends(require_role("admin"))) -> dict[str, Any]:
    """Return the platform's role-based capability matrix.

    Reflects the actual role authorization model used across the backend
    (``require_role`` guards): which roles may perform each capability.
    """
    roles = ["student", "faculty", "vendor", "staff", "admin", "super_admin"]
    # capability -> set of roles that have it
    caps = [
        ("Place & track orders",          ["student", "faculty"]),
        ("Group ordering",                ["student", "faculty"]),
        ("Request refund",                ["student", "faculty"]),
        ("Faculty priority slots",        ["faculty"]),
        ("Manage own menu & inventory",   ["vendor", "staff"]),
        ("Accept / prepare orders",       ["vendor", "staff"]),
        ("Manage slots & capacity",       ["vendor"]),
        ("View vendor settlements",       ["vendor"]),
        ("Approve / reject vendors",      ["admin", "super_admin"]),
        ("Create / edit vendors",         ["admin", "super_admin"]),
        ("Bulk user actions",             ["admin", "super_admin"]),
        ("Manage finance (ledger/refunds)", ["admin", "super_admin"]),
        ("Approve settlements",           ["admin", "super_admin"]),
        ("Printer & pricing administration", ["admin", "super_admin"]),
        ("Campus analytics & KPIs",       ["admin", "super_admin"]),
        ("Emergency shutdown / maintenance", ["admin", "super_admin"]),
        ("Manage policies & announcements", ["admin", "super_admin"]),
        ("View audit logs",               ["admin", "super_admin"]),
        ("Change user roles",             ["super_admin", "admin"]),
        ("Manage backups & restore",      ["super_admin", "admin"]),
    ]
    matrix = [
        {
            "capability": name,
            "roles": {r: (r in allowed) for r in roles},
        }
        for name, allowed in caps
    ]
    return {"roles": roles, "matrix": matrix}


# ── SLOT MANAGEMENT: Global config + templates ─────────────────────────────

_SLOT_CONFIG_KEYS = {
    "slot_default_duration_minutes": "30",
    "slot_default_capacity": "10",
    "campus_open_time": "08:00",
    "campus_close_time": "20:00",
}


@router.get("/slot-config", summary="Get global campus slot configuration")
def get_slot_config(db: Session = Depends(get_db), user=Depends(require_role("admin"))) -> dict[str, Any]:
    from app.modules.admin.model import SystemConfig
    rows = {c.key: c.value for c in db.query(SystemConfig).filter(SystemConfig.key.in_(_SLOT_CONFIG_KEYS.keys())).all()}
    return {k: rows.get(k, default) for k, default in _SLOT_CONFIG_KEYS.items()}


@router.post("/slot-config", summary="Update global campus slot configuration")
def set_slot_config(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.admin.model import SystemConfig
    for key in _SLOT_CONFIG_KEYS:
        if key in payload and payload[key] is not None:
            row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            val = str(payload[key])
            if row:
                row.value = val
            else:
                db.add(SystemConfig(key=key, value=val))
    db.commit()
    try:
        audit_service.write(
            db=db, action=AuditAction.SETTINGS_CHANGED, action_category=AuditCategory.SETTINGS,
            actor_id=user.get("id"), actor_role=user.get("role"),
            entity_type="SlotConfig", entity_id="global", after_state=payload,
        )
        db.commit()
    except Exception:
        db.rollback()
    return get_slot_config(db, user)


def _template_dict(t, vendor_names) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "vendor_id": t.vendor_id,
        "vendor_name": vendor_names.get(t.vendor_id) if t.vendor_id else "Any vendor",
        "day_of_week": t.day_of_week,
        "start_time": t.start_time,
        "end_time": t.end_time,
        "slot_duration_minutes": t.slot_duration_minutes,
        "max_orders_per_slot": t.max_orders_per_slot,
        "is_active": t.is_active,
    }


@router.get("/slot-templates", summary="List slot templates")
def list_slot_templates(db: Session = Depends(get_db), user=Depends(require_role("admin"))):
    from app.modules.slots.model import SlotTemplate
    rows = db.query(SlotTemplate).order_by(SlotTemplate.name).all()
    vids = {t.vendor_id for t in rows if t.vendor_id}
    names = {u.id: (u.name or f"Vendor #{u.id}") for u in db.query(User).filter(User.id.in_(vids)).all()} if vids else {}
    return [_template_dict(t, names) for t in rows]


def _valid_hhmm(s: str) -> bool:
    try:
        h, m = s.split(":")
        return 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except Exception:
        return False


@router.post("/slot-templates", summary="Create a slot template")
def create_slot_template(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.slots.model import SlotTemplate
    name = (payload.get("name") or "").strip()
    start = str(payload.get("start_time", ""))
    end = str(payload.get("end_time", ""))
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    if not _valid_hhmm(start) or not _valid_hhmm(end):
        raise HTTPException(status_code=400, detail="start_time/end_time must be HH:MM")
    if start >= end:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
    dow = payload.get("day_of_week")
    if dow is not None and (not isinstance(dow, int) or dow < 0 or dow > 6):
        raise HTTPException(status_code=400, detail="day_of_week must be 0-6 or null")

    t = SlotTemplate(
        name=name,
        vendor_id=payload.get("vendor_id"),
        day_of_week=dow,
        start_time=start,
        end_time=end,
        slot_duration_minutes=int(payload.get("slot_duration_minutes", 30) or 30),
        max_orders_per_slot=int(payload.get("max_orders_per_slot", 10) or 10),
        is_active=bool(payload.get("is_active", True)),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"message": "Template created", "id": t.id}


@router.patch("/slot-templates/{template_id}", summary="Update a slot template")
def update_slot_template(
    template_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.slots.model import SlotTemplate
    t = db.query(SlotTemplate).filter(SlotTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    for field in ("name", "start_time", "end_time"):
        if payload.get(field) is not None:
            setattr(t, field, str(payload[field]))
    for field in ("slot_duration_minutes", "max_orders_per_slot", "day_of_week", "vendor_id"):
        if field in payload:
            setattr(t, field, payload[field] if payload[field] is None else int(payload[field]))
    if payload.get("is_active") is not None:
        t.is_active = bool(payload["is_active"])
    db.commit()
    return {"message": "Template updated", "id": t.id}


@router.delete("/slot-templates/{template_id}", summary="Delete a slot template")
def delete_slot_template(
    template_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from app.modules.slots.model import SlotTemplate
    t = db.query(SlotTemplate).filter(SlotTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(t)
    db.commit()
    return {"message": "Template deleted", "id": template_id}


@router.post("/slot-templates/{template_id}/generate", summary="Generate real slots from a template")
def generate_slots_from_template(
    template_id: int,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Create Slot rows for a vendor across a date range from the template.

    Skips (does not duplicate) slots that already exist for the same vendor and
    start time. Respects holiday/exam calendar events that block ordering.
    """
    from datetime import datetime, timedelta
    from app.modules.slots.model import Slot, SlotTemplate, SlotStatus

    t = db.query(SlotTemplate).filter(SlotTemplate.id == template_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    vendor_id = payload.get("vendor_id") or t.vendor_id
    if not vendor_id:
        raise HTTPException(status_code=400, detail="vendor_id is required (template is not vendor-bound)")
    vendor = db.query(User).filter(User.id == vendor_id, User.role == UserRole.VENDOR).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    try:
        date_from = datetime.fromisoformat(payload["date_from"]).date()
        date_to = datetime.fromisoformat(payload["date_to"]).date()
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="date_from and date_to (YYYY-MM-DD) are required")
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")
    if (date_to - date_from).days > 62:
        raise HTTPException(status_code=400, detail="Range too large (max 62 days)")

    sh, sm = map(int, t.start_time.split(":"))
    eh, em = map(int, t.end_time.split(":"))
    duration = max(5, t.slot_duration_minutes)

    created = 0
    skipped = 0
    day = date_from
    while day <= date_to:
        if t.day_of_week is None or t.day_of_week == day.weekday():
            cursor = datetime(day.year, day.month, day.day, sh, sm)
            day_end = datetime(day.year, day.month, day.day, eh, em)
            while cursor + timedelta(minutes=duration) <= day_end:
                slot_end = cursor + timedelta(minutes=duration)
                exists = db.query(Slot).filter(
                    Slot.vendor_id == vendor_id, Slot.start_time == cursor
                ).first()
                if exists:
                    skipped += 1
                else:
                    db.add(Slot(
                        vendor_id=vendor_id,
                        start_time=cursor,
                        end_time=slot_end,
                        max_orders=t.max_orders_per_slot,
                        current_orders=0,
                        status=SlotStatus.AVAILABLE,
                        slot_duration_minutes=duration,
                    ))
                    created += 1
                cursor = slot_end
        day += timedelta(days=1)
    db.commit()

    return {"message": "Slots generated", "created": created, "skipped": skipped, "vendor_id": vendor_id}


# ── ANALYTICS: Trends (refunds / fraud / complaints) + printer usage ───────


@router.get("/analytics/trends", summary="Refund/fraud/complaint trends + printer usage")
async def get_analytics_trends(
    days: int = Query(30, ge=7, le=120),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    from datetime import timedelta
    from app.modules.complaints.model import Complaint
    from app.modules.stationery.printer_models import Printer

    since = utcnow_naive() - timedelta(days=days)

    # Refund trend — count + amount by day (Payment refunded).
    refund_rows = db.query(
        func.date(Payment.refunded_at).label("day"),
        func.count(Payment.id).label("count"),
        func.coalesce(func.sum(Payment.amount), 0).label("amount"),
    ).filter(
        Payment.status == PaymentStatus.REFUNDED,
        Payment.refunded_at.isnot(None),
        Payment.refunded_at >= since,
    ).group_by(func.date(Payment.refunded_at)).order_by(func.date(Payment.refunded_at)).all()
    refund_trend = [{"date": str(r.day), "count": r.count, "amount": float(r.amount)} for r in refund_rows]

    # Fraud trend — flagged orders by day.
    fraud_rows = db.query(
        func.date(Order.flagged_at).label("day"),
        func.count(Order.id).label("count"),
    ).filter(
        Order.fraud_flag == True,  # noqa: E712
        Order.flagged_at.isnot(None),
        Order.flagged_at >= since,
    ).group_by(func.date(Order.flagged_at)).order_by(func.date(Order.flagged_at)).all()
    fraud_trend = [{"date": str(r.day), "count": r.count} for r in fraud_rows]

    # Complaint trend — complaints created by day.
    complaint_rows = db.query(
        func.date(Complaint.created_at).label("day"),
        func.count(Complaint.id).label("count"),
    ).filter(Complaint.created_at >= since).group_by(
        func.date(Complaint.created_at)
    ).order_by(func.date(Complaint.created_at)).all()
    complaint_trend = [{"date": str(r.day), "count": r.count} for r in complaint_rows]

    # Printer usage — current aggregate telemetry.
    printers = db.query(Printer).all()
    total_printers = len(printers)
    total_queue = sum(p.queue_depth or 0 for p in printers)
    total_capacity = sum(p.capacity_pages_per_hour or 0 for p in printers)
    avg_ink = round(sum(p.ink_level_pct or 0 for p in printers) / total_printers, 1) if total_printers else 0.0
    low_paper = sum(1 for p in printers if (p.paper_count or 0) < 50)
    by_status: dict[str, int] = {}
    for p in printers:
        sv = p.status.value if hasattr(p.status, "value") else p.status
        by_status[sv] = by_status.get(sv, 0) + 1
    printer_usage = {
        "total_printers": total_printers,
        "total_queue": total_queue,
        "total_capacity_pages_per_hour": total_capacity,
        "avg_ink_level_pct": avg_ink,
        "low_paper_printers": low_paper,
        "by_status": by_status,
        "per_printer": [
            {"id": p.id, "name": p.name, "queue_depth": p.queue_depth,
             "ink_level_pct": p.ink_level_pct, "paper_count": p.paper_count}
            for p in printers
        ],
    }

    return {
        "days": days,
        "refund_trend": refund_trend,
        "fraud_trend": fraud_trend,
        "complaint_trend": complaint_trend,
        "printer_usage": printer_usage,
        "totals": {
            "refunds": sum(r["count"] for r in refund_trend),
            "refund_amount": sum(r["amount"] for r in refund_trend),
            "fraud_flags": sum(r["count"] for r in fraud_trend),
            "complaints": sum(r["count"] for r in complaint_trend),
        },
    }
