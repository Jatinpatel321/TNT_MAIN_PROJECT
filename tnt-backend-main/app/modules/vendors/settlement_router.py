"""Vendor Settlement System - API Router."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.settlement_service import VendorSettlementService

router = APIRouter(prefix="/vendors/settlement", tags=["Vendor Settlement"])


@router.get("/revenue", summary="Get revenue summary")
def get_revenue_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get revenue summary with wallet, today's revenue, and online/cash breakdown."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorSettlementService(db)
    return service.get_revenue_summary(db_user.id)


@router.get("/transactions", summary="Get transaction history")
def get_transactions(
    days: int = Query(30, description="Number of days of transaction history"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get transaction history with online/cash/refund breakdown."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorSettlementService(db)
    return service.get_transactions(db_user.id, days)


@router.get("/settlements", summary="Get settlement reports")
def get_settlements(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get settlement reports with pending settlement and history."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorSettlementService(db)
    return service.get_settlements(db_user.id)


@router.get("/refunds", summary="Get refund tracking")
def get_refunds(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get refund tracking data with history and monthly trends."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorSettlementService(db)
    return service.get_refunds(db_user.id)


@router.get("/daily-revenue", summary="Get daily revenue breakdown")
def get_daily_revenue(
    days: int = Query(7, description="Number of days"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get daily revenue breakdown (online/cash/refunds/net) for last N days."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorSettlementService(db)
    return service.get_daily_revenue(db_user.id, days)