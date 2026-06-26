from datetime import datetime
from typing import Any, Dict, List

from app.core.time_utils import utcnow_naive

from .service import AIIntelligenceService


class AISignals:
    """AI Signals and proactive intelligence"""

    def __init__(self, db):
        self.db = db
        self.ai_service = AIIntelligenceService(db)

    def generate_system_signals(self) -> List[Dict[str, Any]]:
        """Generate system-wide AI signals"""

        signals = []

        # Demand signals
        demand_signals = self._generate_demand_signals()
        signals.extend(demand_signals)

        # Capacity signals
        capacity_signals = self._generate_capacity_signals()
        signals.extend(capacity_signals)

        # Performance signals
        performance_signals = self._generate_performance_signals()
        signals.extend(performance_signals)

        return signals

    def generate_user_signals(self, user_id: int) -> List[Dict[str, Any]]:
        """Generate user-specific AI signals"""

        signals = []

        # Personalization signals
        personalization_signals = self._generate_personalization_signals(user_id)
        signals.extend(personalization_signals)

        # Reorder signals
        reorder_signals = self._generate_reorder_signals(user_id)
        signals.extend(reorder_signals)

        # Timing signals
        timing_signals = self._generate_timing_signals(user_id)
        signals.extend(timing_signals)

        return signals

    def _generate_demand_signals(self) -> List[Dict[str, Any]]:
        """Generate demand-related signals"""

        signals = []

        # Check for unusual demand patterns
        current_hour = utcnow_naive().hour

        # High demand hours
        if current_hour in [12, 13, 19, 20]:
            signals.append({
                "type": "demand_spike",
                "severity": "medium",
                "title": "Peak Demand Hour",
                "message": f"High demand expected at {current_hour}:00",
                "action_required": "Consider increasing capacity",
                "target": "vendor"
            })

        return signals

    def _generate_capacity_signals(self) -> List[Dict[str, Any]]:
        """Generate capacity-related signals"""

        signals = []

        # Check slot utilization
        from app.modules.slots.model import Slot

        high_utilization_slots = self.db.query(Slot).filter(
            Slot.current_orders >= Slot.max_orders * 0.9,
            Slot.max_orders > 0
        ).all()

        for slot in high_utilization_slots:
            signals.append({
                "type": "capacity_warning",
                "severity": "high",
                "title": "Slot Nearly Full",
                "message": f"Slot {slot.id} is {int((slot.current_orders/slot.max_orders)*100)}% full",
                "action_required": "Consider adding more slots or reducing duration",
                "target": "vendor",
                "slot_id": slot.id
            })

        return signals

    def _generate_performance_signals(self) -> List[Dict[str, Any]]:
        """Generate performance-related signals"""

        signals = []

        # Check for vendors with declining performance
        # This would analyze trends over time

        signals.append({
            "type": "performance_trend",
            "severity": "info",
            "title": "Performance Monitoring",
            "message": "System performance is being monitored",
            "action_required": "No action needed",
            "target": "system"
        })

        return signals

    def _generate_personalization_signals(self, user_id: int) -> List[Dict[str, Any]]:
        """Generate personalization signals for user"""

        signals = []

        # Check if user hasn't ordered recently
        from datetime import timedelta

        from app.modules.orders.model import Order

        seven_days_ago = utcnow_naive() - timedelta(days=7)

        recent_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= seven_days_ago
        ).count()

        if recent_orders == 0:
            signals.append({
                "type": "reengagement",
                "severity": "low",
                "title": "We Miss You!",
                "message": "It's been a week since your last order",
                "action_required": "Consider placing a new order",
                "target": "user",
                "user_id": user_id
            })

        return signals

    def _generate_reorder_signals(self, user_id: int) -> List[Dict[str, Any]]:
        """Generate reorder-related signals"""

        signals = []

        # Get reorder suggestions
        reorder_suggestions = self.ai_service.get_reorder_suggestions(user_id)

        if reorder_suggestions.suggestions:
            signals.append({
                "type": "reorder_reminder",
                "severity": "low",
                "title": "Reorder Suggestion",
                "message": f"Consider reordering your favorite items",
                "action_required": "Check reorder suggestions",
                "target": "user",
                "user_id": user_id,
                "suggestion_count": len(reorder_suggestions.suggestions)
            })

        return signals

    def _generate_timing_signals(self, user_id: int) -> List[Dict[str, Any]]:
        """Generate timing-related signals"""

        signals = []

        current_hour = utcnow_naive().hour

        # Suggest optimal ordering times
        if current_hour in [11, 18]:  # Pre-lunch, pre-dinner
            signals.append({
                "type": "optimal_timing",
                "severity": "info",
                "title": "Good Time to Order",
                "message": f"Now is a great time to place your order for {current_hour + 1}:00 pickup",
                "action_required": "Consider ordering now",
                "target": "user",
                "user_id": user_id
            })

        return signals
