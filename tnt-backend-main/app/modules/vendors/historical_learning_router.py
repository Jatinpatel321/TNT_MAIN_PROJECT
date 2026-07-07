"""
Vendor Historical Learning API Router
=======================================

Endpoints for historical learning and forecasting:

GET /vendor/history/forecast - Get forecast based on historical learning
GET /vendor/history/trends - Get historical trends analysis
GET /vendor/history/patterns - Get learned patterns
POST /vendor/history/learn - Trigger learning for vendor
GET /vendor/history/dataset - Get learning dataset for ML
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.historical_learning_service import HistoricalLearningService

router = APIRouter(prefix="/vendor/history", tags=["Vendor Historical Learning"])


def _get_vendor_id(user=Depends(get_current_user), db: Session = Depends(get_db)) -> int:
    """Resolve the authenticated user's vendor ID."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> HistoricalLearningService:
    return HistoricalLearningService(db)


@router.get("/forecast", summary="Get historical-based forecast")
def get_historical_forecast(
    days_ahead: int = Query(7, ge=1, le=30, description="Number of days to forecast"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Generate forecast based on historical learning.
    
    Learns from:
    - Daily order patterns (90 days)
    - Weekly order patterns (24 weeks)
    - Monthly order patterns (12 months)
    - Seasonal trends
    - Semester schedules
    - Vendor holidays
    - Peak campus timings
    
    Returns:
        - forecast: List of daily predictions
        - learning_sources: All learned patterns
        - confidence: Overall forecast confidence
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_historical_forecast(vendor_id, days_ahead)


@router.get("/trends", summary="Get historical trends analysis")
def get_historical_trends(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive historical trends analysis.
    
    Returns:
        - daily_trends: Daily order patterns
        - weekly_trends: Weekly trends and patterns
        - monthly_trends: Monthly patterns and YoY growth
        - seasonal_trends: Seasonal variations
        - campus_impact: Semester schedule impact
        - campus_timings: Peak campus timings
        - holiday_patterns: Vendor holiday analysis
        - insights: AI-generated insights
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_historical_trends(vendor_id)


@router.get("/patterns", summary="Get learned patterns")
def get_learned_patterns(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get all learned patterns for the vendor.
    
    Returns cached patterns if available, otherwise triggers learning.
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    
    # Try to get persisted learning
    persisted = service.get_persisted_learning(vendor_id)
    if persisted:
        return {
            "vendor_id": vendor_id,
            "patterns": persisted,
            "source": "cache",
        }
    
    # Trigger learning
    learning_result = service.persist_learning(vendor_id)
    return {
        "vendor_id": vendor_id,
        "patterns": service.get_persisted_learning(vendor_id),
        "source": "fresh",
        "metadata": learning_result,
    }


@router.post("/learn", summary="Trigger learning for vendor")
def trigger_learning(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Trigger historical learning for the vendor.
    
    This analyzes all historical data and updates the learning cache.
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    
    # Invalidate existing cache
    service.invalidate_cache(vendor_id)
    
    # Trigger fresh learning
    result = service.persist_learning(vendor_id)
    
    return {
        "vendor_id": vendor_id,
        "status": "learning_completed",
        "details": result,
    }


@router.get("/dataset", summary="Get learning dataset for ML")
def get_learning_dataset(
    lookback_days: int = Query(90, ge=30, le=365, description="Days of historical data"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Generate learning dataset for ML model training.
    
    Returns:
        - dataset: Feature vectors and daily aggregates
        - statistics: Dataset statistics
        - metadata: Dataset metadata
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.generate_learning_dataset(vendor_id, lookback_days)


@router.get("/daily", summary="Get daily pattern analysis")
def get_daily_patterns(
    days: int = Query(90, ge=7, le=365, description="Days to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get daily order pattern analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_daily_patterns(vendor_id, days)


@router.get("/weekly", summary="Get weekly pattern analysis")
def get_weekly_patterns(
    weeks: int = Query(24, ge=4, le=52, description="Weeks to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get weekly order pattern analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_weekly_patterns(vendor_id, weeks)


@router.get("/monthly", summary="Get monthly pattern analysis")
def get_monthly_patterns(
    months: int = Query(12, ge=3, le=24, description="Months to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get monthly order pattern analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_monthly_patterns(vendor_id, months)


@router.get("/seasonal", summary="Get seasonal trends")
def get_seasonal_trends(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get seasonal trend analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_seasonal_trends(vendor_id)


@router.get("/campus", summary="Get campus schedule impact")
def get_campus_schedule(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get campus schedule impact analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_semester_schedules(vendor_id)


@router.get("/holidays", summary="Get vendor holiday patterns")
def get_holiday_patterns(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get vendor holiday pattern analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_vendor_holidays(vendor_id)


@router.get("/timings", summary="Get peak campus timings")
def get_campus_timings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get peak campus timing analysis."""
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.analyze_campus_timings(vendor_id)
