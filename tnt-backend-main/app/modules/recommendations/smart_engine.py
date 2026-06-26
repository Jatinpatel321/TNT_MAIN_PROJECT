"""
Smart Recommendation Engine
==========================

Extends the existing recommendation engine with:

1. User behaviour learning (vendor visits, menu clicks, search history)
2. Preference learning (favourite vendors, items, categories, timings)
3. Time-of-day and frequency-aware recommendations
4. "Because You Ordered" - order-based collaborative associations

Integrates with:
    - Existing engine.py (association rules + trending)
    - behaviour_service.py (behaviour tracking)
    - Redis cache layer
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.users.model import User
from app.modules.slots.model import Slot
from app.modules.feedback.model import VendorReview

from app.modules.recommendations.models import UserBehaviour, UserPreferenceSnapshot
from app.modules.recommendations.behaviour_service import BehaviourService
from app.modules.recommendations.engine import RecommendationEngine, ASSOCIATION_RULES, _normalise

logger = logging.getLogger("tnt.recommendations.smart_engine")

CACHE_TTL_RECOMMENDATIONS = 300  # 5 minutes
CACHE_TTL_VENDORS = 600  # 10 minutes
CACHE_TTL_MENU = 300  # 5 minutes


class SmartRecommendationEngine:
    """Production-ready recommendation engine with behaviour learning and caching."""

    def __init__(self, db: Session):
        self.db = db
        self.behaviour = BehaviourService(db)
        self._base_engine = RecommendationEngine(db)

    # ── Cache helpers ──────────────────────────────────────────────────

    def _get_cache(self):
        """Lazy-import to avoid circular dependency at module level."""
        from app.core.redis_cache import cache_service
        return cache_service

    async def _cache_get(self, key: str) -> Optional[Any]:
        try:
            cache = self._get_cache()
            return await cache.get("recommendations", key)
        except Exception:
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int = CACHE_TTL_RECOMMENDATIONS) -> None:
        try:
            cache = self._get_cache()
            await cache.set("recommendations", key, value, ttl)
        except Exception:
            pass

    async def _cache_invalidate(self, user_id: int) -> None:
        try:
            cache = self._get_cache()
            await cache.invalidate_pattern(f"cache:recommendations:*{user_id}*")
        except Exception:
            pass

    # ── Public API: GET /user/recommendations ──────────────────────────

    async def get_recommendations(self, user_id: int, limit: int = 20) -> dict[str, Any]:
        """Full recommendation payload with all categories.

        Returns:
            - frequently_ordered: Items the user orders most
            - recommended_for_you: Hybrid personalized + association picks
            - trending_near_you: Campus-wide trending items (time-of-day aware)
            - because_you_ordered: Items commonly bought together with user's purchases
            - personalized_vendors: Top vendor picks for this user
        """
        # Try cache first
        cache_key = f"recs:{user_id}:v2"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        # Compute recommendations
        snapshot = self.behaviour.get_preference_snapshot(user_id)
        frequently_ordered = self._frequently_ordered(user_id, snapshot, limit=8)
        recommended_for_you = self._recommended_for_you(user_id, snapshot, limit=8)
        trending_near_you = self._trending_near_you(limit=8)
        because_you_ordered = self._because_you_ordered(user_id, limit=6)
        personalized_vendors = self._personalized_vendors(user_id, snapshot, limit=8)

        result = {
            "user_id": user_id,
            "frequently_ordered": frequently_ordered,
            "recommended_for_you": recommended_for_you,
            "trending_near_you": trending_near_you,
            "because_you_ordered": because_you_ordered,
            "personalized_vendors": personalized_vendors,
        }

        # Cache the result
        await self._cache_set(cache_key, result)
        return result

    # ── Public API: GET /user/personalized-vendors ─────────────────────

    async def get_personalized_vendors(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Get personalized vendor recommendations based on preferences."""
        cache_key = f"vendors:{user_id}:v2"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        snapshot = self.behaviour.get_preference_snapshot(user_id)
        vendors = self._personalized_vendors(user_id, snapshot, limit)

        await self._cache_set(cache_key, vendors, CACHE_TTL_VENDORS)
        return vendors

    # ── Public API: GET /user/personalized-menu ────────────────────────

    async def get_personalized_menu(self, user_id: int, vendor_id: Optional[int] = None,
                                     limit: int = 10) -> list[dict[str, Any]]:
        """Get personalized menu items for a user."""
        cache_key = f"menu:{user_id}:{vendor_id or 'all'}:v2"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        snapshot = self.behaviour.get_preference_snapshot(user_id)
        items = self._personalized_menu_items(user_id, snapshot, vendor_id, limit)

        await self._cache_set(cache_key, items, CACHE_TTL_MENU)
        return items

    # ── Frequently Ordered ────────────────────────────────────────────

    def _frequently_ordered(self, user_id: int, snapshot: Optional[UserPreferenceSnapshot],
                             limit: int = 8) -> list[dict[str, Any]]:
        """Items the user has ordered most frequently, with current availability."""
        if snapshot and snapshot.favourite_menu_items:
            item_ids = [item["item_id"] for item in snapshot.favourite_menu_items[:limit]]
            items_map = self._menu_items_by_ids(item_ids)
            results = []
            for fi in snapshot.favourite_menu_items[:limit]:
                mi = items_map.get(fi["item_id"])
                if mi and mi.is_available:
                    results.append(self._item_to_dict(mi, fi, f"You've ordered {fi['order_count']} times"))
                elif mi:
                    results.append(self._item_to_dict(mi, fi, "Currently unavailable"))
                if len(results) >= limit:
                    break
            return results

        # Fallback: use order history directly
        return self._fallback_frequent_items(user_id, limit)

    def _fallback_frequent_items(self, user_id: int, limit: int) -> list[dict[str, Any]]:
        """Query order history directly if snapshot unavailable."""
        thirty_days = utcnow_naive() - timedelta(days=90)
        rows = (
            self.db.query(
                OrderItem.menu_item_id,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.quantity).label("total_qty"),
            )
            .join(Order)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= thirty_days,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(OrderItem.menu_item_id)
            .order_by(func.count(OrderItem.id).desc())
            .limit(limit)
            .all()
        )

        results = []
        for r in rows:
            mi = self.db.query(MenuItem).filter(MenuItem.id == r.menu_item_id).first()
            if mi:
                results.append({
                    "id": mi.id,
                    "name": mi.name,
                    "description": mi.description or "",
                    "price": mi.price,
                    "image_url": mi.image_url,
                    "vendor_id": mi.vendor_id,
                    "is_available": mi.is_available,
                    "reason": f"You've ordered {r.order_count} times",
                    "score": round(min(1.0, r.order_count / 10), 2),
                    "order_count": r.order_count,
                })
        return results

    # ── Recommended For You ────────────────────────────────────────────

    def _recommended_for_you(self, user_id: int, snapshot: Optional[UserPreferenceSnapshot],
                              limit: int = 8) -> list[dict[str, Any]]:
        """Hybrid recommendations: preference-based + association + time-of-day boost."""
        results = []
        seen_ids: set[int] = set()

        # 1. Get user's top vendors and categories from snapshot
        preferred_vendor_ids: list[int] = []
        preferred_categories: list[str] = []
        preferred_hour: int = 12

        if snapshot:
            preferred_vendor_ids = [v["vendor_id"] for v in snapshot.favourite_vendors[:5]]
            preferred_categories = [c["category"] for c in snapshot.favourite_categories[:3]]
            preferred_hour = snapshot.preferred_timings.get("preferred_hour", 12)

        # 2. Items from preferred vendors that user hasn't ordered
        ordered_item_ids = set()
        if snapshot:
            ordered_item_ids = {i["item_id"] for i in snapshot.favourite_menu_items}

        if preferred_vendor_ids:
            candidates = (
                self.db.query(MenuItem)
                .filter(
                    MenuItem.vendor_id.in_(preferred_vendor_ids),
                    MenuItem.id.notin_(ordered_item_ids) if ordered_item_ids else True,
                    MenuItem.is_available == True,
                )
                .order_by(MenuItem.id)
                .limit(limit * 2)
                .all()
            )
            for mi in candidates:
                if mi.id not in seen_ids:
                    seen_ids.add(mi.id)
                    results.append({
                        "id": mi.id,
                        "name": mi.name,
                        "description": mi.description or "",
                        "price": mi.price,
                        "image_url": mi.image_url,
                        "vendor_id": mi.vendor_id,
                        "is_available": mi.is_available,
                        "reason": "From a vendor you love",
                        "score": 0.85,
                    })

        # 3. Time-of-day appropriate items
        current_hour = utcnow_naive().hour
        tod = self._time_of_day(current_hour)
        tod_filtered = self._items_for_time_of_day(tod, preferred_categories, limit)
        for mi in tod_filtered:
            if mi.id not in seen_ids:
                seen_ids.add(mi.id)
                results.append({
                    "id": mi.id,
                    "name": mi.name,
                    "description": mi.description or "",
                    "price": mi.price,
                    "image_url": mi.image_url,
                    "vendor_id": mi.vendor_id,
                    "is_available": mi.is_available,
                    "reason": f"Perfect for {tod}",
                    "score": 0.8,
                })

        # 4. Association-rule pairings from user's order history
        if snapshot:
            ordered_names = [i["name"] for i in snapshot.favourite_menu_items[:5]]
            assoc_items = self._get_association_items(ordered_names)
            for a in assoc_items:
                if a.get("id") and a["id"] not in seen_ids:
                    seen_ids.add(a["id"])
                    a["reason"] = "Recommended for you"
                    results.append(a)

        return results[:limit]

    # ── Trending Near You (time-of-day + campus-wide) ──────────────────

    def _trending_near_you(self, limit: int = 8) -> list[dict[str, Any]]:
        """Trending items, ranked by recency + popularity + time-of-day affinity."""
        current_hour = utcnow_naive().hour
        tod = self._time_of_day(current_hour)

        # Query trending: items most ordered in last 7 days
        seven_days = utcnow_naive() - timedelta(days=7)

        rows = (
            self.db.query(
                OrderItem.menu_item_id,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.count(OrderItem.id).label("order_count"),
            )
            .join(Order)
            .filter(Order.created_at >= seven_days)
            .group_by(OrderItem.menu_item_id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit * 2)
            .all()
        )

        item_ids = [r.menu_item_id for r in rows]
        items_map = self._menu_items_by_ids(item_ids)

        results = []
        for r in rows:
            mi = items_map.get(r.menu_item_id)
            if mi and mi.is_available:
                tod_boost = 1.0
                if self._item_matches_tod(mi, tod):
                    tod_boost = 1.3
                score = round(min(1.0, float(r.total_qty or 0) / 30) * tod_boost, 2)

                results.append({
                    "id": mi.id,
                    "name": mi.name,
                    "description": mi.description or "",
                    "price": mi.price,
                    "image_url": mi.image_url,
                    "vendor_id": mi.vendor_id,
                    "is_available": mi.is_available,
                    "reason": f"Trending right now for {tod}",
                    "score": score,
                    "order_count": r.order_count,
                })
                if len(results) >= limit:
                    break

        if not results:
            return self._fallback_popular_items(limit)

        return results[:limit]

    # ── Because You Ordered ────────────────────────────────────────────

    def _because_you_ordered(self, user_id: int, limit: int = 6) -> list[dict[str, Any]]:
        """Items commonly ordered together with what this user has ordered.

        Uses collaborative association: users who ordered X also ordered Y.
        """
        ninety_days = utcnow_naive() - timedelta(days=90)

        # Get items the user ordered
        user_items = (
            self.db.query(OrderItem.menu_item_id)
            .join(Order)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= ninety_days,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .distinct()
            .all()
        )
        user_item_ids = {r.menu_item_id for r in user_items}

        if not user_item_ids:
            return self._base_engine._demo_recommendations()[0][:limit]

        # Find orders containing any of user's items
        co_orders = (
            self.db.query(OrderItem.order_id)
            .filter(OrderItem.menu_item_id.in_(user_item_ids))
            .distinct()
            .subquery()
        )

        # Find items in those orders that user hasn't ordered
        co_items = (
            self.db.query(
                OrderItem.menu_item_id,
                func.count(OrderItem.id).label("co_occurrence"),
            )
            .filter(
                OrderItem.order_id.in_(co_orders),
                OrderItem.menu_item_id.notin_(user_item_ids),
            )
            .group_by(OrderItem.menu_item_id)
            .order_by(func.count(OrderItem.id).desc())
            .limit(limit * 2)
            .all()
        )

        items_map = self._menu_items_by_ids([r.menu_item_id for r in co_items])

        results = []
        seen_ids: set[int] = set()
        for r in co_items:
            mi = items_map.get(r.menu_item_id)
            if mi and mi.is_available and mi.id not in seen_ids:
                seen_ids.add(mi.id)
                results.append({
                    "id": mi.id,
                    "name": mi.name,
                    "description": mi.description or "",
                    "price": mi.price,
                    "image_url": mi.image_url,
                    "vendor_id": mi.vendor_id,
                    "is_available": mi.is_available,
                    "reason": f"Because you ordered {self._get_item_names(user_item_ids)[:2]}",
                    "score": round(min(1.0, r.co_occurrence / 5), 2),
                    "co_occurrence": r.co_occurrence,
                })
                if len(results) >= limit:
                    break

        # Fallback to association rules if no co-occurrence found
        if not results:
            ordered_names = self._get_item_names(user_item_ids)
            assoc = self._get_association_items(ordered_names)
            for a in assoc:
                if a.get("id") and a["id"] not in user_item_ids:
                    a["reason"] = "Because you ordered similar items"
                    a["score"] = 0.7
                    results.append(a)
                    if len(results) >= limit:
                        break

        return results[:limit]

    # ── Personalized Vendors ──────────────────────────────────────────

    def _personalized_vendors(self, user_id: int, snapshot: Optional[UserPreferenceSnapshot],
                               limit: int = 10) -> list[dict[str, Any]]:
        """Score and rank vendors for this user based on preferences."""
        from app.modules.vendors.profile_models import VendorProfile

        preferred_ids = set()
        if snapshot:
            preferred_ids = {v["vendor_id"] for v in snapshot.favourite_vendors[:5]}

        vendors = (
            self.db.query(User)
            .filter(User.role == "vendor", User.is_approved == True)
            .all()
        )

        results = []
        for v in vendors:
            base_score = 30.0

            # Frequency bonus from snapshot
            freq_bonus = 0.0
            if snapshot:
                for fv in snapshot.favourite_vendors:
                    if fv["vendor_id"] == v.id:
                        freq_bonus = min(fv["score"] / 2, 40)
                        break

            # Load-based adjustment
            current_slots = self.db.query(Slot).filter(Slot.vendor_id == v.id).all()
            total_cap = sum(s.max_orders for s in current_slots) or 1
            total_cur = sum(s.current_orders for s in current_slots)
            utilization = total_cur / total_cap
            load_bonus = (1 - utilization) * 25

            # Rating bonus
            avg_rating = (
                self.db.query(func.avg(VendorReview.rating))
                .filter(VendorReview.vendor_id == v.id)
                .scalar() or 0
            )
            rating_bonus = float(avg_rating) * 5

            total_score = base_score + freq_bonus + load_bonus + rating_bonus

            # Live load label
            if utilization >= 0.9:
                load_label = "HIGH"
            elif utilization >= 0.6:
                load_label = "MEDIUM"
            else:
                load_label = "LOW"

            # Reason
            if v.id in preferred_ids:
                reason = "You've ordered here before"
            elif load_label == "LOW":
                reason = "Quick pickup available"
            elif float(avg_rating) >= 4.0:
                reason = "Highly rated"
            else:
                reason = "Popular on campus"

            results.append({
                "vendor_id": v.id,
                "vendor_name": v.name or f"Vendor #{v.id}",
                "vendor_type": v.vendor_type,
                "logo_url": None,
                "rank_score": round(total_score, 1),
                "live_load": load_label,
                "express_pickup": utilization < 0.5,
                "reason": reason,
            })

        results.sort(key=lambda x: x["rank_score"], reverse=True)
        return results[:limit]

    # ── Personalized Menu Items ───────────────────────────────────────

    def _personalized_menu_items(self, user_id: int,
                                  snapshot: Optional[UserPreferenceSnapshot],
                                  vendor_id: Optional[int] = None,
                                  limit: int = 10) -> list[dict[str, Any]]:
        """Menu items personalized for this user, optionally filtered by vendor."""
        if snapshot and snapshot.favourite_menu_items:
            ordered_ids = {i["item_id"] for i in snapshot.favourite_menu_items}

            # Query items from preferred vendors, excluding already ordered
            preferred_vendor_ids = [v["vendor_id"] for v in snapshot.favourite_vendors[:5]]

            query = self.db.query(MenuItem).filter(MenuItem.is_available == True)
            if vendor_id:
                query = query.filter(MenuItem.vendor_id == vendor_id)
            elif preferred_vendor_ids:
                query = query.filter(MenuItem.vendor_id.in_(preferred_vendor_ids))

            query = query.order_by(MenuItem.id).limit(limit * 2)
            items = query.all()

            results = []
            for mi in items:
                was_ordered = mi.id in ordered_ids
                reason = "You've ordered this before" if was_ordered else "You might like this"
                results.append({
                    "item_id": mi.id,
                    "item_name": mi.name,
                    "description": mi.description or "",
                    "price_paise": mi.price,
                    "vendor_id": mi.vendor_id,
                    "image_url": mi.image_url,
                    "is_available": mi.is_available,
                    "reason": reason,
                    "confidence": 0.9 if was_ordered else 0.65,
                    "ordered_before": was_ordered,
                })

            return results[:limit]

        # Fallback: available items
        query = self.db.query(MenuItem).filter(MenuItem.is_available == True)
        if vendor_id:
            query = query.filter(MenuItem.vendor_id == vendor_id)
        items = query.limit(limit).all()

        return [{
            "item_id": mi.id,
            "item_name": mi.name,
            "description": mi.description or "",
            "price_paise": mi.price,
            "vendor_id": mi.vendor_id,
            "image_url": mi.image_url,
            "is_available": mi.is_available,
            "reason": "Available now",
            "confidence": 0.5,
            "ordered_before": False,
        } for mi in items]

    # ── Behaviour Recording API (for frontend integration) ────────────

    def record_interaction(self, user_id: int, event_type: str,
                           vendor_id: Optional[int] = None,
                           menu_item_id: Optional[int] = None) -> dict[str, Any]:
        """Record a user interaction event for behaviour learning.

        This is intended to be called from frontend interaction hooks.
        """
        self.behaviour.record_event(
            user_id=user_id,
            event_type=event_type,
            vendor_id=vendor_id,
            menu_item_id=menu_item_id,
            weight=1.0,
        )

        # Invalidate cache so next request picks up new data
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._cache_invalidate(user_id))
        except RuntimeError:
            pass

        return {"recorded": True, "event_type": event_type}

    # ── Helpers ───────────────────────────────────────────────────────

    def _item_to_dict(self, mi: MenuItem, snapshot_data: dict[str, Any],
                       reason: str = "") -> dict[str, Any]:
        """Convert MenuItem + snapshot data to recommendation dict."""
        pairs = ASSOCIATION_RULES.get(_normalise(mi.name), [])
        return {
            "id": mi.id,
            "name": mi.name,
            "description": mi.description or f"Delicious {mi.name}",
            "price": mi.price,
            "image_url": mi.image_url,
            "vendor_id": mi.vendor_id,
            "is_available": mi.is_available,
            "reason": reason,
            "score": round(snapshot_data.get("score", 0) / 100, 2),
            "order_count": snapshot_data.get("order_count", 0),
            "pairs_with": pairs if pairs else None,
        }

    def _menu_items_by_ids(self, item_ids: list[int]) -> dict[int, MenuItem]:
        """Batch load menu items by IDs for efficient lookup."""
        items = self.db.query(MenuItem).filter(MenuItem.id.in_(item_ids)).all()
        return {mi.id: mi for mi in items}

    def _get_association_items(self, item_names: list[str]) -> list[dict[str, Any]]:
        """Get association-rule suggestions from a list of item names."""
        return self._base_engine._apply_rules(item_names)

    def _get_item_names(self, item_ids: set[int]) -> list[str]:
        """Resolve item IDs to names."""
        items = self.db.query(MenuItem).filter(MenuItem.id.in_(item_ids)).all()
        return [mi.name for mi in items]

    def _time_of_day(self, hour: int) -> str:
        """Classify hour into time-of-day period."""
        if 6 <= hour < 11:
            return "morning"
        elif 11 <= hour < 15:
            return "lunch"
        elif 15 <= hour < 18:
            return "afternoon"
        else:
            return "evening"

    def _items_for_time_of_day(self, tod: str, preferred_categories: list[str],
                                 limit: int = 8) -> list[MenuItem]:
        """Get items appropriate for the time of day."""
        query = self.db.query(MenuItem).filter(MenuItem.is_available == True)

        # Time-of-day keyword matching
        tod_keywords = {
            "morning": ["chai", "coffee", "tea", "samosa", "idli", "dosa", "vada", "poha", "upma", "bread", "egg"],
            "lunch": ["biryani", "thali", "rice", "roti", "curry", "paneer", "dal", "chole", "rajma", "burger", "wrap"],
            "afternoon": ["snack", "fries", "sandwich", "pasta", "noodles", "manchurian", "roll", "pizza"],
            "evening": ["pizza", "burger", "fries", "pasta", "chai", "coffee", "roll", "noodles", "cold coffee", "ice cream"],
        }

        keywords = tod_keywords.get(tod, [])
        from sqlalchemy import or_
        keyword_filters = [MenuItem.name.ilike(f"%{kw}%") for kw in keywords]
        if preferred_categories:
            keyword_filters.append(MenuItem.category.in_(preferred_categories))
        query = query.filter(or_(*keyword_filters))

        return query.limit(limit).all()

    def _item_matches_tod(self, mi: MenuItem, tod: str) -> bool:
        """Heuristic check if item matches time of day."""
        tod_keywords = {
            "morning": ["chai", "coffee", "tea", "idli", "dosa", "vada", "poha", "upma", "egg"],
            "lunch": ["biryani", "thali", "rice", "roti", "curry", "paneer", "dal"],
            "afternoon": ["snack", "fries", "sandwich", "pasta", "noodles"],
            "evening": ["pizza", "burger", "fries", "chai", "coffee", "cold coffee"],
        }
        name_lower = mi.name.lower()
        for kw in tod_keywords.get(tod, []):
            if kw in name_lower:
                return True
        return False

    def _fallback_popular_items(self, limit: int) -> list[dict[str, Any]]:
        """Fallback to generic popular items."""
        items = (
            self.db.query(MenuItem)
            .filter(MenuItem.is_available == True)
            .order_by(MenuItem.id)
            .limit(limit)
            .all()
        )
        return [{
            "id": mi.id,
            "name": mi.name,
            "description": mi.description or "",
            "price": mi.price,
            "image_url": mi.image_url,
            "vendor_id": mi.vendor_id,
            "is_available": mi.is_available,
            "reason": "Popular on campus",
            "score": 0.5,
        } for mi in items]

