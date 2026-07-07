"""Vendor Retention Platform - API Router."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.vendors.retention_service import VendorRetentionService

router = APIRouter(prefix="/vendors/retention", tags=["Vendor Retention"])


@router.get("/customers", summary="Get all customers with segmentation")
def get_customers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all customers who ordered from this vendor, with segmentation."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    return service.get_customers(db_user.id)


@router.get("/repeat-customers", summary="Get repeat customer analysis")
def get_repeat_customers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get repeat customer analysis with frequent buyers list."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    return service.get_repeat_customers(db_user.id)


@router.post("/offers", summary="Create a new offer")
def create_offer(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new offer for customers."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    offer = service.create_offer(db_user.id, data)
    db.commit()
    db.refresh(offer)
    return {
        "id": offer.id,
        "title": offer.title,
        "discount_type": offer.discount_type.value,
        "discount_value": offer.discount_value,
        "is_active": offer.is_active,
    }


@router.get("/offers", summary="Get all offers")
def get_offers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all offers created by the vendor."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    offers = service.get_offers(db_user.id)
    return {"offers": offers, "total": len(offers)}


@router.post("/campaigns", summary="Create a discount campaign")
def create_campaign(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a discount/combo/off-peak campaign."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    data["start_date"] = datetime.fromisoformat(data["start_date"].replace("Z", "+00:00"))
    data["end_date"] = datetime.fromisoformat(data["end_date"].replace("Z", "+00:00"))

    service = VendorRetentionService(db)
    campaign = service.create_campaign(db_user.id, data)
    db.commit()
    db.refresh(campaign)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "offer_type": campaign.offer_type.value,
        "status": campaign.status.value,
    }


@router.get("/campaigns", summary="Get all campaigns")
def get_campaigns(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all campaigns created by the vendor."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    campaigns = service.get_campaigns(db_user.id)
    return {"campaigns": campaigns, "total": len(campaigns)}


@router.get("/promotions", summary="Get active promotions")
def get_promotions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get all currently active promotions."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    return service.get_promotions(db_user.id)


@router.get("/ai-suggestions", summary="Get AI-suggested discounts")
def get_ai_suggestions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Get AI-generated discount suggestions based on customer behavior."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    suggestions = service.get_ai_suggested_discounts(db_user.id)
    return {"suggestions": suggestions, "total": len(suggestions)}


@router.post("/offers/{offer_id}/notify", summary="Notify customers about offer")
def notify_customers(
    offer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Send notifications to eligible customers about an offer."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    service = VendorRetentionService(db)
    notified = service.notify_customers_about_offer(db_user.id, offer_id)
    db.commit()
    return {"notified": notified}


@router.post("/offers/{offer_id}/redeem", summary="Redeem an offer")
def redeem_offer(
    offer_id: int,
    user_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> Dict[str, Any]:
    """Redeem an offer for a user's order."""
    service = VendorRetentionService(db)
    result = service.redeem_offer(offer_id, user_id, order_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Redemption failed"))
    return result