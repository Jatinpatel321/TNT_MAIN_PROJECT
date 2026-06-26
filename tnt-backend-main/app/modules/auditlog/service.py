"""Audit log service — write and query immutable audit entries."""
from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.modules.auditlog.model import AuditLog


# Action constants
class AuditAction:
    LOGIN_SUCCESS = "auth.login_success"
    LOGIN_FAILED = "auth.login_failed"
    USER_BLOCKED = "user.blocked"
    USER_ACTIVATED = "user.activated"
    USER_ROLE_CHANGED = "user.role_changed"
    VENDOR_APPROVED = "vendor.approved"
    VENDOR_REJECTED = "vendor.rejected"
    VENDOR_SUSPENDED = "vendor.suspended"
    ORDER_OVERRIDE = "order.status_overridden"
    ORDER_CANCELLED = "order.cancelled_by_admin"
    POLICY_UPDATED = "policy.updated"
    FACULTY_POLICY_UPDATED = "policy.faculty_priority_updated"
    VOUCHER_CREATED = "voucher.created"
    VOUCHER_DELETED = "voucher.deleted"
    ANNOUNCEMENT_SENT = "announcement.sent"


class AuditCategory:
    AUTH = "auth"
    USER = "user"
    VENDOR = "vendor"
    ORDER = "order"
    POLICY = "policy"
    VOUCHER = "voucher"
    ANNOUNCEMENT = "announcement"


def write(
    db: Session,
    action: str,
    action_category: str,
    actor_id: Optional[int] = None,
    actor_role: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    before_state: Optional[Dict[str, Any]] = None,
    after_state: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Write a single immutable audit log entry. Uses db.flush() so caller controls commit."""
    ip = None
    ua = None
    if request:
        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
        ua = request.headers.get("User-Agent", "")[:255]

    entry = AuditLog(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        action_category=action_category,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before_state=before_state,
        after_state=after_state,
        metadata=metadata,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(entry)
    db.flush()
    return entry


def list_audit_logs(
    db: Session,
    page: int = 1,
    page_size: int = 50,
    actor_id: Optional[int] = None,
    action_category: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    from datetime import datetime

    query = db.query(AuditLog)

    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)
    if action_category:
        query = query.filter(AuditLog.action_category == action_category)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if search:
        query = query.filter(AuditLog.action.ilike(f"%{search}%"))
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.fromisoformat(date_to))

    total = query.count()
    offset = (page - 1) * page_size
    logs = (
        query.order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }