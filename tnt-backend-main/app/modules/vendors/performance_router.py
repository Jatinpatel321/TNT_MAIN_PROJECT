"""
Vendor Performance Intelligence API Router
===========================================

Endpoints for vendor performance metrics:

GET /vendor/performance/metrics - Get performance metrics
GET /vendor/performance/score - Get vendor score
GET /vendor/performance/report - Get performance report
GET /vendor/performance/history - Get performance history
GET /vendor/performance/insights/forecast - Get insights for forecasting
GET /vendor/performance/insights/recommendations - Get insights for recommendations
GET /vendor/performance/insights/inventory - Get insights for inventory
GET /vendor/performance/insights/dashboard - Get insights for dashboard
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.performance_intelligence_service import PerformanceIntelligenceService

router = APIRouter(prefix="/vendor/performance", tags=["Vendor Performance Intelligence"])


def _get_vendor_id(user=Depends(get_current_user), db: Session = Depends(get_db)) -> int:
    """Resolve the authenticated user's vendor ID."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> PerformanceIntelligenceService:
    return PerformanceIntelligenceService(db)


@router.get("/metrics", summary="Get performance metrics")
def get_performance_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive performance metrics.
    
    Returns:
        - preparation_speed: Average minutes to prepare
        - completion_rate: Percentage of orders completed
        - cancellation_rate: Percentage of orders cancelled
        - average_delay: Average delay in minutes
        - customer_satisfaction: Customer satisfaction score (0-100)
        - order_accuracy: Order accuracy percentage
        - vendor_score: Overall vendor score (0-100)
        - performance_grade: excellent/good/fair/poor
        - insights: AI-generated insights
        - recommendations: Actionable recommendations
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_performance_report(vendor_id, days)


@router.get("/score", summary="Get vendor score")
def get_vendor_score(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get vendor score with grade.
    
    Returns:
        - vendor_score: Overall score (0-100)
        - performance_grade: excellent/good/fair/poor
        - grade_description: Human-readable description
        - color: Hex color for UI
        - icon: Grade icon
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_vendor_score(vendor_id)


@router.get("/report", summary="Get performance report")
def get_performance_report(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get comprehensive performance report with breakdown.
    
    Returns:
        - metrics: All performance metrics
        - breakdown: Detailed order breakdown
        - insights: AI-generated insights
        - recommendations: Actionable recommendations
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_performance_report(vendor_id, days)


@router.get("/history", summary="Get performance history")
def get_performance_history(
    days: int = Query(90, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get performance history for a vendor.
    
    Returns:
        - history: List of historical performance records
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    history = service.get_performance_history(vendor_id, days)
    
    return {
        "vendor_id": vendor_id,
        "period_days": days,
        "total_records": len(history),
        "history": history,
    }


@router.get("/insights/forecast", summary="Get insights for forecasting")
def get_forecast_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get performance insights to improve forecasting.
    
    Returns:
        - vendor_score: Overall vendor score
        - forecast_adjustments: Factors to adjust forecasts
        - insights: Performance-based forecast insights
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_performance_insights_for_forecast(vendor_id)


@router.get("/insights/recommendations", summary="Get insights for recommendations")
def get_recommendation_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get performance insights to improve recommendations.
    
    Returns:
        - vendor_score: Overall vendor score
        - recommendation_factors: Factors for recommendations
        - suggested_actions: Top recommended actions
        - priority_areas: Priority improvement areas
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_performance_insights_for_recommendations(vendor_id)


@router.get("/insights/inventory", summary="Get insights for inventory")
def get_inventory_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get performance insights to improve inventory suggestions.
    
    Returns:
        - vendor_score: Overall vendor score
        - inventory_factors: Factors for inventory management
        - suggestions: Inventory-related suggestions
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_performance_insights_for_inventory(vendor_id)


@router.get("/insights/dashboard", summary="Get insights for dashboard")
def get_dashboard_insights(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get performance insights for dashboard analytics.
    
    Returns:
        - vendor_score: Overall vendor score
        - performance_grade: Performance grade
        - key_metrics: Key metrics with trends
        - breakdown: Detailed breakdown
        - insights: Top insights
        - recommendations: Top recommendations
    """
    vendor_id = _get_vendor_id(user, db)
    service = _get_service(db)
    return service.get_performance_insights_for_dashboard(vendor_id)
