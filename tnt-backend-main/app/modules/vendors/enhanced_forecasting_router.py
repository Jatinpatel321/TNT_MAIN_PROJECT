"""
Enhanced Forecasting API Router
================================

Endpoints for multi-horizon demand forecasting:

GET /vendor/forecast/short-term - Next 24 hours forecast
GET /vendor/forecast/daily - Daily forecast (7-30 days)
GET /vendor/forecast/weekly - Weekly forecast (4-12 weeks)
GET /vendor/forecast/monthly - Monthly forecast (3-12 months)
GET /vendor/forecast/revenue - Revenue forecast
GET /vendor/forecast/customers - Customer count forecast
GET /vendor/forecast/comprehensive - All horizons combined
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.enhanced_forecasting_service import EnhancedForecastingService

router = APIRouter(prefix="/vendor/forecast", tags=["Vendor Enhanced Forecasting"])


def _get_vendor_id(user=Depends(get_current_user), db: Session = Depends(get_db)) -> int:
    """Resolve the authenticated user's vendor ID."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> EnhancedForecastingService:
    return EnhancedForecastingService(db)


@router.get("/short-term", summary="Get short-term forecast (next 24 hours)")
def get_short_term_forecast(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get hourly forecast for next 24 hours.
    
    Returns:
        - hourly_forecast: Hour-by-hour predictions
        - total_orders: Expected orders in next 24h
        - total_revenue: Expected revenue
        - peak_hours: Predicted peak periods
        - confidence: Overall confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_short_term_forecast(vendor_id)


@router.get("/daily", summary="Get daily forecast")
def get_daily_forecast(
    days: int = Query(7, ge=7, le=30, description="Number of days to forecast"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get daily demand forecast for next N days.
    
    Returns:
        - daily_forecast: Day-by-day predictions
        - summary: Aggregated statistics
        - confidence: Overall confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_daily_forecast(vendor_id, days)


@router.get("/weekly", summary="Get weekly forecast")
def get_weekly_forecast(
    weeks: int = Query(4, ge=4, le=12, description="Number of weeks to forecast"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get weekly demand forecast for next N weeks.
    
    Returns:
        - weekly_forecast: Week-by-week predictions
        - summary: Aggregated statistics
        - trend: Overall trend direction
        - confidence: Overall confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_weekly_forecast(vendor_id, weeks)


@router.get("/monthly", summary="Get monthly forecast")
def get_monthly_forecast(
    months: int = Query(3, ge=3, le=12, description="Number of months to forecast"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get monthly demand forecast for next N months.
    
    Returns:
        - monthly_forecast: Month-by-month predictions
        - summary: Aggregated statistics
        - yoy_growth: Year-over-year growth
        - confidence: Overall confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_monthly_forecast(vendor_id, months)


@router.get("/revenue", summary="Get revenue forecast")
def get_revenue_forecast(
    days: int = Query(30, ge=7, le=90, description="Number of days to forecast"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get revenue forecast for next N days.
    
    Returns:
        - total_revenue: Expected total revenue
        - avg_daily_revenue: Average daily revenue
        - daily_breakdown: Day-by-day revenue predictions
        - confidence: Overall confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_revenue_forecast(vendor_id, days)


@router.get("/customers", summary="Get customer count forecast")
def get_customer_forecast(
    days: int = Query(7, ge=7, le=30, description="Number of days to forecast"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get customer count forecast for next N days.
    
    Returns:
        - total_customers: Expected total customers
        - avg_daily_customers: Average daily customers
        - daily_breakdown: Day-by-day customer predictions
        - confidence: Overall confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_customer_forecast(vendor_id, days)


@router.get("/comprehensive", summary="Get comprehensive forecast (all horizons)")
def get_comprehensive_forecast(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive forecast across all time horizons.
    
    Returns:
        - short_term: Next 24 hours
        - daily: Next 7 days
        - weekly: Next 4 weeks
        - monthly: Next 3 months
        - insights: AI-generated insights
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_comprehensive_forecast(vendor_id)


@router.get("/by-type", summary="Get forecast by vendor type")
def get_forecast_by_type(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get forecast based on vendor type (food vs stationery).
    
    Returns enhanced forecast with:
    - Stationery: Print jobs, Xerox jobs, Binding jobs
    - Food: Popular items breakdown
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.forecast_by_vendor_type(vendor_id)
