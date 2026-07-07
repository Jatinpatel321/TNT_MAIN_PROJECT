from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order
from app.modules.slots.model import Slot


class DemandPlanner:
    """AI-powered demand planning and forecasting"""

    def __init__(self, db: Session):
        self.db = db

    def get_demand_planning(self, vendor_id: int) -> Dict[str, Any]:
        """Generate comprehensive demand planning for vendor"""

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Analyze historical demand patterns
        demand_patterns = self._analyze_demand_patterns(vendor_id, thirty_days_ago)

        # Generate demand forecast
        forecast = self._generate_demand_forecast(vendor_id, thirty_days_ago)

        # Calculate optimal capacity
        optimal_capacity = self._calculate_optimal_capacity(vendor_id, demand_patterns)

        # Generate planning recommendations
        recommendations = self._generate_planning_recommendations(demand_patterns, forecast, optimal_capacity)

        return {
            "vendor_id": vendor_id,
            "demand_patterns": demand_patterns,
            "forecast": forecast,
            "optimal_capacity": optimal_capacity,
            "recommendations": recommendations
        }

    def _analyze_demand_patterns(self, vendor_id: int, since: datetime) -> Dict[str, Any]:
        """Analyze historical demand patterns"""

        # Daily demand pattern
        daily_pattern = self.db.query(
            func.extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count'),
            func.extract('dow', Order.created_at).label('day_of_week')
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).group_by(
            func.extract('hour', Order.created_at),
            func.extract('dow', Order.created_at)
        ).all()

        # Peak hours analysis
        peak_hours = self._identify_peak_hours(daily_pattern)

        # Demand volatility
        volatility = self._calculate_demand_volatility(vendor_id, since)

        return {
            "peak_hours": peak_hours,
            "daily_pattern": [{"hour": int(row.hour), "day": int(row.day_of_week), "orders": row.order_count} for row in daily_pattern],
            "volatility_score": volatility
        }

    def _generate_demand_forecast(self, vendor_id: int, since: datetime) -> Dict[str, Any]:
        """Generate demand forecast for next 7 days"""

        # Simple trend-based forecasting
        recent_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).scalar()

        days = (utcnow_naive() - since).days
        daily_avg = recent_orders / max(days, 1)

        # Forecast next 7 days with slight growth assumption
        growth_factor = 1.05  # 5% growth
        forecast = []

        for day in range(1, 8):
            forecast_orders = int(daily_avg * growth_factor)
            forecast.append({
                "day": day,
                "predicted_orders": forecast_orders,
                "confidence": 0.75
            })

        return {
            "period": "next_7_days",
            "forecast": forecast,
            "total_predicted": sum(f["predicted_orders"] for f in forecast)
        }

    def _calculate_optimal_capacity(self, vendor_id: int, demand_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal capacity based on demand patterns"""

        # Get current slots
        current_slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()

        total_capacity = sum(slot.max_orders for slot in current_slots)
        peak_hour_demand = max([p["orders"] for p in demand_patterns["daily_pattern"]], default=0)

        # Optimal capacity should handle peak demand with buffer
        optimal_capacity = int(peak_hour_demand * 1.2)  # 20% buffer

        return {
            "current_capacity": total_capacity,
            "optimal_capacity": optimal_capacity,
            "capacity_gap": optimal_capacity - total_capacity,
            "recommendation": "increase" if optimal_capacity > total_capacity else "maintain"
        }

    def _generate_planning_recommendations(self, patterns: Dict[str, Any], forecast: Dict[str, Any], capacity: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable planning recommendations"""

        recommendations = []

        # Capacity recommendations
        if capacity["capacity_gap"] > 0:
            recommendations.append({
                "type": "capacity",
                "priority": "high",
                "title": "Increase Capacity",
                "description": f"Consider increasing capacity by {capacity['capacity_gap']} slots to handle peak demand",
                "impact": "high"
            })

        # Peak hour recommendations
        peak_hours = patterns["peak_hours"]
        if peak_hours:
            recommendations.append({
                "type": "scheduling",
                "priority": "medium",
                "title": "Optimize Peak Hours",
                "description": f"Focus on peak hours: {', '.join([f'{h}:00' for h in peak_hours])}",
                "impact": "medium"
            })

        # Volatility recommendations
        if patterns["volatility_score"] > 0.7:
            recommendations.append({
                "type": "risk_management",
                "priority": "medium",
                "title": "High Demand Volatility",
                "description": "Demand is highly variable. Consider flexible staffing or dynamic pricing",
                "impact": "medium"
            })

        return recommendations

    def _identify_peak_hours(self, daily_pattern) -> List[int]:
        """Identify peak ordering hours"""

        if not daily_pattern:
            return []

        # Group by hour and sum orders across days
        hour_totals = {}
        for row in daily_pattern:
            hour = int(row.hour)
            if hour not in hour_totals:
                hour_totals[hour] = 0
            hour_totals[hour] += row.order_count

        # Sort by total orders descending
        sorted_hours = sorted(hour_totals.items(), key=lambda x: x[1], reverse=True)

        # Return top 3 peak hours
        return [hour for hour, _ in sorted_hours[:3]]

    def _calculate_demand_volatility(self, vendor_id: int, since: datetime) -> float:
        """Calculate demand volatility score (0-1)"""

        # Get daily order counts
        daily_orders = self.db.query(
            func.date(Order.created_at).label('date'),
            func.count(Order.id).label('count')
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= since
        ).group_by(func.date(Order.created_at))\
         .order_by(func.date(Order.created_at))\
         .all()

        if len(daily_orders) < 2:
            return 0.0

        # Calculate coefficient of variation
        counts = [row.count for row in daily_orders]
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5

        cv = std_dev / mean if mean > 0 else 0

        # Normalize to 0-1 scale (cap at 1.0)
        return min(cv, 1.0)
