from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem
from app.modules.slots.model import Slot


class ReorderEngine:
    """AI-powered smart reorder engine"""

    def __init__(self, db: Session):
        self.db = db

    def generate_reorder_suggestions(self, user_id: int) -> Dict[str, Any]:
        """Generate smart reorder suggestions for a user"""

        # Get user's order history
        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        recent_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= thirty_days_ago,
            Order.status == "completed"
        ).order_by(Order.created_at.desc()).limit(10).all()

        if not recent_orders:
            return self._empty_suggestions_response()

        # Analyze frequent items
        frequent_items = self._analyze_frequent_items(user_id, thirty_days_ago)

        # Analyze preferred slots
        preferred_slot = self._analyze_preferred_slots(user_id, thirty_days_ago)

        # Generate suggestions
        suggestions = []
        for item_data in frequent_items[:3]:  # Top 3 items
            suggestion = {
                "item_id": item_data["menu_item_id"],
                "quantity": item_data["avg_quantity"],
                "slot_id": preferred_slot,
                "print_settings": self._get_print_settings_for_item(item_data["menu_item_id"])
            }
            suggestions.append(suggestion)

        # Determine best time to reorder
        best_time = self._calculate_best_reorder_time(user_id)

        return {
            "suggestions": suggestions,
            "best_time_to_reorder": best_time
        }

    def _analyze_frequent_items(self, user_id: int, since: datetime) -> List[Dict[str, Any]]:
        """Analyze user's most frequently ordered items"""

        frequent_items_query = self.db.query(
            OrderItem.menu_item_id,
            func.avg(OrderItem.quantity).label('avg_quantity'),
            func.count(OrderItem.id).label('order_count')
        ).join(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= since,
            Order.status == "completed"
        ).group_by(OrderItem.menu_item_id)\
         .order_by(func.count(OrderItem.id).desc())\
         .limit(5).all()

        frequent_items = []
        for row in frequent_items_query:
            frequent_items.append({
                "menu_item_id": row.menu_item_id,
                "avg_quantity": int(row.avg_quantity),
                "order_count": row.order_count
            })

        return frequent_items

    def _analyze_preferred_slots(self, user_id: int, since: datetime) -> int:
        """Analyze user's preferred pickup slots"""

        preferred_slot_query = self.db.query(
            Order.slot_id,
            func.count(Order.id).label('slot_count')
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since,
            Order.status == "completed"
        ).group_by(Order.slot_id)\
         .order_by(func.count(Order.id).desc())\
         .first()

        if preferred_slot_query:
            return preferred_slot_query.slot_id

        # Default to first available slot
        default_slot = self.db.query(Slot).first()
        return default_slot.id if default_slot else 1

    def _get_print_settings_for_item(self, menu_item_id: int) -> Dict[str, Any]:
        """Get print settings for stationery items"""

        menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()

        if menu_item and "stationery" in menu_item.name.lower():
            text = f"{menu_item.name} {menu_item.description or ''}".lower()

            paper_type = "A4"
            if "a3" in text:
                paper_type = "A3"
            elif "a5" in text:
                paper_type = "A5"

            color = "color" if "color" in text else "black_and_white"
            sides = "double" if "double" in text or "duplex" in text else "single"

            return {
                "paper_type": paper_type,
                "color": color,
                "sides": sides,
                "copies": 1
            }

        return {}

    def _calculate_best_reorder_time(self, user_id: int) -> str:
        """Calculate best time for user to reorder"""

        # Analyze user's ordering patterns
        orders_by_hour = self.db.query(
            func.extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('count')
        ).filter(
            Order.user_id == user_id
        ).group_by(func.extract('hour', Order.created_at))\
         .order_by(func.count(Order.id).desc())\
         .first()

        if orders_by_hour:
            hour = int(orders_by_hour.hour)
            return f"{hour:02d}:00"

        return "12:00"  # Default noon

    def _empty_suggestions_response(self) -> Dict[str, Any]:
        """Return empty suggestions when no history"""

        return {
            "suggestions": [],
            "best_time_to_reorder": "12:00"
        }
