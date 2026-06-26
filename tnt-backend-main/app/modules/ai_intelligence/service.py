from datetime import time, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot

from .learning.preference_engine import PreferenceEngine
from .planners.demand_planner import DemandPlanner
from .planners.eta_engine import ETAEngine
from .planners.reorder_engine import ReorderEngine
from .planners.slot_planner import SlotPlanner
from .planners.vendor_ranker import VendorRanker
from .schemas import *
from .utils.scoring import SlotScoring, VendorScoring


class AIIntelligenceService:
    """Main AI Intelligence Service coordinating all AI features"""

    def __init__(self, db: Session):
        self.db = db
        self.demand_planner = DemandPlanner(db)
        self.slot_planner = SlotPlanner(db)
        self.vendor_ranker = VendorRanker(db)
        self.eta_engine = ETAEngine(db)
        self.reorder_engine = ReorderEngine(db)
        self.preference_engine = PreferenceEngine(db)

    def get_demand_planning(self, vendor_id: int) -> DemandPlanningResponse:
        """Get demand planning insights for vendor"""
        return self.demand_planner.get_demand_planning(vendor_id)

    def get_capacity_recommendation(self, vendor_id: int) -> CapacityRecommendationResponse:
        """Get AI capacity recommendation for vendor"""
        result = self.slot_planner.get_capacity_recommendation(vendor_id)
        return CapacityRecommendationResponse(**result)

    def get_slot_recommendations(self, user_id: int = None) -> SlotRecommendationsResponse:
        """Get AI-powered slot recommendations"""
        # Get all available slots
        from app.modules.slots.model import Slot
        slots = self.db.query(Slot).filter(Slot.status != "full").all()

        recommendations = []
        best_score = 0
        best_slot_id = None

        for slot in slots:
            # Calculate vendor speed score
            vendor_speed_score = VendorScoring.calculate_vendor_speed_score(slot.vendor_id, self.db)

            # Calculate historical completion rate
            completion_rate = VendorScoring.calculate_historical_completion_rate(slot.vendor_id, self.db)

            # Calculate slot score
            score = SlotScoring.calculate_slot_score(slot, vendor_speed_score, completion_rate)

            reasoning = self._generate_slot_reasoning(slot, score, vendor_speed_score, completion_rate)

            recommendations.append({
                "slot_id": slot.id,
                "score": score,
                "reasoning": reasoning,
                "estimated_eta_minutes": self.eta_engine.predict_eta(slot.id, slot.vendor_id)["predicted_eta_minutes"]
            })

            if score > best_score:
                best_score = score
                best_slot_id = slot.id

        # Sort by score descending
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        return SlotRecommendationsResponse(
            recommendations=recommendations,
            best_slot_id=best_slot_id
        )

    def get_predictive_eta(self, slot_id: int, vendor_id: int) -> PredictiveETAResponse:
        """Get predictive ETA for slot"""
        result = self.eta_engine.predict_eta(slot_id, vendor_id)
        return PredictiveETAResponse(**result)

    def get_vendor_ranking(self) -> VendorRankingResponse:
        """Get AI-powered vendor rankings"""
        rankings = self.vendor_ranker.get_vendor_rankings()
        return VendorRankingResponse(rankings=rankings)

    def get_personalization(self, user_id: int) -> PersonalizationResponse:
        """Get personalized recommendations"""
        result = self.preference_engine.get_personalization(user_id)
        return PersonalizationResponse(**result)

    def get_reorder_suggestions(self, user_id: int) -> ReorderSuggestionsResponse:
        """Get smart reorder suggestions"""
        result = self.reorder_engine.generate_reorder_suggestions(user_id)
        return ReorderSuggestionsResponse(**result)

    def get_proactive_alerts(self, user_id: int = None) -> ProactiveAlertsResponse:
        """Generate proactive AI alerts"""
        alerts = []

        # Rush hour alerts
        rush_alerts = self._generate_rush_hour_alerts()
        alerts.extend(rush_alerts)

        # Delay risk alerts
        if user_id:
            delay_alerts = self._generate_delay_risk_alerts(user_id)
            alerts.extend(delay_alerts)

        # Vendor overload alerts
        overload_alerts = self._generate_vendor_overload_alerts()
        alerts.extend(overload_alerts)

        return ProactiveAlertsResponse(alerts=alerts)

    def get_group_coordination(self, user_ids: List[int]) -> GroupCoordinationResponse:
        """Get group coordination intelligence"""
        if not user_ids:
            return GroupCoordinationResponse(
                overlapping_windows=[],
                suggested_unified_slot=None,
                coordination_score=0.0,
            )

        thirty_days_ago = utcnow_naive().replace(hour=0, minute=0, second=0, microsecond=0)

        user_hour_maps: Dict[int, Dict[int, int]] = {}
        for user_id in user_ids:
            hourly_distribution = self.db.query(
                func.extract("hour", Order.created_at).label("hour"),
                func.count(Order.id).label("order_count"),
            ).filter(
                Order.user_id == user_id,
                Order.created_at >= thirty_days_ago,
            ).group_by(func.extract("hour", Order.created_at)).all()

            user_hour_maps[user_id] = {
                int(row.hour): int(row.order_count)
                for row in hourly_distribution
            }

        overlapping_windows: List[Dict[str, Any]] = []
        for hour in range(24):
            participants = [
                user_id for user_id, hour_map in user_hour_maps.items()
                if hour_map.get(hour, 0) > 0
            ]
            if len(participants) >= 2:
                confidence = len(participants) / len(user_ids)
                overlapping_windows.append(
                    {
                        "hour": hour,
                        "participants": participants,
                        "confidence": round(confidence, 2),
                    }
                )

        overlapping_windows.sort(
            key=lambda row: (row["confidence"], len(row["participants"])),
            reverse=True,
        )

        suggested_slot_id = None
        if overlapping_windows:
            candidate_hours = [window["hour"] for window in overlapping_windows[:3]]
            candidate_slots = self.db.query(Slot).filter(
                Slot.status != "full",
            ).all()

            scored_slots: list[tuple[int, float]] = []
            for slot in candidate_slots:
                slot_hour = slot.start_time.hour
                if slot_hour not in candidate_hours:
                    continue

                remaining_capacity = max(0, slot.max_orders - slot.current_orders)
                normalized_capacity = remaining_capacity / max(slot.max_orders, 1)
                hour_confidence = next(
                    (window["confidence"] for window in overlapping_windows if window["hour"] == slot_hour),
                    0.0,
                )
                scored_slots.append((slot.id, (0.7 * hour_confidence) + (0.3 * normalized_capacity)))

            if scored_slots:
                scored_slots.sort(key=lambda row: row[1], reverse=True)
                suggested_slot_id = scored_slots[0][0]

        coordination_score = 0.0
        if overlapping_windows:
            top_confidence = overlapping_windows[0]["confidence"]
            coordination_score = round(min(1.0, top_confidence * 1.1), 2)

        return GroupCoordinationResponse(
            overlapping_windows=overlapping_windows,
            suggested_unified_slot=suggested_slot_id,
            coordination_score=coordination_score,
        )

    def get_user_signals(self, user_id: int) -> List[Dict[str, Any]]:
        signals = []
        signals.extend(self.get_rush_hour_signals(user_id))
        signals.extend(self.get_slot_suggestion_signals(user_id))
        signals.extend(self.get_reorder_prompt_signals(user_id))
        return signals

    def get_rush_hour_signals(self, user_id: int) -> List[Dict[str, Any]]:
        signals = []
        now = utcnow_naive()

        rush_periods = [
            (time(8, 0), time(10, 0)),
            (time(12, 0), time(14, 0)),
            (time(18, 0), time(20, 0)),
        ]

        current_time = now.time()
        is_rush_hour = any(start <= current_time <= end for start, end in rush_periods)

        if is_rush_hour:
            upcoming_orders = self.db.query(Order).join(
                Slot, Order.slot_id == Slot.id
            ).filter(
                Order.user_id == user_id,
                Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED]),
                Slot.start_time >= now,
                Slot.start_time <= now + timedelta(hours=2),
            ).all()

            if upcoming_orders:
                signals.append(
                    {
                        "type": "rush_hour_warning",
                        "title": "Rush Hour Alert",
                        "message": "You're ordering during peak hours. Consider adjusting your pickup time to avoid delays.",
                        "priority": "medium",
                        "action": "suggest_alternative_slots",
                        "data": {"upcoming_orders": len(upcoming_orders)},
                    }
                )

        return signals

    def get_slot_suggestion_signals(self, user_id: int) -> List[Dict[str, Any]]:
        signals = []
        now = utcnow_naive()

        user_orders = self.db.query(
            Slot.start_time,
        ).join(
            Order, Order.slot_id == Slot.id,
        ).filter(
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED,
        ).order_by(Order.created_at.desc()).limit(10).all()

        if not user_orders:
            return signals

        preferred_hours = {}
        for row in user_orders:
            hour = row.start_time.hour
            preferred_hours[hour] = preferred_hours.get(hour, 0) + 1

        if preferred_hours:
            best_hour = max(preferred_hours, key=preferred_hours.get)
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            today_slots = self.db.query(Slot).filter(
                Slot.start_time >= now,
                Slot.start_time < day_end,
            ).all()
            today_slots = [slot for slot in today_slots if slot.start_time.hour == best_hour]

            low_congestion_slots = [
                slot for slot in today_slots if getattr(slot, "congestion_level", 0) < 0.7
            ]

            if low_congestion_slots:
                signals.append(
                    {
                        "type": "slot_suggestion",
                        "title": "Smart Slot Suggestion",
                        "message": f"Based on your preferences, {low_congestion_slots[0].start_time.strftime('%I:%M %p')} has low congestion.",
                        "priority": "low",
                        "action": "suggest_slot",
                        "data": {"suggested_slot_id": low_congestion_slots[0].id},
                    }
                )

        return signals

    def get_reorder_prompt_signals(self, user_id: int) -> List[Dict[str, Any]]:
        signals = []
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        recent_orders = self.db.query(Order.id).filter(
            Order.user_id == user_id,
            Order.status == OrderStatus.COMPLETED,
            Order.created_at >= thirty_days_ago,
        ).all()

        if not recent_orders:
            return signals

        order_ids = [row.id for row in recent_orders]

        from app.modules.orders.model import OrderItem

        recent_items = self.db.query(
            OrderItem.menu_item_id,
            OrderItem.quantity,
        ).filter(
            OrderItem.order_id.in_(order_ids)
        ).all()

        item_counts = {}
        for item in recent_items:
            item_id = item.menu_item_id
            item_counts[item_id] = item_counts.get(item_id, 0) + item.quantity

        if item_counts:
            most_ordered_item_id = max(item_counts, key=item_counts.get)
            order_count = item_counts[most_ordered_item_id]

            if order_count >= 3:
                menu_item = self.db.query(MenuItem).filter(MenuItem.id == most_ordered_item_id).first()
                if menu_item:
                    signals.append(
                        {
                            "type": "reorder_prompt",
                            "title": "Reorder Favorite",
                            "message": f"You've ordered {menu_item.name} {order_count} times. Want to order again?",
                            "priority": "low",
                            "action": "suggest_reorder",
                            "data": {"item_id": most_ordered_item_id, "item_name": menu_item.name},
                        }
                    )

        return signals

    def _generate_slot_reasoning(self, slot: Slot, score: float, speed_score: float, completion_rate: float) -> str:
        """Generate human-readable reasoning for slot score"""

        reasons = []

        if score >= 80:
            reasons.append("Excellent choice")
        elif score >= 60:
            reasons.append("Good option")
        else:
            reasons.append("Consider alternative")

        if speed_score > 70:
            reasons.append("fast vendor")
        elif speed_score < 40:
            reasons.append("slower vendor")

        if completion_rate > 0.9:
            reasons.append("highly reliable")
        elif completion_rate < 0.7:
            reasons.append("variable reliability")

        capacity_remaining = max(0, slot.max_orders - slot.current_orders)
        if capacity_remaining < 3:
            reasons.append("limited spots")

        return ", ".join(reasons)

    def _generate_rush_hour_alerts(self) -> List[AIAlert]:
        """Generate rush hour alerts"""
        alerts = []

        current_hour = utcnow_naive().hour

        # Peak lunch hours
        if 12 <= current_hour <= 14:
            alerts.append(AIAlert(
                type="rush_hour",
                severity="medium",
                explanation="High demand expected during lunch hours",
                suggested_action="Consider ordering earlier or choosing a different time slot"
            ))

        # Peak dinner hours
        elif 19 <= current_hour <= 21:
            alerts.append(AIAlert(
                type="rush_hour",
                severity="medium",
                explanation="High demand expected during dinner hours",
                suggested_action="Consider ordering earlier or choosing a different time slot"
            ))

        return alerts

    def _generate_delay_risk_alerts(self, user_id: int) -> List[AIAlert]:
        """Generate delay risk alerts for user"""
        alerts = []

        # Check user's upcoming orders
        from datetime import datetime, timedelta

        from app.modules.orders.model import Order

        upcoming_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.status.in_(["confirmed", "preparing"]),
            Order.created_at >= utcnow_naive() - timedelta(hours=2)
        ).all()

        for order in upcoming_orders:
            eta_prediction = self.get_predictive_eta(order.slot_id, order.vendor_id)

            if eta_prediction.delay_risk_level == "HIGH":
                alerts.append(AIAlert(
                    type="delay_risk",
                    severity="high",
                    explanation=f"High delay risk detected for order #{order.id}",
                    suggested_action="Consider contacting vendor or reordering"
                ))

        return alerts

    def _generate_vendor_overload_alerts(self) -> List[AIAlert]:
        """Generate vendor overload alerts"""
        alerts = []

        # Check for overloaded vendors
        from app.modules.slots.model import Slot

        overloaded_slots = self.db.query(Slot).filter(
            Slot.current_orders >= Slot.max_orders * 0.9,
            Slot.max_orders > 0
        ).all()

        for slot in overloaded_slots:
            alerts.append(AIAlert(
                type="vendor_overload",
                severity="medium",
                explanation=f"Vendor {slot.vendor_id} is experiencing high load",
                suggested_action="Consider alternative vendors or later time slots"
            ))

        return alerts

    def get_ai_recommendations(self, user_id: int) -> Dict[str, Any]:
        """
        Generate personalized recommendations based on order frequency,
        vendor load, time of day, and popularity.
        """
        from app.modules.orders.model import Order, OrderItem
        from app.modules.menu.model import MenuItem
        from app.modules.users.model import User as Vendor
        from app.modules.slots.model import Slot
        from sqlalchemy import func
        from datetime import datetime
        
        now = datetime.utcnow()
        
        # 1. Frequent orders
        frequent_orders_query = self.db.query(
            MenuItem.id, MenuItem.name, func.count(Order.id).label("order_count")
        ).join(OrderItem, OrderItem.menu_item_id == MenuItem.id)\
         .join(Order, Order.id == OrderItem.order_id)\
         .filter(Order.user_id == user_id)\
         .group_by(MenuItem.id, MenuItem.name)\
         .order_by(func.count(Order.id).desc())\
         .limit(5).all()
        
        frequent_orders = [{"item_id": r.id, "name": r.name, "frequency": r.order_count} for r in frequent_orders_query]
        
        # 2. Vendors Ranked & Favorite vendors (Frequency + Load)
        vendors_query = self.db.query(
            Vendor.id, Vendor.name, func.count(Order.id).label("order_count")
        ).join(Order, Order.vendor_id == Vendor.id)\
         .filter(Order.user_id == user_id)\
         .group_by(Vendor.id, Vendor.name)\
         .order_by(func.count(Order.id).desc())\
         .limit(5).all()
        
        vendors_ranked = [{"vendor_id": r.id, "name": r.name, "score": r.order_count * 10} for r in vendors_query]
        
        # 3. Recommended & Popular items (Campus wide + personalized)
        popular_items_query = self.db.query(
            MenuItem.id, MenuItem.name, func.count(Order.id).label("popularity")
        ).join(OrderItem, OrderItem.menu_item_id == MenuItem.id)\
         .join(Order, Order.id == OrderItem.order_id)\
         .group_by(MenuItem.id, MenuItem.name)\
         .order_by(func.count(Order.id).desc())\
         .limit(5).all()
         
        recommended_items = [{"item_id": r.id, "name": r.name, "reason": "Trending Campus Item", "score": r.popularity} for r in popular_items_query]
        
        # 4. Best Slots (Based on vendor load and time of day)
        best_slots_query = self.db.query(
            Slot.id, Slot.start_time, Slot.end_time, Slot.vendor_id, Slot.current_orders, Slot.max_orders
        ).filter(Slot.current_orders < Slot.max_orders)\
         .order_by(Slot.current_orders.asc())\
         .limit(3).all()
         
        best_slots = [{"slot_id": r.id, "time": f"{r.start_time}-{r.end_time}", "vendor_id": r.vendor_id, "load_status": "low"} for r in best_slots_query]
        
        return {
            "recommended_items": recommended_items,
            "frequent_orders": frequent_orders,
            "best_slots": best_slots,
            "vendors_ranked": vendors_ranked
        }
