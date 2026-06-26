from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import require_role
from app.modules.auditlog import service
from app.modules.auditlog.schemas import AuditLogListResponse

router = APIRouter(prefix="/admin/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    actor_id: Optional[int] = Query(None),
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
        action_category=action_category,
        entity_type=entity_type,
        entity_id=entity_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )