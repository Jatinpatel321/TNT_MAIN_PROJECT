from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem
from app.modules.users.model import User


class PreferenceEngine:
    """AI-powered user preference learning engine"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_stored_preferences(self, user_id: int) -> Dict[str, Any]:
        """Return the structured preferences JSON stored on the User row.

        Falls back to an empty dict when the user cannot be found or the
        column is NULL so all callers can rely on `.get()` safely.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None or not isinstance(user.preferences, dict):
            return {}
        return user.preferences

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_personalization(self, user_id: int) -> Dict[str, Any]:
        """Get personalized recommendations for user.

        Combines two data sources:
        1. **Behavioural signals** — order history (last 30 days)
        2. **Stated preferences** — the structured ``User.preferences``
           JSON saved via ``PUT /users/me/preferences``

        Stated preferences override or augment behavioural signals where
        applicable, e.g. the stored ``preferred_pickup_hour`` takes
        priority over the hour inferred from order history.
        """
        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Load stated preferences (may be empty dict for new users)
        stored_prefs = self._load_stored_preferences(user_id)

        # Analyse behavioural signals
        frequent_items = self._get_frequent_items(user_id, thirty_days_ago)
        preferred_vendors = self._get_preferred_vendors(user_id, thirty_days_ago)
        preferred_times = self._get_preferred_times(user_id, thirty_days_ago)

        # Generate recommendations, injecting stored preferences
        recommended_items = self._generate_item_recommendations(
            user_id, frequent_items, stored_prefs
        )
        smart_suggestions = self._generate_smart_suggestions(
            user_id, preferred_vendors, preferred_times, stored_prefs
        )

        return {
            "recommended_for_you": recommended_items,
            "smart_suggestions": smart_suggestions,
            # Surface the active preferences so clients know what shaped results
            "active_preferences": {
                "dietary_restrictions": stored_prefs.get("dietary_restrictions", []),
                "cuisine_preferences": stored_prefs.get("cuisine_preferences", []),
                "spice_level": stored_prefs.get("spice_level"),
                "preferred_pickup_hour": stored_prefs.get("preferred_pickup_hour"),
            },
        }

    def _get_frequent_items(self, user_id: int, since: datetime) -> List[Dict[str, Any]]:
        """Get user's most frequently ordered items"""

        frequent_items_query = self.db.query(
            OrderItem.menu_item_id,
            func.count(OrderItem.id).label('order_count'),
            func.avg(OrderItem.quantity).label('avg_quantity')
        ).join(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= since
        ).group_by(OrderItem.menu_item_id)\
         .order_by(func.count(OrderItem.id).desc())\
         .limit(10).all()

        frequent_items = []
        for row in frequent_items_query:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == row.menu_item_id).first()
            if menu_item:
                frequent_items.append({
                    "menu_item_id": row.menu_item_id,
                    "name": menu_item.name,
                    "order_count": row.order_count,
                    "avg_quantity": float(row.avg_quantity)
                })

        return frequent_items

    def _get_preferred_vendors(self, user_id: int, since: datetime) -> List[Dict[str, Any]]:
        """Get user's preferred vendors"""

        preferred_vendors_query = self.db.query(
            Order.vendor_id,
            func.count(Order.id).label('order_count')
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since
        ).group_by(Order.vendor_id)\
         .order_by(func.count(Order.id).desc())\
         .limit(5).all()

        preferred_vendors = []
        for row in preferred_vendors_query:
            preferred_vendors.append({
                "vendor_id": row.vendor_id,
                "order_count": row.order_count
            })

        return preferred_vendors

    def _get_preferred_times(self, user_id: int, since: datetime) -> Dict[str, Any]:
        """Get user's preferred ordering times"""

        preferred_time_query = self.db.query(
            func.extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('count')
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since
        ).group_by(func.extract('hour', Order.created_at))\
         .order_by(func.count(Order.id).desc())\
         .first()

        if preferred_time_query:
            return {
                "preferred_hour": int(preferred_time_query.hour),
                "order_count": preferred_time_query.count
            }

        return {"preferred_hour": 12, "order_count": 0}  # Default to noon

    def _generate_item_recommendations(
        self,
        user_id: int,
        frequent_items: List[Dict[str, Any]],
        stored_prefs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate item recommendations based on user history and stored preferences.

        When ``stored_prefs`` contains ``dietary_restrictions`` or
        ``cuisine_preferences``, those values are surfaced as a contextual
        note on each recommendation so the client can display the reason.
        """
        if stored_prefs is None:
            stored_prefs = {}

        dietary = stored_prefs.get("dietary_restrictions") or []
        cuisines = stored_prefs.get("cuisine_preferences") or []
        spice_level: Optional[int] = stored_prefs.get("spice_level")

        def _build_reason(base_reason: str) -> str:
            """Append preference context to a recommendation reason string."""
            parts = [base_reason]
            if dietary:
                parts.append(f"Matches dietary filter: {', '.join(dietary)}")
            if cuisines:
                parts.append(f"Based on your cuisine preferences: {', '.join(cuisines)}")
            if spice_level is not None:
                parts.append(f"Spice level preference: {spice_level}/5")
            return " · ".join(parts)

        recommendations = []

        # Recommend variations of frequently ordered items
        for item in frequent_items[:3]:  # Top 3 items
            # Find similar items from same vendor
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == item["menu_item_id"]).first()
            if menu_item:
                similar_items = self.db.query(MenuItem).filter(
                    MenuItem.vendor_id == menu_item.vendor_id,
                    MenuItem.id != item["menu_item_id"],
                    MenuItem.is_available == True
                ).limit(2).all()

                for similar_item in similar_items:
                    recommendations.append({
                        "item_id": similar_item.id,
                        "name": similar_item.name,
                        "reason": _build_reason(f"Similar to your favorite {menu_item.name}"),
                        "confidence": 0.8,
                    })

        # If no similar items, recommend popular items
        if not recommendations:
            popular_items = self.db.query(
                MenuItem.id,
                MenuItem.name,
                func.count(OrderItem.id).label('popularity')
            ).join(OrderItem).group_by(MenuItem.id, MenuItem.name)\
             .order_by(func.count(OrderItem.id).desc())\
             .limit(3).all()

            for item in popular_items:
                recommendations.append({
                    "item_id": item.id,
                    "name": item.name,
                    "reason": _build_reason("Popular choice among users"),
                    "confidence": 0.6,
                })

        return recommendations[:5]  # Limit to 5 recommendations

    def _generate_smart_suggestions(
        self,
        user_id: int,
        preferred_vendors: List[Dict[str, Any]],
        preferred_times: Dict[str, Any],
        stored_prefs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generate smart suggestions from behavioural patterns and stated preferences.

        Priority order for timing signal:
        1. ``stored_prefs["preferred_pickup_hour"]`` — explicitly chosen by user.
        2. ``preferred_times["preferred_hour"]`` — inferred from order history.
        3. 12 (noon) — default fallback.
        """
        if stored_prefs is None:
            stored_prefs = {}

        suggestions = []

        # ── Timing suggestion ────────────────────────────────────────────
        current_hour = utcnow_naive().hour

        # Stated preference takes priority over behavioural inference
        stored_hour: Optional[int] = stored_prefs.get("preferred_pickup_hour")
        preferred_hour: int = (
            stored_hour
            if stored_hour is not None
            else preferred_times.get("preferred_hour", 12)
        )

        if abs(current_hour - preferred_hour) <= 2:
            source = "your saved preference" if stored_hour is not None else "your order history"
            suggestions.append({
                "type": "timing",
                "title": "Perfect Timing!",
                "message": (
                    f"This is your preferred pickup window (based on {source}). "
                    "Great time to place an order."
                ),
                "priority": "high",
            })

        # ── Vendor loyalty ────────────────────────────────────────────────
        if preferred_vendors:
            top_vendor = preferred_vendors[0]
            suggestions.append({
                "type": "loyalty",
                "title": "Your Favourite Vendor",
                "message": (
                    f"You've ordered {top_vendor['order_count']} times from "
                    f"vendor {top_vendor['vendor_id']}."
                ),
                "priority": "medium",
            })

        # ── Reorder reminder (if no recent orders) ────────────────────────
        seven_days_ago = utcnow_naive() - timedelta(days=7)
        recent_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= seven_days_ago
        ).count()

        if recent_orders == 0:
            suggestions.append({
                "type": "reorder",
                "title": "Time for a Treat?",
                "message": "It's been a while since your last order. Check out our recommendations!",
                "priority": "low",
            })

        # ── Cuisine preference nudge ──────────────────────────────────────
        cuisines: List[str] = stored_prefs.get("cuisine_preferences") or []
        if cuisines:
            cuisine_display = ", ".join(c.replace("_", " ").title() for c in cuisines[:3])
            suggestions.append({
                "type": "cuisine_preference",
                "title": "Curated for You",
                "message": (
                    f"We know you love {cuisine_display}. "
                    "Look for these cuisines in your vendor and menu listings."
                ),
                "priority": "medium",
            })

        # ── Dietary restriction reminder ──────────────────────────────────
        dietary: List[str] = stored_prefs.get("dietary_restrictions") or []
        if dietary:
            dietary_display = ", ".join(d.replace("_", " ").title() for d in dietary)
            suggestions.append({
                "type": "dietary_reminder",
                "title": "Dietary Preferences Active",
                "message": (
                    f"Your dietary filters ({dietary_display}) are applied to recommendations."
                ),
                "priority": "low",
            })

        return suggestions
