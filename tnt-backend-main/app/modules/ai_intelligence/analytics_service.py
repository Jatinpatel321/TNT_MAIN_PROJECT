import logging
from datetime import time, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole
from app.modules.feedback.model import VendorReview

from .schemas import (
    BestPickupTimeResponse,
    PeakHourAlert,
    PeakHourPeriod,
    PickupTimeSlot,
    PopularNearbyResponse,
    PopularNearbyVendor,
    SmartReorderItem,
    SmartReorderResponse,
    VendorRecommendationItem,
    VendorRecommendationsResponse,
    MenuSuggestionItem,
    MenuSuggestionsResponse,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """AI analytics service for user-facing features."""

    def __init__(self, db: Session):
        self.db = db

    # ── 1. Personalized Vendor Recommendations ─────────────────────────────

    def get_vendor_recommendations(self, user_id: int) -> VendorRecommendationsResponse:
        try:
            items: List[VendorRecommendationItem] = []

            thirty_days_ago = utcnow_naive() - timedelta(days=30)

            user_vendor_counts = dict(
                self.db.query(Order.vendor_id, func.count(Order.id))
                .filter(Order.user_id == user_id, Order.created_at >= thirty_days_ago)
                .group_by(Order.vendor_id)
                .all()
            )

            vendors = (
                self.db.query(User)
                .filter(User.role == UserRole.VENDOR, User.is_approved == True)
                .all()
            )

            for vendor in vendors:
                order_count = user_vendor_counts.get(vendor.id, 0)

                current_slots = self.db.query(Slot).filter(Slot.vendor_id == vendor.id).all()
                total_cap = sum(s.max_orders for s in current_slots) or 1
                total_orders = sum(s.current_orders for s in current_slots)
                utilization = total_orders / total_cap

                if utilization >= 0.9:
                    load = "HIGH"
                elif utilization >= 0.6:
                    load = "MEDIUM"
                else:
                    load = "LOW"

                express = utilization < 0.5

                freq_bonus = min(order_count * 15, 40)
                load_bonus = (1 - utilization) * 30
                base_score = 30

                vp = getattr(vendor, "vendor_profile", None)
                category = getattr(vp, "category", None) if vp else None
                logo_url = getattr(vp, "logo_url", None) if vp else None

                score = round(freq_bonus + load_bonus + base_score, 1)

                if order_count >= 3:
                    reason = f"You've ordered here {order_count} times"
                elif order_count >= 1:
                    reason = "One of your regular spots"
                elif load == "LOW":
                    reason = "Low wait time right now"
                else:
                    reason = "Popular on campus"

                items.append(
                    VendorRecommendationItem(
                        vendor_id=vendor.id,
                        vendor_name=vendor.name or f"Vendor #{vendor.id}",
                        vendor_type=vendor.vendor_type,
                        category=category,
                        logo_url=logo_url,
                        rank_score=score,
                        live_load=load,
                        express_pickup=express,
                        reason=reason,
                    )
                )

            items.sort(key=lambda v: v.rank_score, reverse=True)
            return VendorRecommendationsResponse(recommendations=items[:10])
        except Exception:
            logger.exception("get_vendor_recommendations failed for user_id=%s", user_id)
            return VendorRecommendationsResponse(recommendations=[])

    # ── 2. Personalized Menu Suggestions ───────────────────────────────────

    def get_menu_suggestions(self, user_id: int) -> MenuSuggestionsResponse:
        try:
            thirty_days_ago = utcnow_naive() - timedelta(days=30)

            user_items = (
                self.db.query(OrderItem.menu_item_id, func.count(OrderItem.id).label("cnt"))
                .join(Order)
                .filter(Order.user_id == user_id, Order.created_at >= thirty_days_ago)
                .group_by(OrderItem.menu_item_id)
                .order_by(func.count(OrderItem.id).desc())
                .limit(5)
                .all()
            )

            personalized: List[MenuSuggestionItem] = []
            seen_ids: set[int] = set()

            for row in user_items:
                menu_item = self.db.query(MenuItem).filter(MenuItem.id == row.menu_item_id).first()
                if not menu_item:
                    continue

                similar = (
                    self.db.query(MenuItem)
                    .filter(
                        MenuItem.vendor_id == menu_item.vendor_id,
                        MenuItem.id != menu_item.id,
                        MenuItem.is_available == True,
                    )
                    .limit(3)
                    .all()
                )

                vendor = self.db.query(User).filter(User.id == menu_item.vendor_id).first()
                vendor_name = vendor.name if vendor else f"Vendor #{menu_item.vendor_id}"

                for s in similar:
                    if s.id in seen_ids:
                        continue
                    seen_ids.add(s.id)
                    personalized.append(
                        MenuSuggestionItem(
                            item_id=s.id,
                            item_name=s.name,
                            vendor_id=s.vendor_id,
                            vendor_name=vendor_name,
                            price_paise=s.price,
                            image_url=s.image_url,
                            is_available=s.is_available,
                            reason=f"Similar to your favorite {menu_item.name}",
                            confidence=0.8,
                        )
                    )

            trending_items = (
                self.db.query(MenuItem.id, MenuItem.name, MenuItem.vendor_id, MenuItem.price,
                              MenuItem.image_url, MenuItem.is_available,
                              func.count(OrderItem.id).label("pop"))
                .join(OrderItem, OrderItem.menu_item_id == MenuItem.id)
                .join(Order, Order.id == OrderItem.order_id)
                .filter(Order.created_at >= thirty_days_ago)
                .group_by(MenuItem.id)
                .order_by(func.count(OrderItem.id).desc())
                .limit(10)
                .all()
            )

            trending: List[MenuSuggestionItem] = []
            for r in trending_items:
                if r.id in seen_ids:
                    continue
                seen_ids.add(r.id)
                vendor = self.db.query(User).filter(User.id == r.vendor_id).first()
                vendor_name = vendor.name if vendor else f"Vendor #{r.vendor_id}"
                trending.append(
                    MenuSuggestionItem(
                        item_id=r.id,
                        item_name=r.name,
                        vendor_id=r.vendor_id,
                        vendor_name=vendor_name,
                        price_paise=r.price,
                        image_url=r.image_url,
                        is_available=r.is_available,
                        reason="Trending on campus",
                        confidence=0.6,
                    )
                )

            if not personalized and not trending:
                fallback = self.db.query(MenuItem).filter(MenuItem.is_available == True).limit(5).all()
                for mi in fallback:
                    if mi.id in seen_ids:
                        continue
                    seen_ids.add(mi.id)
                    vendor = self.db.query(User).filter(User.id == mi.vendor_id).first()
                    vendor_name = vendor.name if vendor else f"Vendor #{mi.vendor_id}"
                    personalized.append(
                        MenuSuggestionItem(
                            item_id=mi.id,
                            item_name=mi.name,
                            vendor_id=mi.vendor_id,
                            vendor_name=vendor_name,
                            price_paise=mi.price,
                            image_url=mi.image_url,
                            is_available=mi.is_available,
                            reason="Available now",
                            confidence=0.3,
                        )
                    )

            return MenuSuggestionsResponse(
                personalized=personalized[:8],
                trending=trending[:8],
            )
        except Exception:
            logger.exception("get_menu_suggestions failed for user_id=%s", user_id)
            return MenuSuggestionsResponse(personalized=[], trending=[])

    # ── 3. Smart Reorder ────────────────────────────────────────────────────

    def get_smart_reorder(self, user_id: int) -> SmartReorderResponse:
        try:
            thirty_days_ago = utcnow_naive() - timedelta(days=30)

            item_rows = (
                self.db.query(
                    OrderItem.menu_item_id,
                    func.count(OrderItem.id).label("order_count"),
                    func.avg(OrderItem.quantity).label("avg_qty"),
                    func.max(Order.created_at).label("last_ordered"),
                )
                .join(Order)
                .filter(
                    Order.user_id == user_id,
                    Order.created_at >= thirty_days_ago,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED]),
                )
                .group_by(OrderItem.menu_item_id)
                .order_by(func.count(OrderItem.id).desc())
                .limit(5)
                .all()
            )

            preferred_slot = (
                self.db.query(Order.slot_id, func.count(Order.id).label("cnt"))
                .filter(
                    Order.user_id == user_id,
                    Order.created_at >= thirty_days_ago,
                    Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED]),
                )
                .group_by(Order.slot_id)
                .order_by(func.count(Order.id).desc())
                .first()
            )

            best_slot_id = preferred_slot.slot_id if preferred_slot else None
            best_slot_time = None
            if best_slot_id:
                slot = self.db.query(Slot).filter(Slot.id == best_slot_id).first()
                if slot:
                    best_slot_time = f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"

            best_hour_row = (
                self.db.query(
                    func.extract("hour", Order.created_at).label("hour"),
                    func.count(Order.id).label("cnt"),
                )
                .filter(Order.user_id == user_id)
                .group_by(func.extract("hour", Order.created_at))
                .order_by(func.count(Order.id).desc())
                .first()
            )
            best_hour = int(best_hour_row.hour) if best_hour_row else 12
            best_reorder_time = f"{best_hour:02d}:00"

            items: List[SmartReorderItem] = []
            for row in item_rows:
                menu_item = self.db.query(MenuItem).filter(MenuItem.id == row.menu_item_id).first()
                if not menu_item:
                    continue
                vendor = self.db.query(User).filter(User.id == menu_item.vendor_id).first()
                vendor_name = vendor.name if vendor else f"Vendor #{menu_item.vendor_id}"

                items.append(
                    SmartReorderItem(
                        item_id=menu_item.id,
                        item_name=menu_item.name,
                        vendor_id=menu_item.vendor_id,
                        vendor_name=vendor_name,
                        price_paise=menu_item.price,
                        image_url=menu_item.image_url,
                        order_count=row.order_count,
                        last_ordered_at=str(row.last_ordered),
                        suggested_quantity=int(row.avg_qty),
                        suggested_slot_id=best_slot_id,
                        suggested_slot_time=best_slot_time,
                    )
                )

            return SmartReorderResponse(
                items=items,
                best_reorder_time=best_reorder_time,
                best_reorder_slot_id=best_slot_id,
            )
        except Exception:
            logger.exception("get_smart_reorder failed for user_id=%s", user_id)
            return SmartReorderResponse(items=[], best_reorder_time="12:00", best_reorder_slot_id=None)

    # ── 4. Best Pickup Time Suggestions ────────────────────────────────────

    def get_best_pickup_time(self, user_id: int) -> BestPickupTimeResponse:
        try:
            now = utcnow_naive()
            day_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

            # Determine preferred hour safely
            stored_prefs: dict = {}
            try:
                user = self.db.query(User).filter(User.id == user_id).first()
                if user is not None:
                    prefs = getattr(user, "preferences", None)
                    if isinstance(prefs, dict):
                        stored_prefs = prefs
            except Exception:
                logger.warning("Could not read user preferences for user_id=%s", user_id, exc_info=True)

            stored_hour = stored_prefs.get("preferred_pickup_hour") if isinstance(stored_prefs, dict) else None

            pref_hour_row = (
                self.db.query(
                    func.extract("hour", Order.created_at).label("hour"),
                    func.count(Order.id).label("cnt"),
                )
                .filter(Order.user_id == user_id)
                .group_by(func.extract("hour", Order.created_at))
                .order_by(func.count(Order.id).desc())
                .first()
            )
            history_hour = int(pref_hour_row.hour) if pref_hour_row else None

            if stored_hour is not None:
                preferred_hour = stored_hour
                source = "preference"
            elif history_hour is not None:
                preferred_hour = history_hour
                source = "history"
            else:
                preferred_hour = 12
                source = "default"

            # Get available slots today
            available_slots = (
                self.db.query(Slot)
                .filter(Slot.start_time >= now, Slot.start_time <= day_end, Slot.status != "full")
                .all()
            )

            slot_items: List[PickupTimeSlot] = []
            for slot in available_slots:
                utilization = (slot.current_orders / max(slot.max_orders, 1))
                if utilization >= 0.9:
                    congestion = "CRITICAL"
                elif utilization >= 0.75:
                    congestion = "HIGH"
                elif utilization >= 0.5:
                    congestion = "MEDIUM"
                else:
                    congestion = "LOW"

                base_eta = 15
                if utilization >= 0.8:
                    base_eta = 30
                elif utilization >= 0.5:
                    base_eta = 20

                delay_risk = "HIGH" if utilization > 0.9 else "MEDIUM" if utilization > 0.7 else "LOW"

                vendor = self.db.query(User).filter(User.id == slot.vendor_id).first()
                vendor_name = vendor.name if vendor else f"Vendor #{slot.vendor_id}"

                congestion_score = (1 - utilization) * 40
                hour_match = 30 if slot.start_time.hour == preferred_hour else (
                    15 if abs(slot.start_time.hour - preferred_hour) <= 1 else 0
                )
                capacity_score = min(20, (slot.max_orders - slot.current_orders) * 5)
                score = round(congestion_score + hour_match + capacity_score, 1)

                slot_items.append(
                    PickupTimeSlot(
                        slot_id=slot.id,
                        vendor_id=slot.vendor_id,
                        vendor_name=vendor_name,
                        start_time=slot.start_time.strftime("%H:%M"),
                        end_time=slot.end_time.strftime("%H:%M"),
                        eta_minutes=base_eta,
                        congestion_level=congestion,
                        delay_risk=delay_risk,
                        score=score,
                    )
                )

            slot_items.sort(key=lambda s: s.score, reverse=True)

            best = slot_items[0] if slot_items else None
            alternatives = slot_items[1:6] if len(slot_items) > 1 else []

            return BestPickupTimeResponse(
                best_slot=best,
                alternative_slots=alternatives,
                preferred_hour=preferred_hour,
                preferred_hour_source=source,
            )
        except Exception:
            logger.exception("get_best_pickup_time failed for user_id=%s", user_id)
            return BestPickupTimeResponse(
                best_slot=None,
                alternative_slots=[],
                preferred_hour=12,
                preferred_hour_source="default",
            )

    # ── 5. Peak Hour Alerts ────────────────────────────────────────────────

    def get_peak_hour_alerts(self, user_id: int) -> PeakHourAlert:
        try:
            now = utcnow_naive()
            current_hour = now.hour

            seven_days_ago = utcnow_naive() - timedelta(days=7)

            hour_counts = dict(
                self.db.query(
                    func.extract("hour", Order.created_at).label("hour"),
                    func.count(Order.id).label("cnt"),
                )
                .filter(Order.created_at >= seven_days_ago)
                .group_by(func.extract("hour", Order.created_at))
                .all()
            )

            hour_counts = {int(k): int(v) for k, v in hour_counts.items()}

            all_slots = self.db.query(Slot).all()
            total_cap = sum(s.max_orders for s in all_slots) or 1
            total_cur = sum(s.current_orders for s in all_slots)

            peak_periods: List[PeakHourPeriod] = []
            period_defs = [
                (8, 10, "Morning Rush"),
                (12, 14, "Lunch Peak"),
                (18, 20, "Dinner Peak"),
            ]

            for start, end, label in period_defs:
                volume = sum(hour_counts.get(h, 0) for h in range(start, end + 1))
                if volume > 0:
                    severity = "HIGH" if volume >= 20 else "MEDIUM" if volume >= 10 else "LOW"
                    avg_wait = 25 if severity == "HIGH" else 15 if severity == "MEDIUM" else 8
                else:
                    severity = "LOW"
                    avg_wait = 5
                    volume = 0

                peak_periods.append(
                    PeakHourPeriod(
                        start_hour=start,
                        end_hour=end,
                        label=label,
                        severity=severity,
                        avg_wait_minutes=avg_wait,
                        order_volume=volume,
                    )
                )

            is_peak = False
            current_period = None
            for p in peak_periods:
                if p.start_hour <= current_hour <= p.end_hour:
                    is_peak = True
                    current_period = p
                    break

            off_peak: List[Dict[str, Any]] = []
            for h in range(6, 22):
                is_in_peak = any(p.start_hour <= h <= p.end_hour for p in peak_periods)
                if not is_in_peak and hour_counts.get(h, 0) < 5:
                    off_peak.append({
                        "hour": h,
                        "label": f"{h:02d}:00 - {h + 1:02d}:00",
                        "expected_wait_minutes": 8,
                    })

            if is_peak and current_period:
                suggested_action = (
                    f"Peak hours now ({current_period.label}). "
                    f"Consider ordering at an off-peak time for faster pickup."
                )
            else:
                suggested_action = "Great time to order! Current wait times are low."

            return PeakHourAlert(
                is_peak_now=is_peak,
                current_period=current_period,
                peak_periods_today=peak_periods,
                off_peak_windows=off_peak,
                suggested_action=suggested_action,
            )
        except Exception:
            logger.exception("get_peak_hour_alerts failed for user_id=%s", user_id)
            return PeakHourAlert(
                is_peak_now=False,
                current_period=None,
                peak_periods_today=[],
                off_peak_windows=[],
                suggested_action="Unable to load peak hour data. Please try again.",
            )

    # ── 6. Popular Nearby ───────────────────────────────────────────────────

    def get_popular_nearby(self) -> PopularNearbyResponse:
        try:
            thirty_days_ago = utcnow_naive() - timedelta(days=30)

            food_vendors: List[PopularNearbyVendor] = []
            stationery_vendors: List[PopularNearbyVendor] = []

            vendors = (
                self.db.query(User)
                .filter(User.role == UserRole.VENDOR, User.is_approved == True)
                .all()
            )

            for vendor in vendors:
                order_count = (
                    self.db.query(func.count(Order.id))
                    .filter(Order.vendor_id == vendor.id, Order.created_at >= thirty_days_ago)
                    .scalar() or 0
                )

                avg_rating = (
                    self.db.query(func.avg(VendorReview.rating))
                    .filter(VendorReview.vendor_id == vendor.id)
                    .scalar() or 0.0
                )

                current_slots = self.db.query(Slot).filter(Slot.vendor_id == vendor.id).all()
                total_cap = sum(s.max_orders for s in current_slots) or 1
                total_cur = sum(s.current_orders for s in current_slots)
                util = total_cur / total_cap
                load = "HIGH" if util >= 0.8 else "MEDIUM" if util >= 0.5 else "LOW"

                vp = getattr(vendor, "vendor_profile", None)
                category = getattr(vp, "category", None) if vp else None
                logo_url = getattr(vp, "logo_url", None) if vp else None

                item = PopularNearbyVendor(
                    vendor_id=vendor.id,
                    vendor_name=vendor.name or f"Vendor #{vendor.id}",
                    vendor_type=vendor.vendor_type,
                    category=category,
                    logo_url=logo_url,
                    order_count=order_count,
                    avg_rating=round(float(avg_rating), 1),
                    live_load=load,
                )

                if vendor.vendor_type == "food":
                    food_vendors.append(item)
                else:
                    stationery_vendors.append(item)

            food_vendors.sort(key=lambda v: v.order_count, reverse=True)
            stationery_vendors.sort(key=lambda v: v.order_count, reverse=True)

            return PopularNearbyResponse(
                food_vendors=food_vendors[:10],
                stationery_vendors=stationery_vendors[:10],
            )
        except Exception:
            logger.exception("get_popular_nearby failed")
            return PopularNearbyResponse(food_vendors=[], stationery_vendors=[])
