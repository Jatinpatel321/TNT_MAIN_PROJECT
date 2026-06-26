"""Vendor Retention Platform - Business Logic Service."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.users.model import User
from app.modules.menu.model import MenuItem
from app.modules.rewards.model import RewardPoints, RewardTransaction, RewardType
from app.modules.notifications.model import NotificationType
from app.modules.notifications.service import notify_user
from app.modules.vendors.retention_models import (
    DiscountCampaign,
    VendorOffer,
    VendorCampaign,
    VendorOfferRedemption,
    OfferType,
    CampaignStatus,
)


class VendorRetentionService:
    """Service for vendor customer retention, offers, and promotions."""

    def __init__(self, db: Session):
        self.db = db

    # ── Customer Analysis ──────────────────────────────────────────────────

    def get_customers(self, vendor_id: int) -> Dict[str, Any]:
        """Get all customers who have ordered from this vendor."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        ninety_days_ago = utcnow_naive() - timedelta(days=90)

        customers = self.db.query(
            User.id,
            User.name,
            User.phone,
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_amount).label("total_spent"),
            func.max(Order.created_at).label("last_order_date"),
        ).join(
            Order, Order.user_id == User.id
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            User.id, User.name, User.phone
        ).order_by(
            func.count(Order.id).desc()
        ).all()

        customer_list = []
        for row in customers:
            last_order = row.last_order_date
            days_since_last = (utcnow_naive() - last_order).days if last_order else 999

            # Segment customers
            if row.total_orders >= 5 and days_since_last <= 30:
                segment = "loyal"
            elif row.total_orders >= 2 and days_since_last <= 30:
                segment = "repeat"
            elif days_since_last <= 30:
                segment = "new"
            elif days_since_last <= 60:
                segment = "at_risk"
            else:
                segment = "lapsed"

            customer_list.append({
                "user_id": row.id,
                "name": row.name,
                "phone": row.phone,
                "total_orders": row.total_orders,
                "total_spent": float(row.total_spent or 0),
                "last_order_date": last_order.isoformat() if last_order else None,
                "days_since_last_order": days_since_last,
                "segment": segment,
            })

        # Segment counts
        segments = {"loyal": 0, "repeat": 0, "new": 0, "at_risk": 0, "lapsed": 0}
        for c in customer_list:
            segments[c["segment"]] = segments.get(c["segment"], 0) + 1

        return {
            "vendor_id": vendor_id,
            "total_customers": len(customer_list),
            "customers": customer_list,
            "segments": segments,
        }

    def get_repeat_customers(self, vendor_id: int) -> Dict[str, Any]:
        """Get repeat customers (2+ orders) with analysis."""
        customers = self.get_customers(vendor_id)
        repeat = [c for c in customers["customers"] if c["total_orders"] >= 2]

        # Calculate repeat rate
        total = customers["total_customers"]
        repeat_rate = round(len(repeat) / total * 100, 1) if total > 0 else 0

        # Top frequent buyers
        frequent = sorted(repeat, key=lambda c: c["total_orders"], reverse=True)[:10]

        return {
            "vendor_id": vendor_id,
            "total_repeat_customers": len(repeat),
            "repeat_rate": repeat_rate,
            "frequent_buyers": frequent,
        }

    # ── Offer Management ───────────────────────────────────────────────────

    def create_offer(self, vendor_id: int, data: Dict[str, Any]) -> VendorOffer:
        """Create a new offer."""
        offer = VendorOffer(
            vendor_id=vendor_id,
            campaign_id=data.get("campaign_id"),
            target_user_id=data.get("target_user_id"),
            title=data["title"],
            description=data.get("description"),
            discount_type=OfferType(data["discount_type"]),
            discount_value=data["discount_value"],
            min_order_amount=data.get("min_order_amount"),
            max_discount_amount=data.get("max_discount_amount"),
            is_dynamic=data.get("is_dynamic", False),
            ai_confidence=data.get("ai_confidence"),
            expires_at=data.get("expires_at"),
        )
        self.db.add(offer)
        self.db.flush()
        return offer

    def get_offers(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Get all offers for a vendor."""
        offers = self.db.query(VendorOffer).filter(
            VendorOffer.vendor_id == vendor_id
        ).order_by(VendorOffer.created_at.desc()).all()

        return [
            {
                "id": o.id,
                "title": o.title,
                "description": o.description,
                "discount_type": o.discount_type.value,
                "discount_value": o.discount_value,
                "min_order_amount": o.min_order_amount,
                "max_discount_amount": o.max_discount_amount,
                "is_dynamic": o.is_dynamic,
                "ai_confidence": o.ai_confidence,
                "is_active": o.is_active,
                "times_redeemed": o.times_redeemed,
                "expires_at": o.expires_at.isoformat() if o.expires_at else None,
                "created_at": o.created_at.isoformat(),
            }
            for o in offers
        ]

    # ── Campaign Management ────────────────────────────────────────────────

    def create_campaign(self, vendor_id: int, data: Dict[str, Any]) -> DiscountCampaign:
        """Create a discount campaign."""
        campaign = DiscountCampaign(
            vendor_id=vendor_id,
            name=data["name"],
            description=data.get("description"),
            offer_type=OfferType(data["offer_type"]),
            discount_value=data.get("discount_value"),
            min_order_amount=data.get("min_order_amount"),
            max_discount_amount=data.get("max_discount_amount"),
            is_combo=data.get("is_combo", False),
            combo_items=json.dumps(data.get("combo_items", [])),
            combo_price=data.get("combo_price"),
            is_off_peak=data.get("is_off_peak", False),
            off_peak_start=data.get("off_peak_start"),
            off_peak_end=data.get("off_peak_end"),
            start_date=data["start_date"],
            end_date=data["end_date"],
            usage_limit=data.get("usage_limit"),
            status=CampaignStatus.ACTIVE,
        )
        self.db.add(campaign)
        self.db.flush()

        # Create corresponding offer
        offer = VendorOffer(
            vendor_id=vendor_id,
            campaign_id=campaign.id,
            title=campaign.name,
            description=campaign.description,
            discount_type=campaign.offer_type,
            discount_value=campaign.discount_value or 0,
            min_order_amount=campaign.min_order_amount,
            max_discount_amount=campaign.max_discount_amount,
            expires_at=campaign.end_date,
        )
        self.db.add(offer)
        self.db.flush()

        return campaign

    def get_campaigns(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Get all campaigns for a vendor."""
        campaigns = self.db.query(DiscountCampaign).filter(
            DiscountCampaign.vendor_id == vendor_id
        ).order_by(DiscountCampaign.created_at.desc()).all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "offer_type": c.offer_type.value,
                "discount_value": c.discount_value,
                "min_order_amount": c.min_order_amount,
                "max_discount_amount": c.max_discount_amount,
                "is_combo": c.is_combo,
                "combo_items": json.loads(c.combo_items) if c.combo_items else [],
                "combo_price": c.combo_price,
                "is_off_peak": c.is_off_peak,
                "off_peak_start": c.off_peak_start,
                "off_peak_end": c.off_peak_end,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
                "usage_limit": c.usage_limit,
                "times_used": c.times_used,
                "is_active": c.is_active,
                "status": c.status.value,
                "created_at": c.created_at.isoformat(),
            }
            for c in campaigns
        ]

    # ── Promotions ─────────────────────────────────────────────────────────

    def get_promotions(self, vendor_id: int) -> Dict[str, Any]:
        """Get all active promotions for a vendor."""
        now = utcnow_naive()

        active_campaigns = self.db.query(DiscountCampaign).filter(
            DiscountCampaign.vendor_id == vendor_id,
            DiscountCampaign.is_active == True,
            DiscountCampaign.status == CampaignStatus.ACTIVE,
            DiscountCampaign.start_date <= now,
            DiscountCampaign.end_date >= now,
        ).all()

        active_offers = self.db.query(VendorOffer).filter(
            VendorOffer.vendor_id == vendor_id,
            VendorOffer.is_active == True,
        ).all()

        return {
            "vendor_id": vendor_id,
            "active_campaigns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "offer_type": c.offer_type.value,
                    "discount_value": c.discount_value,
                    "is_combo": c.is_combo,
                    "is_off_peak": c.is_off_peak,
                    "end_date": c.end_date.isoformat(),
                    "times_used": c.times_used,
                }
                for c in active_campaigns
            ],
            "active_offers": [
                {
                    "id": o.id,
                    "title": o.title,
                    "discount_type": o.discount_type.value,
                    "discount_value": o.discount_value,
                    "is_dynamic": o.is_dynamic,
                    "times_redeemed": o.times_redeemed,
                }
                for o in active_offers
            ],
            "total_active": len(active_campaigns) + len(active_offers),
        }

    # ── AI Suggested Discounts ─────────────────────────────────────────────

    def get_ai_suggested_discounts(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Generate AI-suggested discounts based on customer behavior."""
        suggestions = []

        # 1. Lapsed customer win-back offer
        lapsed_customers = self.db.query(
            User.id, User.name, func.max(Order.created_at).label("last_order")
        ).join(
            Order, Order.user_id == User.id
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(User.id, User.name).having(
            func.max(Order.created_at) < utcnow_naive() - timedelta(days=30)
        ).limit(5).all()

        if lapsed_customers:
            suggestions.append({
                "type": "win_back",
                "title": "Win-Back Offer",
                "description": f"Offer 20% off to {len(lapsed_customers)} lapsed customers",
                "suggested_discount": 20,
                "discount_type": "discount_percentage",
                "target_segment": "lapsed",
                "potential_customers": len(lapsed_customers),
                "confidence": 0.85,
            })

        # 2. Off-peak promotion
        current_hour = utcnow_naive().hour
        if 14 <= current_hour <= 17:  # Afternoon slump
            suggestions.append({
                "type": "off_peak",
                "title": "Off-Peak Promotion",
                "description": "Boost afternoon orders with 15% discount",
                "suggested_discount": 15,
                "discount_type": "discount_percentage",
                "target_segment": "all",
                "confidence": 0.75,
            })

        # 3. Combo deal suggestion
        popular_items = self.db.query(
            MenuItem.id, MenuItem.name, func.count(OrderItem.id).label("count")
        ).join(
            OrderItem, OrderItem.menu_item_id == MenuItem.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            Order.created_at >= utcnow_naive() - timedelta(days=30),
        ).group_by(MenuItem.id, MenuItem.name).order_by(
            func.count(OrderItem.id).desc()
        ).limit(3).all()

        if len(popular_items) >= 2:
            combo_names = [i.name for i in popular_items[:2]]
            suggestions.append({
                "type": "combo",
                "title": "Combo Deal",
                "description": f"Bundle {combo_names[0]} + {combo_names[1]} at 10% off",
                "suggested_discount": 10,
                "discount_type": "combo_deal",
                "target_segment": "all",
                "combo_items": [i.id for i in popular_items[:2]],
                "confidence": 0.80,
            })

        # 4. Loyalty reward
        loyal_count = self.db.query(func.count(User.id)).join(
            Order, Order.user_id == User.id
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(User.id).having(
            func.count(Order.id) >= 5
        ).count()

        if loyal_count > 0:
            suggestions.append({
                "type": "loyalty",
                "title": "Loyalty Bonus",
                "description": f"Reward {loyal_count} loyal customers with 25% off",
                "suggested_discount": 25,
                "discount_type": "discount_percentage",
                "target_segment": "loyal",
                "potential_customers": loyal_count,
                "confidence": 0.90,
            })

        return suggestions

    # ── Redeem Offer ───────────────────────────────────────────────────────

    def redeem_offer(self, offer_id: int, user_id: int, order_id: int) -> Dict[str, Any]:
        """Redeem an offer for a user's order."""
        offer = self.db.query(VendorOffer).filter(VendorOffer.id == offer_id).first()
        if not offer or not offer.is_active:
            return {"success": False, "error": "Offer not found or inactive"}

        # Calculate discount
        discount = offer.discount_value
        if offer.max_discount_amount:
            discount = min(discount, offer.max_discount_amount)

        redemption = VendorOfferRedemption(
            offer_id=offer_id,
            user_id=user_id,
            order_id=order_id,
            discount_amount=discount,
        )
        self.db.add(redemption)

        offer.times_redeemed = (offer.times_redeemed or 0) + 1

        # Award bonus reward points
        reward = self.db.query(RewardPoints).filter(RewardPoints.user_id == user_id).first()
        if reward:
            bonus_points = discount * 0.5  # 0.5 points per rupee discount
            reward.points += bonus_points
            reward.total_earned += bonus_points

            tx = RewardTransaction(
                user_id=user_id,
                reward_type=RewardType.VOUCHER_REDEMPTION,
                points=bonus_points,
                description=f"Bonus points for redeeming offer: {offer.title}",
                order_id=order_id,
            )
            self.db.add(tx)

        self.db.flush()

        return {
            "success": True,
            "discount_amount": discount,
            "bonus_points": discount * 0.5,
        }

    # ── Notify Customers ───────────────────────────────────────────────────

    def notify_customers_about_offer(self, vendor_id: int, offer_id: int) -> int:
        """Send notifications to eligible customers about an offer."""
        offer = self.db.query(VendorOffer).filter(
            VendorOffer.id == offer_id,
            VendorOffer.vendor_id == vendor_id,
        ).first()
        if not offer:
            return 0

        customer_ids = self.db.query(Order.user_id).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        ).distinct().all()

        notified = 0
        for (user_id,) in customer_ids:
            try:
                customer = self.db.query(User).filter(User.id == user_id).first()
                if not customer:
                    continue
                notify_user(
                    user_id=user_id,
                    phone=customer.phone,
                    title=f"Special Offer: {offer.title}",
                    message=f"{offer.description or 'Check out our latest offer!'} - {offer.discount_value}% off!",
                    db=self.db,
                    send_sms_flag=False,
                    notification_type=NotificationType.PROMO,
                    reference_id=offer_id,
                )
                notified += 1
            except Exception:
                pass

        return notified