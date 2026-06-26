"""
Forecast Validation API Router
===============================

Endpoints:
POST /vendor/forecast/validate - Validate predictions against actuals
POST /vendor/forecast/validate/with-db - Validate against database
GET /vendor/forecast/validate/history - Get validation history
GET /vendor/forecast/validate/history/trend - Get accuracy trend
"""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.forecast_validation_service import ForecastValidationService

router = APIRouter(prefix="/vendor/forecast/validate", tags=["Vendor Forecast Validation"])


def _resolve_vendor(user: dict, db: Session) -> int:
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


def _get_service(db: Session) -> ForecastValidationService:
    return ForecastValidationService(db)


@router.post("", summary="Validate predictions against actuals")
def validate_forecast(
    body: dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Compare predicted vs actual values for forecast accuracy.
    
    Body:
    - predictions: List of {period_label, predicted_orders, predicted_revenue}
    - actuals: List of {period_label, actual_orders, actual_revenue}
    - period_type: "daily" | "weekly" | "monthly" (default: "daily")
    
    Returns:
    - overall_accuracy: Overall forecast accuracy %
    - overall_grade: excellent/good/fair/poor/fail
    - orders: {mape, rmse, prediction_accuracy, grade, samples, ...}
    - revenue: {mape, rmse, prediction_accuracy, grade, samples, ...}
    - comparisons: Per-period breakdown
    - insights: AI-generated insights
    - recommendations: Actionable recommendations
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    
    predictions = body.get("predictions", [])
    actuals = body.get("actuals", [])
    period_type = body.get("period_type", "daily")
    
    if not predictions:
        raise HTTPException(status_code=400, detail="predictions list is required")
    if not actuals:
        raise HTTPException(status_code=400, detail="actuals list is required")
    
    return service.get_validation_result(vendor_id, predictions, actuals, period_type)


@router.post("/with-db", summary="Validate against database")
def validate_with_database(
    body: dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Compare predictions with actual orders from the database.
    
    Body:
    - predictions: List of {period_label, predicted_orders, predicted_revenue}
    - days_back: Number of days to look back (default: 30)
    
    Returns:
    - Full validation result with metrics
    """
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    
    predictions = body.get("predictions", [])
    days_back = body.get("days_back", 30)
    
    if not predictions:
        raise HTTPException(status_code=400, detail="predictions list is required")
    
    return service.compare_with_database(vendor_id, predictions, days_back)


@router.get("/history", summary="Get validation history")
def get_validation_history(
    period_type: str = Query("daily", description="daily/weekly/monthly"),
    limit: int = Query(50, ge=1, le=200, description="Max entries"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get stored validation history for vendor."""
    vendor_id = _resolve_vendor(user, db)
    service = _get_service(db)
    return service.get_history(vendor_id, period_type, limit)
