"""Audit log service — write and query immutable audit entries."""
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.modules.auditlog.model import AuditLog
from app.modules.users.model import User


def _json_safe(value: Any) -> Any:
    """Recursively convert Decimal (money) values so the JSON before/after
    snapshot columns can serialize them regardless of DB engine/dialect."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


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
    VENDOR_CREATED = "vendor.created"
    VENDOR_UPDATED = "vendor.updated"
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
    REFUND_APPROVED = "refund.approved"
    LEDGER_ADJUSTED = "ledger.adjusted"
    SETTLEMENT_APPROVED = "settlement.approved"
    MAINTENANCE_MODE_CHANGED = "settings.maintenance_mode"
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
        before_state=_json_safe(before_state),
        after_state=_json_safe(after_state),
        meta=_json_safe(metadata),
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
        log_dict = {
            "id": log.id,
            "actor_id": log.actor_id,
            "actor_role": log.actor_role,
            "action": log.action,
            "action_category": log.action_category,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "before_state": log.before_state,
            "after_state": log.after_state,
            "metadata": log.meta if isinstance(log.meta, dict) else (log.meta or {}),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at,
            "actor_name": actor_name,
        }
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
        log_dict = {
            "id": log.id,
            "actor_id": log.actor_id,
            "actor_role": log.actor_role,
            "action": log.action,
            "action_category": log.action_category,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "before_state": log.before_state,
            "after_state": log.after_state,
            "metadata": log.meta if isinstance(log.meta, dict) else (log.meta or {}),
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at,
            "actor_name": actor_name,
        }
        logs.append(log_dict)

    return {
        "logs": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


def get_summary_stats(db: Session) -> Dict[str, Any]:
    from sqlalchemy import func, case, Date, cast
    from datetime import datetime, timedelta
    
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)
    last_week = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # 1. Aggregate query for total, today, weekly, and 30-day counts
    stats = db.query(
        func.count(AuditLog.id).label("total"),
        func.sum(case((AuditLog.created_at >= yesterday, 1), else_=0)).label("today"),
        func.sum(case((AuditLog.created_at >= last_week, 1), else_=0)).label("week"),
        func.sum(case((AuditLog.created_at >= last_30d, 1), else_=0)).label("total_30d"),
        func.count(func.distinct(case((AuditLog.created_at >= last_30d, AuditLog.actor_id), else_=None))).label("active_users_30d")
    ).first()
    
    total_events = int(stats.total or 0)
    today_events = int(stats.today or 0)
    week_events = int(stats.week or 0)
    total_logs_30d = int(stats.total_30d or 0)
    active_users_30d = int(stats.active_users_30d or 0)
    
    # 2. Critical actions in last 30 days
    critical_action_names = [
        AuditAction.LOGIN_FAILED,
        AuditAction.USER_BLOCKED,
        AuditAction.USER_ROLE_CHANGED,
        AuditAction.VENDOR_SUSPENDED,
        AuditAction.VENDOR_REJECTED,
        AuditAction.ORDER_CANCELLED,
        AuditAction.MAINTENANCE_MODE_CHANGED,
        "security.target_blocked",
        "emergency.shutdown_enabled",
    ]
    critical_actions_30d = db.query(func.count(AuditLog.id)).filter(
        AuditLog.created_at >= last_30d,
        AuditLog.action.in_(critical_action_names)
    ).scalar() or 0
    
    # 3. Category counts
    category_counts_rows = db.query(AuditLog.action_category, func.count(AuditLog.id)).group_by(AuditLog.action_category).all()
    category_counts = {str(c[0]): int(c[1]) for c in category_counts_rows if c[0]}
    
    # Category counts for 30d (for actions_by_category)
    cat_30d_rows = db.query(AuditLog.action_category, func.count(AuditLog.id)).filter(AuditLog.created_at >= last_30d).group_by(AuditLog.action_category).all()
    actions_by_category = {str(c[0]): int(c[1]) for c in cat_30d_rows if c[0]}
    if not actions_by_category and category_counts:
        actions_by_category = dict(category_counts)
    
    auth_events = category_counts.get(AuditCategory.AUTH, 0)
    order_events = category_counts.get(AuditCategory.ORDER, 0)
    flagged_events = category_counts.get(AuditCategory.POLICY, 0) + category_counts.get(AuditCategory.REFUND, 0)
    
    # Top actors
    top_actors_query = db.query(
        AuditLog.actor_id, User.full_name, func.count(AuditLog.id).label("event_count")
    ).outerjoin(User, AuditLog.actor_id == User.id).group_by(AuditLog.actor_id, User.full_name).order_by(desc("event_count")).limit(5).all()
    
    top_actors = [
        {"actor_id": r[0], "actor_name": r[1] or "System", "event_count": int(r[2])}
        for r in top_actors_query
    ]
    
    # 4. Daily trend for last 30 days
    day_counts_raw = db.query(
        cast(AuditLog.created_at, Date).label("d"),
        func.count(AuditLog.id).label("cnt")
    ).filter(AuditLog.created_at >= last_30d).group_by(cast(AuditLog.created_at, Date)).all()
    day_counts_map = {str(r[0]): int(r[1]) for r in day_counts_raw if r[0]}
    
    actions_by_day = []
    for i in range(29, -1, -1):
        day_date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        actions_by_day.append({
            "date": day_date,
            "count": day_counts_map.get(day_date, 0)
        })
    
    return {
        "total_events": total_events,
        "today_events": today_events,
        "week_events": week_events,
        "auth_events": auth_events,
        "order_events": order_events,
        "flagged_events": flagged_events,
        "category_counts": category_counts,
        "top_actors": top_actors,
        "total_logs_30d": total_logs_30d,
        "active_users_30d": active_users_30d,
        "critical_actions_30d": int(critical_actions_30d),
        "actions_by_category": actions_by_category,
        "actions_by_day": actions_by_day,
    }