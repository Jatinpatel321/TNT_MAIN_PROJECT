"""Audit log service — write and query immutable audit entries."""
from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.modules.auditlog.model import AuditLog
from app.modules.users.model import User


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
    ORDER_UPDATED = "order.updated"
    POLICY_UPDATED = "policy.updated"
    FACULTY_POLICY_UPDATED = "policy.faculty_priority_updated"
    VOUCHER_CREATED = "voucher.created"
    VOUCHER_DELETED = "voucher.deleted"
    ANNOUNCEMENT_SENT = "announcement.sent"
    REFUND_ISSUED = "refund.issued"
    REFUND_REJECTED = "refund.rejected"
    MENU_ITEM_CREATED = "menu.item_created"
    MENU_ITEM_UPDATED = "menu.item_updated"
    MENU_ITEM_DELETED = "menu.item_deleted"
    INVENTORY_UPDATED = "inventory.updated"
    INVENTORY_RESTOCKED = "inventory.restocked"
    SETTINGS_CHANGED = "settings.changed"
    USER_LOGIN = "auth.user_login"
    VENDOR_LOGIN = "auth.vendor_login"
    ADMIN_LOGIN = "auth.admin_login"


class AuditCategory:
    AUTH = "auth"
    USER = "user"
    VENDOR = "vendor"
    ORDER = "order"
    POLICY = "policy"
    VOUCHER = "voucher"
    ANNOUNCEMENT = "announcement"
    REFUND = "refund"
    MENU = "menu"
    INVENTORY = "inventory"
    SETTINGS = "settings"


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
    actor_role: Optional[str] = None,
    action_category: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Dict[str, Any]:
    from datetime import datetime
    from sqlalchemy import or_

    # Count query (no join)
    from sqlalchemy import func
    total_query = db.query(func.count(AuditLog.id))

    filters = []
    if actor_id:
        filters.append(AuditLog.actor_id == actor_id)
    if actor_role:
        filters.append(AuditLog.actor_role == actor_role)
    if action_category:
        filters.append(AuditLog.action_category == action_category)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    if search:
        search_filter = f"%{search}%"
        filters.append(
            or_(
                AuditLog.action.ilike(search_filter),
                AuditLog.entity_type.ilike(search_filter),
                AuditLog.entity_id.ilike(search_filter)
            )
        )
    if date_from:
        filters.append(AuditLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        filters.append(AuditLog.created_at <= datetime.fromisoformat(date_to))

    if filters:
        total_query = total_query.filter(*filters)
    total = total_query.scalar()

    # Data query with outer join
    query = db.query(AuditLog, User.full_name.label("actor_name")).outerjoin(User, AuditLog.actor_id == User.id)
    if filters:
        query = query.filter(*filters)

    offset = (page - 1) * page_size
    results = (
        query.order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    
    logs = []
    for log, actor_name in results:
        log_dict = {c.name: getattr(log, c.name) for c in log.__table__.columns}
        log_dict["actor_name"] = actor_name
        logs.append(log_dict)

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


def get_timeline(db: Session, actor_id: int, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    from sqlalchemy import func
    total = db.query(func.count(AuditLog.id)).filter(AuditLog.actor_id == actor_id).scalar()

    query = db.query(AuditLog, User.full_name.label("actor_name")).outerjoin(User, AuditLog.actor_id == User.id)
    query = query.filter(AuditLog.actor_id == actor_id)
    offset = (page - 1) * page_size
    results = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(page_size).all()
    
    logs = []
    for log, actor_name in results:
        log_dict = {c.name: getattr(log, c.name) for c in log.__table__.columns}
        log_dict["actor_name"] = actor_name
        logs.append(log_dict)

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


def get_summary_stats(db: Session) -> Dict[str, Any]:
    from sqlalchemy import func, case
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    last_week = now - timedelta(days=7)
    
    # 1. Single aggregate query for total, today, and weekly counts
    stats = db.query(
        func.count(AuditLog.id).label("total"),
        func.sum(case((AuditLog.created_at >= yesterday, 1), else_=0)).label("today"),
        func.sum(case((AuditLog.created_at >= last_week, 1), else_=0)).label("week")
    ).first()
    
    total_events = int(stats.total or 0)
    today_events = int(stats.today or 0)
    week_events = int(stats.week or 0)
    
    # 2. Category counts in one query (helps avoid separate DB calls for AUTH/ORDER/POLICY/REFUND counts)
    category_counts_rows = db.query(AuditLog.action_category, func.count(AuditLog.id)).group_by(AuditLog.action_category).all()
    category_counts = {c[0]: c[1] for c in category_counts_rows}
    
    auth_events = category_counts.get(AuditCategory.AUTH, 0)
    order_events = category_counts.get(AuditCategory.ORDER, 0)
    flagged_events = category_counts.get(AuditCategory.POLICY, 0) + category_counts.get(AuditCategory.REFUND, 0)
    
    # Top actors
    top_actors_query = db.query(
        AuditLog.actor_id, User.full_name, func.count(AuditLog.id).label("event_count")
    ).outerjoin(User, AuditLog.actor_id == User.id).group_by(AuditLog.actor_id, User.full_name).order_by(desc("event_count")).limit(5).all()
    
    top_actors = [
        {"actor_id": r[0], "actor_name": r[1] or "System", "event_count": r[2]}
        for r in top_actors_query
    ]
    
    return {
        "total_events": total_events,
        "today_events": today_events,
        "week_events": week_events,
        "auth_events": auth_events,
        "order_events": order_events,
        "flagged_events": flagged_events,
        "category_counts": category_counts,
        "top_actors": top_actors,
    }