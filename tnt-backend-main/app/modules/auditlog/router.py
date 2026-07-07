from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import require_role
from app.modules.auditlog import service
from app.modules.auditlog.schemas import AuditLogListResponse, AuditStatsResponse, AuditTimelineResponse

router = APIRouter(prefix="/admin/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    actor_id: Optional[int] = Query(None),
    actor_role: Optional[str] = Query(None),
    action_category: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date string"),
    date_to: Optional[str] = Query(None, description="ISO date string"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    """Read-only endpoint. No write access — logs are written internally only."""
    return service.list_audit_logs(
        db=db,
        page=page,
        page_size=page_size,
        actor_id=actor_id,
        actor_role=actor_role,
        action_category=action_category,
        entity_type=entity_type,
        entity_id=entity_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )

@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    from app.core.redis_cache import cache_service
    return await cache_service.get_or_set(
        category="analytics",
        identifier="audit_summary_stats",
        fetch_func=lambda: service.get_summary_stats(db),
        ttl=60
    )

@router.get("/timeline/{actor_id}", response_model=AuditTimelineResponse)
def get_audit_timeline(
    actor_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    return service.get_timeline(db, actor_id, page, page_size)

@router.get("/export")
def export_audit_logs(
    actor_id: Optional[int] = Query(None),
    actor_role: Optional[str] = Query(None),
    action_category: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
):
    import csv
    import io
    from fastapi.responses import StreamingResponse

    logs_data = service.list_audit_logs(
        db=db,
        page=1,
        page_size=10000,
        actor_id=actor_id,
        actor_role=actor_role,
        action_category=action_category,
        date_from=date_from,
        date_to=date_to,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Actor ID", "Actor Name", "Actor Role", "Action", "Category", "Entity Type", "Entity ID", "IP Address"])
    
    for log in logs_data["logs"]:
        writer.writerow([
            log["id"],
            log["created_at"].isoformat() if log["created_at"] else "",
            log["actor_id"] or "",
            log["actor_name"] or "",
            log["actor_role"] or "",
            log["action"],
            log["action_category"],
            log["entity_type"] or "",
            log["entity_id"] or "",
            log["ip_address"] or ""
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
    )