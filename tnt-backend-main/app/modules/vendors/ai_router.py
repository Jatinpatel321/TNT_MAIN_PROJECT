"""Vendor AI Intelligence API Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.vendor_ai_service import VendorAIService

router = APIRouter(prefix="/vendors/ai", tags=["Vendor AI"])


def _get_vendor(db_user: User | None) -> int:
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


@router.get("/dashboard", summary="Get full AI dashboard data")
def get_ai_dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get complete AI dashboard with all forecasts, insights, and recommendations."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_full_ai_dashboard(db_user.id)


@router.get("/forecast/daily", summary="Get daily orders forecast")
def get_daily_forecast(
    days: int = 7,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Predict daily order volume for the next N days."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_daily_forecast(db_user.id, days)


@router.get("/forecast/weekly", summary="Get weekly orders forecast")
def get_weekly_forecast(
    weeks: int = 4,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Predict weekly order volume for the next N weeks."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_weekly_forecast(db_user.id, weeks)


@router.get("/forecast/monthly", summary="Get monthly orders forecast")
def get_monthly_forecast(
    months: int = 3,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Predict monthly order volume for the next N months."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_monthly_forecast(db_user.id, months)


@router.get("/popular-items", summary="Get popular items prediction")
def get_popular_items(
    limit: int = 10,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get popular menu items with order frequency and trends."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_popular_items(db_user.id, limit)


@router.get("/workload", summary="Get workload prediction")
def get_workload(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get stationery workload or peak time prediction based on vendor type."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)

    # Determine vendor type
    from app.modules.stationery.service_model import StationeryService
    is_stationery = db.query(StationeryService).filter(StationeryService.vendor_id == db_user.id).first()

    if is_stationery:
        return service.get_stationery_workload(db_user.id)
    else:
        return service.get_peak_time_prediction(db_user.id)


@router.get("/peak-times", summary="Get peak time prediction")
def get_peak_times(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Predict peak hours for the vendor."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_peak_time_prediction(db_user.id)


@router.get("/waste-insights", summary="Get food waste reduction insights")
def get_waste_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate food waste reduction insights based on order data."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_waste_reduction_insights(db_user.id)


@router.get("/inventory-suggestions", summary="Get inventory suggestions")
def get_inventory_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate inventory stocking suggestions."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_inventory_suggestions(db_user.id)


@router.get("/recommendations", summary="Get AI recommendations")
def get_recommendations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Generate comprehensive AI recommendations for the vendor."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorAIService(db)
    return service.get_ai_recommendations(db_user.id)