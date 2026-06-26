"""Smart Demand Dashboard - API Router."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.demand_dashboard_service import DemandDashboardService

router = APIRouter(prefix="/vendors/demand-dashboard", tags=["Vendor Demand Dashboard"])


def _get_vendor_id(user=Depends(get_current_user), db: Session = Depends(get_db)) -> int:
    """Resolve the authenticated user's vendor ID."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> DemandDashboardService:
    return DemandDashboardService(db)


@router.get("/", summary="Get full demand dashboard")
def get_full_dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get complete smart demand dashboard with demand overview, stock prediction, and rush prediction."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_full_dashboard(vendor_id)


@router.get("/overview", summary="Get demand overview")
def get_demand_overview(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get demand overview with today's orders, predictions, and trends."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_demand_overview(vendor_id)


@router.get("/stock-prediction", summary="Get stock prediction")
def get_stock_prediction(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get stock requirements prediction with urgency levels and restock recommendations."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_stock_prediction(vendor_id)


@router.get("/rush-prediction", summary="Get rush prediction")
def get_rush_prediction(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get rush period predictions for today with recommended staffing."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_rush_prediction(vendor_id)
