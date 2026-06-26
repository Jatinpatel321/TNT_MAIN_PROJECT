"""Vendor Analytics Suite - API Router with export support."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.vendors.analytics_service import VendorAnalyticsService

router = APIRouter(prefix="/vendors/analytics", tags=["Vendor Analytics"])


@router.get("/dashboard", summary="Get full analytics dashboard")
def get_analytics_dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get complete analytics dashboard with all reports."""
    service = VendorAnalyticsService(db)
    return service.get_full_analytics(user["id"])


@router.get("/daily", summary="Get daily sales report")
def get_daily_sales(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get daily sales data for the last N days."""
    service = VendorAnalyticsService(db)
    return service.get_daily_sales(user["id"], days)


@router.get("/weekly", summary="Get weekly sales report")
def get_weekly_sales(
    weeks: int = Query(12, description="Number of weeks to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get weekly sales data for the last N weeks."""
    service = VendorAnalyticsService(db)
    return service.get_weekly_sales(user["id"], weeks)


@router.get("/monthly", summary="Get monthly sales report")
def get_monthly_sales(
    months: int = Query(12, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get monthly sales data for the last N months."""
    service = VendorAnalyticsService(db)
    return service.get_monthly_sales(user["id"], months)


@router.get("/yearly", summary="Get yearly sales report")
def get_yearly_sales(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get yearly sales data."""
    service = VendorAnalyticsService(db)
    return service.get_yearly_sales(user["id"])


@router.get("/peak-hours", summary="Get peak hour analysis")
def get_peak_hours(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Analyze order distribution by hour of day."""
    service = VendorAnalyticsService(db)
    return service.get_peak_hour_analysis(user["id"])


@router.get("/items", summary="Get item sales analysis")
def get_item_analysis(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get popular and low-selling item analysis."""
    service = VendorAnalyticsService(db)
    return service.get_item_analysis(user["id"])


@router.get("/waste", summary="Get food waste analysis")
def get_waste_analysis(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Analyze food waste from cancelled orders."""
    service = VendorAnalyticsService(db)
    return service.get_food_waste_analysis(user["id"])


@router.get("/revenue-trends", summary="Get revenue trends")
def get_revenue_trends(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get revenue trend analysis (daily/weekly/monthly)."""
    service = VendorAnalyticsService(db)
    return service.get_revenue_trends(user["id"])


# ── CSV Export Endpoints ───────────────────────────────────────────────────


@router.get("/export/csv/{report_type}", response_class=PlainTextResponse)
def export_csv(
    report_type: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Export analytics data as CSV. Types: daily, weekly, monthly, items, peak_hours."""
    if report_type not in ("daily", "weekly", "monthly", "items", "peak_hours"):
        raise HTTPException(status_code=400, detail="Invalid report type")

    service = VendorAnalyticsService(db)
    csv_content = service.export_csv(user["id"], report_type)

    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_report.csv"},
    )