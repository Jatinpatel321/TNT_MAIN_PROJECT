from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, or_, func
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import require_role
from app.core.time_utils import utcnow_naive
from app.modules.auditlog.service import write as write_audit_log, AuditAction, AuditCategory
from app.modules.fraud.model import FraudAlert
from app.modules.fraud.fraud_detection_service import FraudDetectionService
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.orders.model import Order

router = APIRouter(prefix="/admin/fraud", tags=["Admin Fraud Detection"])


# ── Pydantic Schemas ─────────────────────────────────────────────────────────

class FraudAlertSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int] = None
    vendor_id: Optional[int] = None
    order_id: Optional[int] = None
    alert_type: str
    severity: str
    score: float
    description: Optional[str] = None
    status: str
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    vendor_name: Optional[str] = None


class ResolveAlertRequest(BaseModel):
    notes: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=Dict[str, Any])
def list_fraud_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    alert_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """List fraud alerts with robust server-side paging and filtering."""
    query = db.query(FraudAlert)

    if alert_type:
        query = query.filter(FraudAlert.alert_type == alert_type)
    if severity:
        query = query.filter(FraudAlert.severity == severity)
    if status:
        query = query.filter(FraudAlert.status == status)
    if search:
        query = query.filter(
            or_(
                FraudAlert.description.ilike(f"%{search}%"),
                FraudAlert.alert_type.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    alerts_raw = (
        query.order_by(desc(FraudAlert.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    alerts_list = []
    for alert in alerts_raw:
        user_phone = None
        user_name = None
        vendor_name = None

        if alert.user_id:
            u = db.query(User).filter(User.id == alert.user_id).first()
            if u:
                user_phone = u.phone
                user_name = u.name or u.full_name

        if alert.vendor_id:
            v = db.query(Vendor).filter(Vendor.owner_id == alert.vendor_id).first()
            if v:
                vendor_name = v.vendor_name
            else:
                # fallback to user role checking
                vu = db.query(User).filter(User.id == alert.vendor_id).first()
                if vu:
                    vendor_name = vu.name or vu.full_name

        alert_dict = {
            "id": alert.id,
            "user_id": alert.user_id,
            "vendor_id": alert.vendor_id,
            "order_id": alert.order_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "score": alert.score,
            "description": alert.description,
            "status": alert.status,
            "resolution_notes": alert.resolution_notes,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at,
            "user_phone": user_phone,
            "user_name": user_name,
            "vendor_name": vendor_name,
        }
        alerts_list.append(alert_dict)

    return {
        "alerts": alerts_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/alerts/{alert_id}", response_model=Dict[str, Any])
def get_fraud_alert_detail(
    alert_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Retrieve detailed view of a fraud alert with context."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    user_details = None
    vendor_details = None
    order_details = None

    if alert.user_id:
        u = db.query(User).filter(User.id == alert.user_id).first()
        if u:
            # calculate cumulative score
            cumulative_score = FraudDetectionService.calculate_user_fraud_score(db, u.id)
            user_details = {
                "id": u.id,
                "name": u.name or u.full_name,
                "phone": u.phone,
                "role": u.role.value,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "cumulative_fraud_score": cumulative_score,
            }

    if alert.vendor_id:
        v = db.query(Vendor).filter(Vendor.owner_id == alert.vendor_id).first()
        vu = db.query(User).filter(User.id == alert.vendor_id).first()
        if vu:
            vendor_details = {
                "id": vu.id,
                "name": v.vendor_name if v else (vu.name or vu.full_name),
                "phone": vu.phone,
                "status": v.status.value if v else ("active" if vu.is_active else "inactive"),
                "is_active": vu.is_active,
            }

    if alert.order_id:
        o = db.query(Order).filter(Order.id == alert.order_id).first()
        if o:
            order_details = {
                "id": o.id,
                "status": o.status.value,
                "total_amount": o.total_amount,
                "created_at": o.created_at,
                "booking_type": o.booking_type,
            }

    return {
        "alert": {
            "id": alert.id,
            "user_id": alert.user_id,
            "vendor_id": alert.vendor_id,
            "order_id": alert.order_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "score": alert.score,
            "description": alert.description,
            "status": alert.status,
            "resolution_notes": alert.resolution_notes,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at,
        },
        "user": user_details,
        "vendor": vendor_details,
        "order": order_details,
    }


@router.post("/alerts/{alert_id}/resolve")
def resolve_fraud_alert(
    alert_id: int,
    payload: ResolveAlertRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Mark a fraud alert as Resolved with notes."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    before = {"status": alert.status, "resolution_notes": alert.resolution_notes}
    alert.status = "resolved"
    alert.resolution_notes = payload.notes
    alert.updated_at = utcnow_naive()
    db.commit()

    # Log to audit history
    try:
        write_audit_log(
            db=db,
            action="fraud.alert_resolved",
            action_category="security",
            actor_id=admin.get("id"),
            actor_role=admin.get("role"),
            entity_type="FraudAlert",
            entity_id=str(alert.id),
            before_state=before,
            after_state={"status": "resolved", "resolution_notes": payload.notes},
        )
        db.commit()
    except Exception:
        pass

    return {"success": True, "message": "Alert marked as resolved", "alert_id": alert_id}


@router.post("/alerts/{alert_id}/false-positive")
def mark_alert_false_positive(
    alert_id: int,
    payload: ResolveAlertRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Mark a fraud alert as a False Positive."""
    alert = db.query(FraudAlert).filter(FraudAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    before = {"status": alert.status, "resolution_notes": alert.resolution_notes}
    alert.status = "false_positive"
    alert.resolution_notes = payload.notes
    alert.updated_at = utcnow_naive()
    db.commit()

    # Log to audit history
    try:
        write_audit_log(
            db=db,
            action="fraud.alert_false_positive",
            action_category="security",
            actor_id=admin.get("id"),
            actor_role=admin.get("role"),
            entity_type="FraudAlert",
            entity_id=str(alert.id),
            before_state=before,
            after_state={"status": "false_positive", "resolution_notes": payload.notes},
        )
        db.commit()
    except Exception:
        pass

    return {"success": True, "message": "Alert marked as false positive", "alert_id": alert_id}


@router.post("/users/{user_id}/blacklist")
def blacklist_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Blacklist a user by setting is_active = False and revoking refresh tokens."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not target_user.is_active:
        return {"success": True, "message": "User is already blacklisted/inactive"}

    before = {"is_active": target_user.is_active}
    target_user.is_active = False
    db.commit()

    # Revoke tokens
    try:
        from app.modules.auth.refresh_router import revoke_all_user_tokens
        revoke_all_user_tokens(user_id)
    except Exception:
        pass

    # Audit logging
    try:
        write_audit_log(
            db=db,
            action=AuditAction.USER_BLOCKED,
            action_category=AuditCategory.USER,
            actor_id=admin.get("id"),
            actor_role=admin.get("role"),
            entity_type="User",
            entity_id=str(user_id),
            before_state=before,
            after_state={"is_active": False},
        )
        db.commit()
    except Exception:
        pass

    return {"success": True, "message": "User successfully blacklisted"}


@router.post("/vendors/{vendor_id}/blacklist")
def blacklist_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Blacklist a vendor business entity (and their user account)."""
    # Look up by user_id or vendor_id
    vendor_obj = db.query(Vendor).filter(
        or_(Vendor.vendor_id == vendor_id, Vendor.owner_id == vendor_id)
    ).first()

    owner_id = vendor_id
    if vendor_obj:
        owner_id = vendor_obj.owner_id
        vendor_obj.status = VendorStatus.SUSPENDED

    vendor_user = db.query(User).filter(User.id == owner_id).first()
    if not vendor_user:
        raise HTTPException(status_code=404, detail="Vendor user not found")

    before_user = {"is_active": vendor_user.is_active}
    vendor_user.is_active = False
    db.commit()

    # Revoke tokens
    try:
        from app.modules.auth.refresh_router import revoke_all_user_tokens
        revoke_all_user_tokens(owner_id)
    except Exception:
        pass

    # Audit logging
    try:
        write_audit_log(
            db=db,
            action=AuditAction.VENDOR_SUSPENDED,
            action_category=AuditCategory.VENDOR,
            actor_id=admin.get("id"),
            actor_role=admin.get("role"),
            entity_type="Vendor",
            entity_id=str(owner_id),
            before_state=before_user,
            after_state={"is_active": False, "status": "suspended"},
        )
        db.commit()
    except Exception:
        pass

    return {"success": True, "message": "Vendor successfully blacklisted/suspended"}


@router.post("/scan")
def trigger_fraud_scan(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Manually run a full system audit scan to catch retrospective scam attempts."""
    alert_count = FraudDetectionService.run_full_system_scan(db)
    return {"success": True, "alerts_found": alert_count}


@router.get("/metrics")
def get_fraud_metrics(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Retrieve summarized statistics and aggregations for the Fraud Dashboard."""
    # Count totals
    total_alerts = db.query(FraudAlert).count()
    pending_alerts = db.query(FraudAlert).filter(FraudAlert.status == "pending").count()
    resolved_alerts = db.query(FraudAlert).filter(FraudAlert.status == "resolved").count()
    false_positives = db.query(FraudAlert).filter(FraudAlert.status == "false_positive").count()
    critical_alerts = (
        db.query(FraudAlert)
        .filter(FraudAlert.status == "pending", FraudAlert.severity == "critical")
        .count()
    )

    # Blacklisted users (is_active = False and not admin role)
    blacklisted_users = (
        db.query(User)
        .filter(User.is_active == False, User.role == UserRole.STUDENT)
        .count()
    )
    blacklisted_vendors = (
        db.query(User)
        .filter(User.is_active == False, User.role == UserRole.VENDOR)
        .count()
    )

    # Severity distribution
    severity_dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    severity_rows = (
        db.query(FraudAlert.severity, func.count(FraudAlert.id))
        .filter(FraudAlert.status == "pending")
        .group_by(FraudAlert.severity)
        .all()
    )
    for r in severity_rows:
        severity_dist[r[0]] = r[1]

    # Type distribution
    type_dist = {}
    type_rows = (
        db.query(FraudAlert.alert_type, func.count(FraudAlert.id))
        .group_by(FraudAlert.alert_type)
        .all()
    )
    for r in type_rows:
        type_dist[r[0]] = r[1]

    # Activity list
    recent_alerts_raw = (
        db.query(FraudAlert)
        .order_by(desc(FraudAlert.created_at))
        .limit(10)
        .all()
    )
    recent_activity = []
    for alert in recent_alerts_raw:
        u_name = "System"
        if alert.user_id:
            u = db.query(User).filter(User.id == alert.user_id).first()
            if u:
                u_name = u.name or u.phone

        recent_activity.append({
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "user_name": u_name,
            "created_at": alert.created_at,
            "status": alert.status,
        })

    return {
        "summary": {
            "total_alerts": total_alerts,
            "pending_alerts": pending_alerts,
            "resolved_alerts": resolved_alerts,
            "false_positives": false_positives,
            "critical_alerts": critical_alerts,
            "blacklisted_users": blacklisted_users,
            "blacklisted_vendors": blacklisted_vendors,
        },
        "severity_distribution": severity_dist,
        "type_distribution": type_dist,
        "recent_activity": recent_activity,
    }
