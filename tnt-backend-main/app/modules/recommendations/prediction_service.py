"""
Predictive Behaviour Learning Service
======================================

Machine learning service that learns user patterns and predicts:
- Next likely order
- Preferred ordering time
- Preferred vendor
- Preferred menu item

Uses PostgreSQL for all storage and pattern analysis.
Integrates with existing recommendation engine.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.users.model import User
from app.modules.recommendations.models import (
    UserBehaviour,
    UserPreferenceSnapshot,
    PredictionHistory,
)

logger = logging.getLogger("tnt.recommendations.predictions")


class PredictionService:
    """ML-powered prediction service for user behaviour learning."""

    def __init__(self, db: Session):
        self.db = db

    # ── Pattern Learning ──────────────────────────────────────────────────

    def learn_weekly_patterns(self, user_id: int, days: int = 90) -> dict[str, Any]:
        """Learn weekly ordering habits.

        Returns:
            - day_distribution: {0: count, 1: count, ...} (0=Monday)
            - preferred_days: [0, 2, 4] (days user orders most)
            - weekly_pattern: "consistent", "weekend_warrior", "weekday_lunch"
        """
        since = utcnow_naive() - timedelta(days=days)

        orders = (
            self.db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .all()
        )

        if not orders:
            return {
                "day_distribution": {},
                "preferred_days": [],
                "weekly_pattern": "no_data",
            }

        # Count orders by day of week
        day_counts = Counter()
        for order in orders:
            day_of_week = order.created_at.weekday()  # 0=Monday, 6=Sunday
            day_counts[day_of_week] += 1

        # Find preferred days (top 3)
        preferred_days = [day for day, _ in day_counts.most_common(3)]

        # Classify pattern
        weekday_count = sum(day_counts.get(d, 0) for d in range(5))
        weekend_count = sum(day_counts.get(d, 0) for d in [5, 6])

        if weekday_count > 0 and weekend_count > 0:
            if weekday_count > weekend_count * 2:
                pattern = "weekday_lunch"
            elif weekend_count > weekday_count * 2:
                pattern = "weekend_warrior"
            else:
                pattern = "consistent"
        elif weekday_count > 0:
            pattern = "weekday_lunch"
        elif weekend_count > 0:
            pattern = "weekend_warrior"
        else:
            pattern = "no_data"

        return {
            "day_distribution": dict(day_counts),
            "preferred_days": preferred_days,
            "weekly_pattern": pattern,
        }

    def learn_daily_patterns(self, user_id: int, days: int = 90) -> dict[str, Any]:
        """Learn daily ordering habits (time of day).

        Returns:
            - hour_distribution: {0: count, 1: count, ...}
            - preferred_hour: int (most common ordering hour)
            - daily_pattern: "morning", "lunch", "afternoon", "evening", "night_owl"
        """
        since = utcnow_naive() - timedelta(days=days)

        orders = (
            self.db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .all()
        )

        if not orders:
            return {
                "hour_distribution": {},
                "preferred_hour": 12,
                "daily_pattern": "no_data",
            }

        # Count orders by hour
        hour_counts = Counter()
        for order in orders:
            hour = order.created_at.hour
            hour_counts[hour] += 1

        # Find preferred hour
        preferred_hour = hour_counts.most_common(1)[0][0] if hour_counts else 12

        # Classify pattern
        morning = sum(hour_counts.get(h, 0) for h in range(6, 11))
        lunch = sum(hour_counts.get(h, 0) for h in range(11, 15))
        afternoon = sum(hour_counts.get(h, 0) for h in range(15, 18))
        evening = sum(hour_counts.get(h, 0) for h in range(18, 22))
        night = sum(hour_counts.get(h, 0) for h in range(22, 24)) + sum(
            hour_counts.get(h, 0) for h in range(0, 6)
        )

        max_period = max(morning, lunch, afternoon, evening, night)
        if max_period == morning:
            pattern = "morning"
        elif max_period == lunch:
            pattern = "lunch"
        elif max_period == afternoon:
            pattern = "afternoon"
        elif max_period == evening:
            pattern = "evening"
        else:
            pattern = "night_owl"

        return {
            "hour_distribution": dict(hour_counts),
            "preferred_hour": preferred_hour,
            "daily_pattern": pattern,
        }

    def learn_semester_patterns(self, user_id: int) -> dict[str, Any]:
        """Learn semester-based patterns (exam periods, holidays, etc.).

        Returns:
            - phase: "early", "mid", "late", "exam", "holiday"
            - order_frequency_change: float (percentage change)
            - preferred_items_this_phase: [item_names]
        """
        now = utcnow_naive()
        month = now.month

        # Simple semester detection (adjust based on actual academic calendar)
        # Assuming: Jan-May = Semester 1, Jun-Dec = Semester 2
        if month in [1, 2, 3, 4, 5]:
            semester = 1
        else:
            semester = 2

        # Detect phase within semester
        if month in [3, 4, 9, 10]:
            phase = "mid"  # Mid-semester
        elif month in [4, 11]:
            phase = "exam"  # Exam period
        elif month in [1, 6, 7, 12]:
            phase = "holiday"  # Holiday/break
        elif month in [2, 8]:
            phase = "early"  # Early semester
        else:
            phase = "late"  # Late semester

        # Get orders from this phase in previous semester
        prev_semester_month = 6 if semester == 1 else 1
        prev_phase_start = now.replace(month=prev_semester_month, day=1)
        prev_phase_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.user_id == user_id,
                Order.created_at >= prev_phase_start,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .scalar()
            or 0
        )

        # Get orders from current phase
        current_phase_start = now - timedelta(days=30)
        current_phase_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.user_id == user_id,
                Order.created_at >= current_phase_start,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .scalar()
            or 0
        )

        # Calculate frequency change
        if prev_phase_orders > 0:
            freq_change = ((current_phase_orders - prev_phase_orders) / prev_phase_orders) * 100
        else:
            freq_change = 0.0

        # Get preferred items this phase
        phase_items = (
            self.db.query(MenuItem.name, func.count(OrderItem.id).label("count"))
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= current_phase_start,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(MenuItem.name)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )

        preferred_items = [item.name for item in phase_items]

        return {
            "phase": phase,
            "semester": semester,
            "order_frequency_change": round(freq_change, 1),
            "preferred_items_this_phase": preferred_items,
        }

    def learn_favourite_vendors(self, user_id: int, days: int = 90) -> list[dict[str, Any]]:
        """Learn favourite vendors with confidence scores."""
        since = utcnow_naive() - timedelta(days=days)

        vendor_stats = (
            self.db.query(
                Order.vendor_id,
                User.name.label("vendor_name"),
                User.vendor_type,
                func.count(Order.id).label("order_count"),
                func.max(Order.created_at).label("last_order"),
            )
            .join(User, User.id == Order.vendor_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .group_by(Order.vendor_id, User.name, User.vendor_type)
            .order_by(desc("order_count"))
            .limit(10)
            .all()
        )

        total_orders = sum(v.order_count for v in vendor_stats) or 1

        favourites = []
        for v in vendor_stats:
            confidence = min(1.0, v.order_count / max(total_orders, 1))
            favourites.append({
                "vendor_id": v.vendor_id,
                "vendor_name": v.vendor_name,
                "vendor_type": v.vendor_type,
                "order_count": v.order_count,
                "confidence": round(confidence, 2),
                "last_order": v.last_order.isoformat() if v.last_order else None,
            })

        return favourites

    def learn_favourite_foods(self, user_id: int, days: int = 90) -> list[dict[str, Any]]:
        """Learn favourite food items with confidence scores."""
        since = utcnow_naive() - timedelta(days=days)

        food_items = (
            self.db.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.quantity).label("total_qty"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
                MenuItem.category.in_(["food", "indian", "chinese", "italian", "snacks", "beverages", "south indian"]),
            )
            .group_by(OrderItem.menu_item_id, MenuItem.name, MenuItem.category)
            .order_by(desc("order_count"))
            .limit(15)
            .all()
        )

        total_food_orders = sum(f.order_count for f in food_items) or 1

        favourites = []
        for f in food_items:
            confidence = min(1.0, (f.order_count * f.total_qty) / total_food_orders)
            favourites.append({
                "item_id": f.menu_item_id,
                "name": f.name,
                "category": f.category,
                "order_count": f.order_count,
                "total_quantity": int(f.total_qty or 0),
                "confidence": round(confidence, 2),
            })

        return favourites

    def learn_favourite_stationery(self, user_id: int, days: int = 90) -> list[dict[str, Any]]:
        """Learn favourite stationery services with confidence scores."""
        since = utcnow_naive() - timedelta(days=days)

        stationery_items = (
            self.db.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                MenuItem.category,
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.quantity).label("total_qty"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
                MenuItem.category.in_(["stationery", "print", "xerox", "binding", "lamination"]),
            )
            .group_by(OrderItem.menu_item_id, MenuItem.name, MenuItem.category)
            .order_by(desc("order_count"))
            .limit(10)
            .all()
        )

        total_stationery_orders = sum(s.order_count for s in stationery_items) or 1

        favourites = []
        for s in stationery_items:
            confidence = min(1.0, (s.order_count * s.total_qty) / total_stationery_orders)
            favourites.append({
                "item_id": s.menu_item_id,
                "name": s.name,
                "category": s.category,
                "order_count": s.order_count,
                "total_quantity": int(s.total_qty or 0),
                "confidence": round(confidence, 2),
            })

        return favourites

    # ── Prediction Generation ─────────────────────────────────────────────

    def predict_next_order(self, user_id: int) -> dict[str, Any]:
        """Predict user's next likely order.

        Uses:
        - Weekly patterns (day of week)
        - Daily patterns (time of day)
        - Semester patterns (current phase)
        - Favourite vendors and items
        - Order frequency

        Returns:
            - predicted_vendor_id
            - predicted_menu_item_id
            - predicted_hour
            - predicted_day_of_week
            - confidence_score
            - reasoning
        """
        # Learn patterns
        weekly = self.learn_weekly_patterns(user_id)
        daily = self.learn_daily_patterns(user_id)
        semester = self.learn_semester_patterns(user_id)
        fav_vendors = self.learn_favourite_vendors(user_id)
        fav_foods = self.learn_favourite_foods(user_id)
        fav_stationery = self.learn_favourite_stationery(user_id)

        # Predict next order day
        now = utcnow_naive()
        current_day = now.weekday()
        current_hour = now.hour

        # Find next preferred day
        preferred_days = weekly.get("preferred_days", [])
        if preferred_days:
            # Find next preferred day
            days_ahead = 1
            for day in preferred_days:
                if day > current_day:
                    days_ahead = day - current_day
                    break
            else:
                days_ahead = (7 - current_day) + preferred_days[0]
            predicted_day = (current_day + days_ahead) % 7
        else:
            predicted_day = current_day

        # Predict preferred hour
        predicted_hour = daily.get("preferred_hour", 12)

        # Predict vendor
        predicted_vendor_id = None
        if fav_vendors:
            # Weight by recency and frequency
            best_vendor = fav_vendors[0]
            predicted_vendor_id = best_vendor["vendor_id"]

        # Predict menu item
        predicted_item_id = None
        predicted_item_name = None

        # Determine if food or stationery based on time
        if 10 <= current_hour <= 16:
            # Afternoon: more likely stationery
            if fav_stationery:
                best_item = fav_stationery[0]
                predicted_item_id = best_item["item_id"]
                predicted_item_name = best_item["name"]
        else:
            # Morning/Evening: more likely food
            if fav_foods:
                best_item = fav_foods[0]
                predicted_item_id = best_item["item_id"]
                predicted_item_name = best_item["name"]

        # Calculate confidence
        confidence_factors = []

        if weekly.get("weekly_pattern") != "no_data":
            confidence_factors.append(0.2)

        if daily.get("daily_pattern") != "no_data":
            confidence_factors.append(0.2)

        if fav_vendors:
            confidence_factors.append(0.3)

        if predicted_item_id:
            confidence_factors.append(0.3)

        confidence_score = min(1.0, sum(confidence_factors))

        # Build reasoning
        reasoning_parts = []
        if weekly.get("weekly_pattern"):
            reasoning_parts.append(f"Weekly pattern: {weekly['weekly_pattern']}")
        if daily.get("daily_pattern"):
            reasoning_parts.append(f"Daily pattern: {daily['daily_pattern']}")
        if fav_vendors:
            reasoning_parts.append(f"Favourite vendor: {fav_vendors[0]['vendor_name']}")
        if predicted_item_name:
            reasoning_parts.append(f"Favourite item: {predicted_item_name}")

        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Insufficient data"

        return {
            "predicted_vendor_id": predicted_vendor_id,
            "predicted_menu_item_id": predicted_item_id,
            "predicted_menu_item_name": predicted_item_name,
            "predicted_hour": predicted_hour,
            "predicted_day_of_week": predicted_day,
            "confidence_score": round(confidence_score, 2),
            "reasoning": reasoning,
            "patterns": {
                "weekly": weekly,
                "daily": daily,
                "semester": semester,
            },
        }

    def predict_preferred_time(self, user_id: int) -> dict[str, Any]:
        """Predict user's preferred ordering time.

        Returns:
            - preferred_hour
            - preferred_day_of_week
            - confidence_score
            - next_recommended_order_time (ISO datetime)
        """
        daily = self.learn_daily_patterns(user_id)
        weekly = self.learn_weekly_patterns(user_id)

        preferred_hour = daily.get("preferred_hour", 12)
        preferred_days = weekly.get("preferred_days", [])

        # Calculate next recommended order time
        now = utcnow_naive()
        current_day = now.weekday()
        current_hour = now.hour

        # Find next preferred day
        if preferred_days:
            days_ahead = 1
            for day in preferred_days:
                if day >= current_day:
                    days_ahead = day - current_day
                    break
            else:
                days_ahead = (7 - current_day) + preferred_days[0]
        else:
            days_ahead = 1

        next_order = now + timedelta(days=days_ahead)
        next_order = next_order.replace(
            hour=preferred_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

        # Calculate confidence
        confidence = 0.5
        if daily.get("daily_pattern") != "no_data":
            confidence += 0.3
        if weekly.get("weekly_pattern") != "no_data":
            confidence += 0.2
        confidence = min(1.0, confidence)

        return {
            "preferred_hour": preferred_hour,
            "preferred_day_of_week": preferred_days[0] if preferred_days else current_day,
            "confidence_score": round(confidence, 2),
            "next_recommended_order_time": next_order.isoformat(),
            "daily_pattern": daily.get("daily_pattern"),
            "weekly_pattern": weekly.get("weekly_pattern"),
        }

    def predict_preferred_vendor(self, user_id: int) -> dict[str, Any]:
        """Predict user's preferred vendor for next order.

        Returns:
            - vendor_id
            - vendor_name
            - vendor_type
            - confidence_score
            - reason
        """
        fav_vendors = self.learn_favourite_vendors(user_id)

        if not fav_vendors:
            return {
                "vendor_id": None,
                "vendor_name": None,
                "vendor_type": None,
                "confidence_score": 0.0,
                "reason": "No order history",
            }

        best_vendor = fav_vendors[0]

        return {
            "vendor_id": best_vendor["vendor_id"],
            "vendor_name": best_vendor["vendor_name"],
            "vendor_type": best_vendor["vendor_type"],
            "confidence_score": best_vendor["confidence"],
            "reason": f"Ordered {best_vendor['order_count']} times",
            "order_count": best_vendor["order_count"],
        }

    def predict_preferred_item(self, user_id: int) -> dict[str, Any]:
        """Predict user's preferred menu item for next order.

        Returns:
            - item_id
            - item_name
            - category
            - confidence_score
            - reason
        """
        fav_foods = self.learn_favourite_foods(user_id)
        fav_stationery = self.learn_favourite_stationery(user_id)

        # Determine which type based on time
        now = utcnow_naive()
        current_hour = now.hour

        if 10 <= current_hour <= 16:
            # Afternoon: prefer stationery
            items = fav_stationery if fav_stationery else fav_foods
            item_type = "stationery"
        else:
            # Morning/Evening: prefer food
            items = fav_foods if fav_foods else fav_stationery
            item_type = "food"

        if not items:
            return {
                "item_id": None,
                "item_name": None,
                "category": None,
                "confidence_score": 0.0,
                "reason": "No order history",
            }

        best_item = items[0]

        return {
            "item_id": best_item["item_id"],
            "item_name": best_item["name"],
            "category": best_item["category"],
            "confidence_score": best_item["confidence"],
            "reason": f"Ordered {best_item['order_count']} times ({item_type})",
            "order_count": best_item["order_count"],
        }

    # ── Prediction Storage ────────────────────────────────────────────────

    def save_prediction(
        self,
        user_id: int,
        prediction_type: str,
        predicted_values: dict[str, Any],
        confidence_score: float,
    ) -> PredictionHistory:
        """Save a prediction to history for learning."""
        prediction = PredictionHistory(
            user_id=user_id,
            prediction_type=prediction_type,
            predicted_vendor_id=predicted_values.get("vendor_id"),
            predicted_menu_item_id=predicted_values.get("item_id"),
            predicted_hour=predicted_values.get("hour"),
            predicted_day_of_week=predicted_values.get("day_of_week"),
            confidence_score=confidence_score,
            prediction_data=predicted_values.get("metadata", {}),
        )

        self.db.add(prediction)
        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def resolve_prediction(self, prediction_id: int, actual_order_id: int) -> None:
        """Resolve a prediction with actual order outcome."""
        prediction = (
            self.db.query(PredictionHistory)
            .filter(PredictionHistory.id == prediction_id)
            .first()
        )

        if not prediction:
            return

        order = (
            self.db.query(Order)
            .filter(Order.id == actual_order_id)
            .first()
        )

        if not order:
            return

        # Update prediction with actual values
        prediction.actual_order_id = actual_order_id
        prediction.actual_vendor_id = order.vendor_id
        prediction.actual_hour = order.created_at.hour

        # Get actual menu item
        order_items = (
            self.db.query(OrderItem)
            .filter(OrderItem.order_id == actual_order_id)
            .first()
        )

        if order_items:
            prediction.actual_menu_item_id = order_items.menu_item_id

        # Calculate accuracy
        correct = 1

        if prediction.predicted_vendor_id and prediction.actual_vendor_id:
            if prediction.predicted_vendor_id != prediction.actual_vendor_id:
                correct = 0

        if prediction.predicted_hour and prediction.actual_hour:
            # Allow 1 hour tolerance
            if abs(prediction.predicted_hour - prediction.actual_hour) > 1:
                correct = 0

        prediction.was_correct = correct
        prediction.resolved_at = utcnow_naive()

        self.db.commit()

    def get_prediction_accuracy(self, user_id: int, days: int = 30) -> dict[str, Any]:
        """Get prediction accuracy statistics for a user."""
        since = utcnow_naive() - timedelta(days=days)

        predictions = (
            self.db.query(PredictionHistory)
            .filter(
                PredictionHistory.user_id == user_id,
                PredictionHistory.predicted_at >= since,
                PredictionHistory.was_correct.isnot(None),
            )
            .all()
        )

        if not predictions:
            return {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "by_type": {},
            }

        total = len(predictions)
        correct = sum(1 for p in predictions if p.was_correct == 1)
        accuracy = (correct / total) * 100 if total > 0 else 0.0

        # Accuracy by type
        by_type = defaultdict(lambda: {"total": 0, "correct": 0})
        for p in predictions:
            by_type[p.prediction_type]["total"] += 1
            if p.was_correct == 1:
                by_type[p.prediction_type]["correct"] += 1

        type_accuracy = {}
        for ptype, stats in by_type.items():
            type_accuracy[ptype] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": round((stats["correct"] / stats["total"]) * 100, 1),
            }

        return {
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": round(accuracy, 1),
            "by_type": type_accuracy,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def get_suggested_reorder(self, user_id: int) -> dict[str, Any]:
        """Get suggested reorder with prediction confidence.

        Returns:
            - suggested_items: [items to reorder]
            - suggested_time: when to order
            - confidence: prediction confidence
            - reasoning: why these suggestions
        """
        # Get prediction
        prediction = self.predict_next_order(user_id)

        # Save prediction
        self.save_prediction(
            user_id=user_id,
            prediction_type="next_order",
            predicted_values={
                "vendor_id": prediction["predicted_vendor_id"],
                "item_id": prediction["predicted_menu_item_id"],
                "hour": prediction["predicted_hour"],
                "day_of_week": prediction["predicted_day_of_week"],
                "metadata": prediction["patterns"],
            },
            confidence_score=prediction["confidence_score"],
        )

        # Get suggested items
        suggested_items = []

        if prediction["predicted_menu_item_id"]:
            mi = (
                self.db.query(MenuItem)
                .filter(MenuItem.id == prediction["predicted_menu_item_id"])
                .first()
            )

            if mi and mi.is_available:
                suggested_items.append({
                    "item_id": mi.id,
                    "item_name": mi.name,
                    "vendor_id": mi.vendor_id,
                    "price": mi.price,
                    "image_url": mi.image_url,
                    "is_available": mi.is_available,
                    "reason": "Based on your ordering pattern",
                })

        # Add other frequent items
        snapshot = (
            self.db.query(UserPreferenceSnapshot)
            .filter(UserPreferenceSnapshot.user_id == user_id)
            .first()
        )

        if snapshot and snapshot.favourite_menu_items:
            for item in snapshot.favourite_menu_items[:3]:
                if item["item_id"] != prediction["predicted_menu_item_id"]:
                    mi = self.db.query(MenuItem).filter(MenuItem.id == item["item_id"]).first()
                    if mi and mi.is_available:
                        suggested_items.append({
                            "item_id": mi.id,
                            "item_name": mi.name,
                            "vendor_id": mi.vendor_id,
                            "price": mi.price,
                            "image_url": mi.image_url,
                            "is_available": mi.is_available,
                            "reason": f"You've ordered this {item['order_count']} times",
                        })

        # Get suggested time
        time_prediction = self.predict_preferred_time(user_id)

        return {
            "suggested_items": suggested_items[:5],
            "suggested_time": time_prediction["next_recommended_order_time"],
            "preferred_hour": time_prediction["preferred_hour"],
            "preferred_day": time_prediction["preferred_day_of_week"],
            "confidence": prediction["confidence_score"],
            "reasoning": prediction["reasoning"],
            "patterns": prediction["patterns"],
        }

    def get_prediction_insights(self, user_id: int) -> dict[str, Any]:
        """Get comprehensive prediction insights for a user.

        Returns:
            - weekly_patterns
            - daily_patterns
            - semester_patterns
            - favourite_vendors
            - favourite_foods
            - favourite_stationery
            - prediction_accuracy
            - next_order_prediction
        """
        weekly = self.learn_weekly_patterns(user_id)
        daily = self.learn_daily_patterns(user_id)
        semester = self.learn_semester_patterns(user_id)
        fav_vendors = self.learn_favourite_vendors(user_id)
        fav_foods = self.learn_favourite_foods(user_id)
        fav_stationery = self.learn_favourite_stationery(user_id)
        accuracy = self.get_prediction_accuracy(user_id)
        next_order = self.predict_next_order(user_id)

        return {
            "weekly_patterns": weekly,
            "daily_patterns": daily,
            "semester_patterns": semester,
            "favourite_vendors": fav_vendors[:5],
            "favourite_foods": fav_foods[:5],
            "favourite_stationery": fav_stationery[:5],
            "prediction_accuracy": accuracy,
            "next_order_prediction": next_order,
        }
