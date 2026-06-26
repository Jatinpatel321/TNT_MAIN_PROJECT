"""
User Behaviour Tracking Service
================================

Records and analyses user interactions for preference learning.
Provides the raw data for the Smart Recommendation Engine.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.recommendations.models import UserBehaviour, UserPreferenceSnapshot

logger = logging.getLogger("tnt.recommendations.behaviour")


class BehaviourService:
    """Tracks and analyses user behaviour for personalization."""

    def __init__(self, db: Session):
        self.db = db

    # ── Event Recording ──────────────────────────────────────────────────

    def record_event(
        self,
        user_id: int,
        event_type: str,
        vendor_id: Optional[int] = None,
        menu_item_id: Optional[int] = None,
        order_id: Optional[int] = None,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        search_results_count: Optional[int] = None,
        source_screen: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        referrer: Optional[str] = None,
        weight: float = 1.0,
    ) -> UserBehaviour:
        """Record a single user interaction event."""
        event = UserBehaviour(
            user_id=user_id,
            event_type=event_type,
            vendor_id=vendor_id,
            menu_item_id=menu_item_id,
            order_id=order_id,
            category=category,
            search_query=search_query,
            search_results_count=search_results_count,
            source_screen=source_screen,
            duration_seconds=duration_seconds,
            referrer=referrer,
            weight=weight,
        )
        self.db.add(event)
        self.db.commit()
        return event

    def record_vendor_visit(self, user_id: int, vendor_id: int, source: str = "home") -> None:
        """Track a vendor page visit."""
        self.record_event(
            user_id=user_id,
            event_type="page_view",
            vendor_id=vendor_id,
            source_screen=source,
            weight=0.8,
        )

    def record_menu_click(self, user_id: int, menu_item_id: int, vendor_id: int, source: str = "menu") -> None:
        """Track a menu item click/view."""
        self.record_event(
            user_id=user_id,
            event_type="item_click",
            menu_item_id=menu_item_id,
            vendor_id=vendor_id,
            source_screen=source,
            weight=0.6,
        )

    def record_search(self, user_id: int, query: str, results_count: int = 0) -> None:
        """Track a search query."""
        self.record_event(
            user_id=user_id,
            event_type="search",
            search_query=query,
            search_results_count=results_count,
            source_screen="search",
            weight=0.9,
        )

    def record_order_placed(self, user_id: int, order_id: int, vendor_id: int) -> None:
        """Track an order placement event."""
        self.record_event(
            user_id=user_id,
            event_type="order_placed",
            order_id=order_id,
            vendor_id=vendor_id,
            source_screen="checkout",
            weight=1.5,
        )

    def record_category_view(self, user_id: int, category: str, source: str = "home") -> None:
        """Track a category browse."""
        self.record_event(
            user_id=user_id,
            event_type="category_view",
            category=category,
            source_screen=source,
            weight=0.5,
        )

    def record_favourite(self, user_id: int, vendor_id: int) -> None:
        """Track when a user favourites a vendor."""
        self.record_event(
            user_id=user_id,
            event_type="favourite",
            vendor_id=vendor_id,
            source_screen="vendor_detail",
            weight=2.0,
        )

    # ── Behaviour Analytics ──────────────────────────────────────────────

    def get_recent_events(self, user_id: int, event_type: Optional[str] = None,
                          days: int = 30, limit: int = 100) -> list[UserBehaviour]:
        """Get recent events for a user, optionally filtered by type."""
        since = utcnow_naive() - timedelta(days=days)
        query = self.db.query(UserBehaviour).filter(
            UserBehaviour.user_id == user_id,
            UserBehaviour.created_at >= since,
        )
        if event_type:
            query = query.filter(UserBehaviour.event_type == event_type)
        return query.order_by(UserBehaviour.created_at.desc()).limit(limit).all()

    def get_most_viewed_vendors(self, user_id: int, days: int = 30, limit: int = 10) -> list[dict[str, Any]]:
        """Get vendors the user has viewed most frequently."""
        since = utcnow_naive() - timedelta(days=days)
        rows = (
            self.db.query(
                UserBehaviour.vendor_id,
                func.count(UserBehaviour.id).label("view_count"),
                func.max(UserBehaviour.created_at).label("last_viewed"),
            )
            .filter(
                UserBehaviour.user_id == user_id,
                UserBehaviour.created_at >= since,
                UserBehaviour.event_type.in_(["page_view", "item_click"]),
                UserBehaviour.vendor_id.isnot(None),
            )
            .group_by(UserBehaviour.vendor_id)
            .order_by(func.count(UserBehaviour.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "vendor_id": r.vendor_id,
                "view_count": r.view_count,
                "last_viewed": r.last_viewed.isoformat() if r.last_viewed else None,
            }
            for r in rows
        ]

    def get_category_affinity(self, user_id: int, days: int = 30) -> list[dict[str, Any]]:
        """Get the user's affinity scores for different categories."""
        since = utcnow_naive() - timedelta(days=days)
        rows = (
            self.db.query(
                UserBehaviour.category,
                func.count(UserBehaviour.id).label("interaction_count"),
                func.sum(UserBehaviour.weight).label("total_weight"),
            )
            .filter(
                UserBehaviour.user_id == user_id,
                UserBehaviour.created_at >= since,
                UserBehaviour.category.isnot(None),
            )
            .group_by(UserBehaviour.category)
            .order_by(func.sum(UserBehaviour.weight).desc())
            .all()
        )
        return [
            {
                "category": r.category,
                "interaction_count": r.interaction_count,
                "affinity_score": round(float(r.total_weight or 0), 2),
            }
            for r in rows
        ]

    def get_search_history(self, user_id: int, days: int = 30, limit: int = 20) -> list[dict[str, Any]]:
        """Get the user's recent search queries."""
        since = utcnow_naive() - timedelta(days=days)
        rows = (
            self.db.query(
                UserBehaviour.search_query,
                func.count(UserBehaviour.id).label("query_count"),
                func.avg(UserBehaviour.search_results_count).label("avg_results"),
                func.max(UserBehaviour.created_at).label("last_searched"),
            )
            .filter(
                UserBehaviour.user_id == user_id,
                UserBehaviour.created_at >= since,
                UserBehaviour.event_type == "search",
                UserBehaviour.search_query.isnot(None),
            )
            .group_by(UserBehaviour.search_query)
            .order_by(func.count(UserBehaviour.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "query": r.search_query,
                "query_count": r.query_count,
                "avg_results": int(r.avg_results or 0),
                "last_searched": r.last_searched.isoformat() if r.last_searched else None,
            }
            for r in rows
        ]

    def get_ordering_frequency(self, user_id: int, days: int = 90) -> dict[str, Any]:
        """Calculate order frequency patterns."""
        since = utcnow_naive() - timedelta(days=days)
        rows = (
            self.db.query(
                func.date(Order.created_at).label("order_date"),
                func.count(Order.id).label("order_count"),
            )
            .filter(Order.user_id == user_id, Order.created_at >= since)
            .group_by(func.date(Order.created_at))
            .all()
        )

        total_orders = sum(r.order_count for r in rows)
        unique_days = len(rows)
        days_span = max((utcnow_naive() - since).days, 1)

        avg_frequency_days = days_span / max(unique_days, 1)

        # Classify frequency
        if avg_frequency_days <= 1.5:
            frequency_label = "daily"
        elif avg_frequency_days <= 4:
            frequency_label = "frequent"
        elif avg_frequency_days <= 10:
            frequency_label = "weekly"
        else:
            frequency_label = "occasional"

        return {
            "total_orders": total_orders,
            "unique_ordering_days": unique_days,
            "avg_frequency_days": round(avg_frequency_days, 1),
            "frequency_label": frequency_label,
            "daily_distribution": {
                str(r.order_date): r.order_count for r in rows
            },
        }

    def get_ordering_times(self, user_id: int, days: int = 90) -> dict[str, Any]:
        """Get preferred ordering times distribution."""
        since = utcnow_naive() - timedelta(days=days)
        rows = (
            self.db.query(
                func.extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("count"),
            )
            .filter(Order.user_id == user_id, Order.created_at >= since)
            .group_by(func.extract("hour", Order.created_at))
            .order_by(func.count(Order.id).desc())
            .all()
        )

        hour_distribution = {int(r.hour): r.count for r in rows}
        preferred_hour = int(rows[0].hour) if rows else 12

        return {
            "preferred_hour": preferred_hour,
            "hour_distribution": hour_distribution,
            "total_orders_from_history": sum(r.count for r in rows),
        }

    # ── Preference Snapshot Computation ─────────────────────────────────

    def compute_preference_snapshot(self, user_id: int) -> UserPreferenceSnapshot:
        """Compute or update the materialised preference snapshot for a user."""
        days = 90
        since = utcnow_naive() - timedelta(days=days)

        # ── Favourite vendors ──────────────────────────────────────────
        vendor_rows = (
            self.db.query(
                Order.vendor_id,
                func.count(Order.id).label("order_count"),
                func.max(Order.created_at).label("last_order"),
            )
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(Order.vendor_id)
            .order_by(func.count(Order.id).desc())
            .limit(20)
            .all()
        )

        total_orders = sum(r.order_count for r in vendor_rows)

        favourite_vendors = []
        for r in vendor_rows:
            score = round(r.order_count / max(total_orders, 1) * 100, 2)
            favourite_vendors.append({
                "vendor_id": r.vendor_id,
                "order_count": r.order_count,
                "score": score,
                "last_order": r.last_order.isoformat() if r.last_order else None,
            })

        # ── Favourite menu items ───────────────────────────────────────
        item_rows = (
            self.db.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.quantity).label("total_quantity"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(OrderItem.menu_item_id, MenuItem.name)
            .order_by(func.count(OrderItem.id).desc())
            .limit(30)
            .all()
        )

        favourite_items = []
        for r in item_rows:
            score = round((r.order_count * r.total_quantity) / max(total_orders, 1) * 100, 2)
            favourite_items.append({
                "item_id": r.menu_item_id,
                "name": r.name,
                "order_count": r.order_count,
                "total_quantity": int(r.total_quantity or 0),
                "score": score,
            })

        # ── Favourite categories ───────────────────────────────────────
        cat_rows = (
            self.db.query(
                MenuItem.category,
                func.count(OrderItem.id).label("item_count"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(MenuItem.category)
            .order_by(func.count(OrderItem.id).desc())
            .all()
        )

        total_cat_items = sum(r.item_count for r in cat_rows) or 1
        favourite_categories = [
            {
                "category": r.category or "food",
                "score": round(r.item_count / total_cat_items * 100, 2),
            }
            for r in cat_rows
        ]

        # ── Preferred timings ──────────────────────────────────────────
        timing_data = self.get_ordering_times(user_id, days)

        # ── Vendor types ───────────────────────────────────────────────
        from app.modules.users.model import User
        vendor_type_rows = (
            self.db.query(User.vendor_type, func.count(Order.id).label("cnt"))
            .join(Order, Order.vendor_id == User.id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(User.vendor_type)
            .order_by(func.count(Order.id).desc())
            .all()
        )
        preferred_vendor_types = [r.vendor_type for r in vendor_type_rows]

        # ── Is veg preferred? ──────────────────────────────────────────
        item_counts = (
            self.db.query(
                MenuItem.is_veg,
                func.count(OrderItem.id).label("cnt"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(MenuItem.is_veg)
            .all()
        )
        veg_count = 0
        non_veg_count = 0
        for r in item_counts:
            if r.is_veg is True:
                veg_count += r.cnt
            elif r.is_veg is False:
                non_veg_count += r.cnt

        if veg_count > non_veg_count and veg_count > 0:
            is_veg_preferred = 1
        elif non_veg_count > veg_count and non_veg_count > 0:
            is_veg_preferred = 0
        else:
            is_veg_preferred = None

        # ── Order frequency ────────────────────────────────────────────
        freq_data = self.get_ordering_frequency(user_id, days)

        # ── Upsert snapshot ────────────────────────────────────────────
        snapshot = (
            self.db.query(UserPreferenceSnapshot)
            .filter(UserPreferenceSnapshot.user_id == user_id)
            .first()
        )

        if snapshot is None:
            snapshot = UserPreferenceSnapshot(user_id=user_id)

        snapshot.favourite_vendors = favourite_vendors
        snapshot.favourite_menu_items = favourite_items
        snapshot.favourite_categories = favourite_categories
        snapshot.preferred_timings = {
            "hour_distribution": timing_data["hour_distribution"],
            "preferred_hour": timing_data["preferred_hour"],
        }
        snapshot.preferred_vendor_types = preferred_vendor_types
        snapshot.avg_order_frequency_days = freq_data["avg_frequency_days"]
        snapshot.total_orders = total_orders
        snapshot.is_veg_preferred = is_veg_preferred
        snapshot.computed_at = utcnow_naive()

        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def get_preference_snapshot(self, user_id: int) -> Optional[UserPreferenceSnapshot]:
        """Get the latest preference snapshot, computing if stale or absent."""
        snapshot = (
            self.db.query(UserPreferenceSnapshot)
            .filter(UserPreferenceSnapshot.user_id == user_id)
            .first()
        )

        # Compute if missing or older than 1 hour
        if snapshot is None:
            return self.compute_preference_snapshot(user_id)

        age_hours = (utcnow_naive() - snapshot.computed_at).total_seconds() / 3600
        if age_hours > 1:
            return self.compute_preference_snapshot(user_id)

        return snapshot
