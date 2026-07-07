"""Vendor Promotion & Retention Router.

PHASE D — Implements:
- Campaign Management
- Coupon Campaigns
- Promotion Management
- Push Campaign Integration
- Retention Analytics

Connects with existing FCM infrastructure and retention service.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.fcm import send_push
from app.core.security import get_current_user
from app.modules.users.model import User
from app.modules.orders.model import Order, OrderStatus
from app.modules.notifications.service import notify_user
from app.modules.notifications.model import NotificationType
from app.modules.vendors.retention_service import VendorRetentionService
from app.modules.vendors.retention_models import (
    DiscountCampaign,
    VendorOffer,
    VendorCampaign,
    OfferType,
    CampaignStatus,
)

router = APIRouter(prefix="/vendors/promotions", tags=["Vendor Promotions"])


def _resolve_vendor(user: dict, db: Session) -> int:
    """Get vendor user ID from authenticated user."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user.id


# ── Campaign Management ──────────────────────────────────────────────────────


@router.get("/campaigns", summary="Get all campaigns")
def get_campaigns(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get all campaigns for the authenticated vendor."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    return {"campaigns": service.get_campaigns(vendor_id)}


@router.post("/campaigns", summary="Create a campaign")
def create_campaign(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new discount/combo campaign."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    campaign = service.create_campaign(vendor_id, data)
    return {
        "message": "Campaign created",
        "campaign_id": campaign.id,
        "name": campaign.name,
    }


@router.put("/campaigns/{campaign_id}/toggle", summary="Toggle campaign active status")
def toggle_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Enable or disable a campaign."""
    vendor_id = _resolve_vendor(user, db)
    campaign = db.query(DiscountCampaign).filter(
        DiscountCampaign.id == campaign_id,
        DiscountCampaign.vendor_id == vendor_id,
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.is_active = not campaign.is_active
    campaign.status = CampaignStatus.ACTIVE if campaign.is_active else CampaignStatus.INACTIVE
    db.commit()

    return {
        "message": f"Campaign {'activated' if campaign.is_active else 'deactivated'}",
        "campaign_id": campaign.id,
        "is_active": campaign.is_active,
    }


# ── Coupon Campaigns ─────────────────────────────────────────────────────────


@router.get("/coupons", summary="Get all coupon offers")
def get_coupons(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get all coupon/offer promotions."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    return {"coupons": service.get_offers(vendor_id)}


@router.post("/coupons", summary="Create a coupon offer")
def create_coupon(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new coupon/offer."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    offer = service.create_offer(vendor_id, data)
    return {
        "message": "Coupon created",
        "offer_id": offer.id,
        "title": offer.title,
    }


@router.delete("/coupons/{offer_id}", summary="Delete a coupon offer")
def delete_coupon(
    offer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete a coupon offer."""
    vendor_id = _resolve_vendor(user, db)
    offer = db.query(VendorOffer).filter(
        VendorOffer.id == offer_id,
        VendorOffer.vendor_id == vendor_id,
    ).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    db.delete(offer)
    db.commit()
    return {"message": "Coupon deleted", "offer_id": offer_id}


# ── Promotion Management ─────────────────────────────────────────────────────


@router.get("/active", summary="Get active promotions")
def get_active_promotions(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get all currently active promotions."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    return service.get_promotions(vendor_id)


@router.get("/ai-suggestions", summary="Get AI-suggested discounts")
def get_ai_suggested_discounts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get AI-generated discount suggestions based on customer behavior."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    return {"suggestions": service.get_ai_suggested_discounts(vendor_id)}


# ── Push Campaign Integration ────────────────────────────────────────────────


@router.post("/push-campaign", summary="Send push notification campaign")
def send_push_campaign(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send a push notification campaign to all or targeted customers.
    
    Body:
    - title: Notification title
    - message: Notification message
    - segment: Optional customer segment filter (loyal, repeat, new, at_risk, lapsed, all)
    - offer_id: Optional offer ID to include in notification
    """
    vendor_id = _resolve_vendor(user, db)
    title = data.get("title", "Special Offer")
    message = data.get("message", "Check out our latest deals!")
    segment = data.get("segment", "all")
    offer_id = data.get("offer_id")

    # Get customer list, optionally filtered by segment
    service = VendorRetentionService(db)
    customers_data = service.get_customers(vendor_id)
    customers = customers_data["customers"]

    if segment != "all":
        customers = [c for c in customers if c["segment"] == segment]

    sent_count = 0
    for customer in customers:
        try:
            # Send via notification system
            notify_user(
                user_id=customer["user_id"],
                phone=customer.get("phone"),
                title=title,
                message=message,
                db=db,
                send_sms_flag=False,
                notification_type=NotificationType.PROMO,
                reference_id=offer_id,
            )

            # Also attempt direct FCM push
            device_token = _get_user_device_token(customer["user_id"], db)
            if device_token:
                send_push(
                    device_token=device_token,
                    title=title,
                    body=message,
                    data={"offer_id": str(offer_id), "type": "promotion"},
                )

            sent_count += 1
        except Exception:
            pass

    return {
        "message": f"Push campaign sent to {sent_count} customers",
        "total_sent": sent_count,
        "segment": segment,
        "total_in_segment": len(customers),
    }


def _get_user_device_token(user_id: int, db: Session) -> Optional[str]:
    """Get device token for a user."""
    try:
        # Check user model for device_token field
        from app.modules.users.model import User
        user = db.query(User).filter(User.id == user_id).first()
        if hasattr(user, 'device_token') and user.device_token:
            return user.device_token
        return None
    except Exception:
        return None


@router.post("/notify-offer/{offer_id}", summary="Notify customers about an offer")
def notify_customers_about_offer(
    offer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Send notifications to eligible customers about a specific offer."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    notified = service.notify_customers_about_offer(vendor_id, offer_id)
    return {
        "message": f"Notified {notified} customers about offer",
        "notified_count": notified,
    }


# ── Retention Analytics ──────────────────────────────────────────────────────


@router.get("/retention-analytics", summary="Get retention analytics dashboard")
def get_retention_analytics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get comprehensive retention analytics including customer segments and repeat rates."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)

    customers_data = service.get_customers(vendor_id)
    repeat_data = service.get_repeat_customers(vendor_id)
    promotions = service.get_promotions(vendor_id)
    suggestions = service.get_ai_suggested_discounts(vendor_id)

    return {
        "vendor_id": vendor_id,
        "total_customers": customers_data["total_customers"],
        "segments": customers_data["segments"],
        "repeat_rate": repeat_data["repeat_rate"],
        "total_repeat_customers": repeat_data["total_repeat_customers"],
        "frequent_buyers": repeat_data.get("frequent_buyers", []),
        "active_promotions": promotions["total_active"],
        "active_campaigns": len(promotions.get("active_campaigns", [])),
        "active_offers": len(promotions.get("active_offers", [])),
        "ai_suggestions": suggestions,
        "promotions": promotions,
    }


@router.get("/customer-segments", summary="Get customer segment analysis")
def get_customer_segments(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get customer segment breakdown (loyal, repeat, new, at_risk, lapsed)."""
    vendor_id = _resolve_vendor(user, db)
    service = VendorRetentionService(db)
    return service.get_customers(vendor_id)