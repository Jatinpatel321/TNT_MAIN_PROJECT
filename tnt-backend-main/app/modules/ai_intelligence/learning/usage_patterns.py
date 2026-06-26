from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order
from app.modules.users.model import User


class UsagePatterns:
    """AI-powered usage pattern analysis"""

    def __init__(self, db: Session):
        self.db = db

    def analyze_user_patterns(self, user_id: int) -> Dict[str, Any]:
        """Analyze comprehensive usage patterns for a user"""

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        patterns = {
            "ordering_frequency": self._calculate_ordering_frequency(user_id, thirty_days_ago),
            "preferred_times": self._analyze_preferred_times(user_id, thirty_days_ago),
            "spending_patterns": self._analyze_spending_patterns(user_id, thirty_days_ago),
            "category_preferences": self._analyze_category_preferences(user_id, thirty_days_ago),
            "loyalty_patterns": self._analyze_loyalty_patterns(user_id, thirty_days_ago)
        }

        return patterns

    def analyze_system_patterns(self) -> Dict[str, Any]:
        """Analyze system-wide usage patterns"""

        seven_days_ago = utcnow_naive() - timedelta(days=7)

        patterns = {
            "peak_hours": self._analyze_system_peak_hours(seven_days_ago),
            "popular_categories": self._analyze_popular_categories(seven_days_ago),
            "vendor_performance_trends": self._analyze_vendor_performance_trends(seven_days_ago),
            "demand_forecasting": self._generate_demand_forecast(seven_days_ago)
        }

        return patterns

    def _calculate_ordering_frequency(self, user_id: int, since: datetime) -> Dict[str, Any]:
        """Calculate user's ordering frequency"""

        total_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= since
        ).count()

        days_since = (utcnow_naive() - since).days
        orders_per_day = total_orders / max(days_since, 1)

        # Classify frequency
        if orders_per_day >= 1.0:
            frequency_level = "high"
            description = "Daily ordering"
        elif orders_per_day >= 0.5:
            frequency_level = "medium"
            description = "2-3 times per week"
        elif orders_per_day >= 0.1:
            frequency_level = "low"
            description = "Weekly ordering"
        else:
            frequency_level = "rare"
            description = "Occasional ordering"

        return {
            "total_orders": total_orders,
            "orders_per_day": round(orders_per_day, 2),
            "frequency_level": frequency_level,
            "description": description
        }

    def _analyze_preferred_times(self, user_id: int, since: datetime) -> Dict[str, Any]:
        """Analyze user's preferred ordering times"""

        time_distribution = self.db.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('count')
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since
        ).group_by(extract('hour', Order.created_at))\
         .order_by(func.count(Order.id).desc())\
         .all()

        if not time_distribution:
            return {"preferred_hour": None, "time_pattern": "unknown"}

        preferred_hour = int(time_distribution[0].hour)

        # Classify time preference
        if 6 <= preferred_hour <= 10:
            time_pattern = "morning"
        elif 11 <= preferred_hour <= 14:
            time_pattern = "lunch"
        elif 15 <= preferred_hour <= 17:
            time_pattern = "afternoon"
        elif 18 <= preferred_hour <= 21:
            time_pattern = "dinner"
        else:
            time_pattern = "other"

        return {
            "preferred_hour": preferred_hour,
            "time_pattern": time_pattern,
            "distribution": [{"hour": int(row.hour), "count": row.count} for row in time_distribution]
        }

    def _analyze_spending_patterns(self, user_id: int, since: datetime) -> Dict[str, Any]:
        """Analyze user's spending patterns"""

        aggregates = self.db.query(
            func.avg(Order.total_amount).label("avg_order_value"),
            func.sum(Order.total_amount).label("total_spent"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since,
            Order.status != "cancelled",
        ).first()

        avg_order_value = float(aggregates.avg_order_value or 0)
        total_spent = float(aggregates.total_spent or 0)
        order_count = int(aggregates.order_count or 0)

        if avg_order_value >= 250:
            spending_category = "high"
        elif avg_order_value >= 120:
            spending_category = "medium"
        else:
            spending_category = "low"

        budget_conscious = order_count > 0 and avg_order_value <= 130

        return {
            "avg_order_value": round(avg_order_value, 2),
            "total_spent": round(total_spent, 2),
            "spending_category": spending_category,
            "budget_conscious": budget_conscious,
        }

    def _analyze_category_preferences(self, user_id: int, since: datetime) -> Dict[str, Any]:
        """Analyze user's category preferences"""

        rows = self.db.query(
            User.vendor_type,
            func.count(Order.id).label("order_count"),
        ).join(
            Order, Order.vendor_id == User.id,
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since,
            Order.status != "cancelled",
        ).group_by(User.vendor_type).all()

        total_orders = sum(int(row.order_count or 0) for row in rows)
        if total_orders == 0:
            return {
                "preferred_category": "unknown",
                "category_distribution": {},
                "diversity_score": 0.0,
            }

        distribution = {
            (row.vendor_type or "unknown"): round((int(row.order_count) / total_orders), 2)
            for row in rows
        }
        preferred_category = max(distribution.items(), key=lambda entry: entry[1])[0]
        diversity_score = round(min(1.0, len(distribution) / 3), 2)

        return {
            "preferred_category": preferred_category,
            "category_distribution": distribution,
            "diversity_score": diversity_score,
        }

    def _analyze_loyalty_patterns(self, user_id: int, since: datetime) -> Dict[str, Any]:
        """Analyze user's loyalty to vendors"""

        vendor_loyalty = self.db.query(
            Order.vendor_id,
            func.count(Order.id).label('order_count')
        ).filter(
            Order.user_id == user_id,
            Order.created_at >= since
        ).group_by(Order.vendor_id)\
         .order_by(func.count(Order.id).desc())\
         .all()

        if not vendor_loyalty:
            return {"loyalty_score": 0, "preferred_vendor": None}

        total_orders = sum(row.order_count for row in vendor_loyalty)
        top_vendor_orders = vendor_loyalty[0].order_count

        loyalty_score = top_vendor_orders / total_orders

        return {
            "loyalty_score": round(loyalty_score, 2),
            "preferred_vendor_id": vendor_loyalty[0].vendor_id,
            "vendor_distribution": [{"vendor_id": row.vendor_id, "count": row.order_count} for row in vendor_loyalty]
        }

    def _analyze_system_peak_hours(self, since: datetime) -> List[Dict[str, Any]]:
        """Analyze system-wide peak hours"""

        peak_hours = self.db.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count')
        ).filter(Order.created_at >= since)\
         .group_by(extract('hour', Order.created_at))\
         .order_by(func.count(Order.id).desc())\
         .limit(5).all()

        return [{"hour": int(row.hour), "order_count": row.order_count} for row in peak_hours]

    def _analyze_popular_categories(self, since: datetime) -> Dict[str, Any]:
        """Analyze popular categories system-wide"""

        rows = self.db.query(
            User.vendor_type,
            func.count(Order.id).label("order_count"),
        ).join(
            Order, Order.vendor_id == User.id,
        ).filter(
            Order.created_at >= since,
            Order.status != "cancelled",
        ).group_by(User.vendor_type).all()

        total_orders = sum(int(row.order_count or 0) for row in rows)
        category_counts = {
            (row.vendor_type or "unknown"): int(row.order_count or 0)
            for row in rows
        }
        food_orders = category_counts.get("food", 0)
        stationery_orders = category_counts.get("stationery", 0)
        trending_category = "unknown"
        if category_counts:
            trending_category = max(category_counts.items(), key=lambda entry: entry[1])[0]

        return {
            "food_orders": food_orders,
            "stationery_orders": stationery_orders,
            "food_percentage": round(((food_orders / total_orders) * 100), 1) if total_orders else 0.0,
            "trending_category": trending_category,
        }

    def _analyze_vendor_performance_trends(self, since: datetime) -> List[Dict[str, Any]]:
        """Analyze vendor performance trends"""

        now = utcnow_naive()
        period_days = max((now - since).days, 1)
        previous_start = since - timedelta(days=period_days)

        vendor_rows = self.db.query(Order.vendor_id).filter(
            Order.created_at >= previous_start,
            Order.status != "cancelled",
        ).distinct().all()

        trends: List[Dict[str, Any]] = []
        for vendor_row in vendor_rows:
            vendor_id = vendor_row.vendor_id

            current_total = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= since,
            ).scalar() or 0
            current_completed = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= since,
                Order.status == "completed",
            ).scalar() or 0

            previous_total = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= previous_start,
                Order.created_at < since,
            ).scalar() or 0
            previous_completed = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= previous_start,
                Order.created_at < since,
                Order.status == "completed",
            ).scalar() or 0

            current_rate = (current_completed / current_total) if current_total else 0.0
            previous_rate = (previous_completed / previous_total) if previous_total else current_rate
            change_pct = round((current_rate - previous_rate) * 100, 1)

            if change_pct > 2:
                trend = "improving"
            elif change_pct < -2:
                trend = "declining"
            else:
                trend = "stable"

            trends.append(
                {
                    "vendor_id": vendor_id,
                    "trend": trend,
                    "completion_rate_change": change_pct,
                }
            )

        trends.sort(key=lambda row: abs(row["completion_rate_change"]), reverse=True)
        return trends[:5]

    def _generate_demand_forecast(self, since: datetime) -> Dict[str, Any]:
        """Generate basic demand forecast"""

        # Simple forecasting based on recent trends
        recent_orders = self.db.query(func.count(Order.id)).filter(
            Order.created_at >= since
        ).scalar()

        days = (utcnow_naive() - since).days
        daily_avg = recent_orders / max(days, 1)

        # Project next 7 days
        forecast = {
            "current_daily_avg": round(daily_avg, 1),
            "next_week_forecast": round(daily_avg * 7, 0),
            "growth_trend": "stable",  # Would analyze trend
            "confidence_level": "medium"
        }

        return forecast
