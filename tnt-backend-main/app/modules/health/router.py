from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.deps import get_db
from app.core.security import require_role
from app.modules.health import service

router = APIRouter(prefix="/admin/health", tags=["Admin System Health"])

@router.get("/metrics", response_model=Dict[str, Any], summary="Get detailed system health metrics")
def get_health_metrics(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """
    Run diagnostics and return detailed diagnostics for all 8 subsystems
    along with historical performance snapshots.
    """
    return service.run_health_checks(db)


@router.get("/status", response_model=Dict[str, str], summary="Get overall system health status")
def get_health_status(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """
    Returns minimal system health status indicator: healthy | degraded | unhealthy.
    """
    result = service.run_health_checks(db)
    return {"status": result.get("status", "healthy")}
