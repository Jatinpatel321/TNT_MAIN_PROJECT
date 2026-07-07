"""
Peak Hour Prediction API Router
================================

Endpoints:
GET /vendor/peak-hours/predict - Get complete peak hour predictions
GET /vendor/peak-hours/rush - Get rush hours
GET /vendor/peak-hours/quiet - Get quiet hours
GET /vendor/peak-hours/heatmap - Get peak hour heatmap
GET /vendor/peak-hours/capacity - Get capacity recommendations
GET /vendor/peak-hours/staff - Get staff suggestions
GET /vendor/peak-hours/waiting - Get waiting time estimates
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.peak_hour_prediction_service import PeakHourPredictionService

router = APIRouter(prefix="/vendor/peak-hours", tags=["Vendor Peak Hour Prediction"])


def _resolve_vendor(user: dict, db: Session) -> int:
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> PeakHourPredictionService:
    return PeakHourPredictionService(db)


@router.get("/predict", summary="Get complete peak hour predictions")
def get_peak_hour_predictions(
    days_ahead: int = Query(1, ge=0, le=7, description="Days ahead to predict"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get complete peak hour predictions with all generated outputs."""
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    result = service.predict_peak_hours(vendor_id, days_ahead)
    
    return {
        "vendor_id": vendor_id,
        "prediction_date": result.prediction_date,
        "rush_hours": result.rush_hours,
        "quiet_hours": result.quiet_hours,
        "heatmap": result.heatmap,
        "capacity_recommendations": result.capacity_recommendations,
        "staff_suggestions": result.staff_suggestions,
        "waiting_time_estimates": result.waiting_time_estimates,
        "summary": result.summary,
        "insights": result.insights,
    }


@router.get("/rush", summary="Get rush hours")
def get_rush_hours(
    days_ahead: int = Query(1, ge=0, le=7),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_peak_hours(vendor_id, days_ahead)


@router.get("/quiet", summary="Get quiet hours")
def get_quiet_hours(
    days_ahead: int = Query(1, ge=0, le=7),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_quiet_hours(vendor_id, days_ahead)


@router.get("/heatmap", summary="Get peak hour heatmap")
def get_heatmap(
    days_ahead: int = Query(1, ge=0, le=7),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_heatmap(vendor_id, days_ahead)


@router.get("/capacity", summary="Get capacity recommendations")
def get_capacity_recommendations(
    days_ahead: int = Query(1, ge=0, le=7),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_capacity_recommendations(vendor_id, days_ahead)


@router.get("/staff", summary="Get staff suggestions")
def get_staff_suggestions(
    days_ahead: int = Query(1, ge=0, le=7),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_staff_suggestions(vendor_id, days_ahead)


@router.get("/waiting", summary="Get waiting time estimates")
def get_waiting_estimates(
    days_ahead: int = Query(1, ge=0, le=7),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_waiting_time_estimates(vendor_id, days_ahead)
