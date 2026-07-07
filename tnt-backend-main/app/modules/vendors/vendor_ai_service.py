"""Vendor AI Intelligence Service for demand forecasting, predictions, and insights."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot, SlotCapacityRule
from app.modules.menu.model import MenuItem
from app.modules.users.model import User


class VendorAIService:
    """AI-powered vendor intelligence service for forecasting and recommendations."""

    def __init__(self, db: Session):
        self.db = db

    # ── Demand Prediction ──────────────────────────────────────────────────

    def get_daily_forecast(self, vendor_id: int, days: int = 7) -> Dict[str, Any]:
        """Predict daily order volume for the next N days."""
        from datetime import date, timedelta
        today = date.today()
        
        # Historical daily averages from last 30 days
        thirty_days_ago = datetime.combine(today - timedelta(days=30), datetime.min.time())
        historical = self.db.query(
            func.date(Order.created_at).label("order_date"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).group_by(func.date(Order.created_at)).all()
        
        historical_map = {row.order_date: row.order_count for row in historical}
        
        # Calculate day-of-week averages
        dow_avg: Dict[int, List[int]] = {i: [] for i in range(7)}
        for row in historical:
            if hasattr(row.order_date, 'weekday'):
                dow = row.order_date.weekday()
            else:
                dow = row.order_date.weekday()
            dow_avg[dow].append(row.order_count)
        
        dow_prediction: Dict[int, float] = {}
        for day, counts in dow_avg.items():
            dow_prediction[day] = sum(counts) / len(counts) if counts else 0
        
        # Generate forecast for next N days
        forecast = []
        for i in range(days):
            forecast_date = today + timedelta(days=i)
            dow = forecast_date.weekday()
            predicted = round(dow_prediction.get(dow, 0))
            
            # Factor in recent trend (last 3 days vs same period last week)
            recent_avg = sum(
                historical_map.get(today - timedelta(days=d), 0)
                for d in range(3)
            ) / 3 if len(historical) >= 3 else 0
            
            adjusted = max(0, int(predicted * 0.8 + recent_avg * 0.2))
            
            forecast.append({
                "date": forecast_date.isoformat(),
                "day_name": forecast_date.strftime("%A"),
                "predicted_orders": adjusted,
                "confidence": min(0.95, 0.5 + len(historical) * 0.01),
            })
        
        total_predicted = sum(f["predicted_orders"] for f in forecast)
        
        return {
            "vendor_id": vendor_id,
            "forecast": forecast,
            "total_predicted": total_predicted,
            "daily_average": round(total_predicted / max(1, days), 1),
            "recommendation": self._get_capacity_recommendation(total_predicted / max(1, days)),
        }

    def get_weekly_forecast(self, vendor_id: int, weeks: int = 4) -> Dict[str, Any]:
        """Predict weekly order volume for the next N weeks."""
        from datetime import date
        today = date.today()
        
        # Historical weekly data from last 12 weeks
        twelve_weeks_ago = today - timedelta(weeks=12)
        historical = self.db.query(
            func.date_trunc("week", Order.created_at).label("week_start"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= twelve_weeks_ago,
        ).group_by(func.date_trunc("week", Order.created_at)).all()
        
        weekly_counts = [row.order_count for row in historical]
        avg_weekly = sum(weekly_counts) / len(weekly_counts) if weekly_counts else 0
        
        # Simple linear trend
        trend = 0
        if len(weekly_counts) >= 2:
            recent_avg = sum(weekly_counts[-2:]) / 2
            trend = recent_avg - avg_weekly
        
        forecast = []
        for i in range(weeks):
            week_start = today + timedelta(weeks=i)
            predicted = max(0, int(avg_weekly + trend * (i + 1) * 0.5))
            forecast.append({
                "week_start": week_start.isoformat(),
                "predicted_orders": predicted,
                "trend": "up" if trend > 0 else ("down" if trend < 0 else "stable"),
            })
        
        return {
            "vendor_id": vendor_id,
            "forecast": forecast,
            "weekly_average": round(avg_weekly, 1),
            "trend_direction": "up" if trend > 0 else ("down" if trend < 0 else "stable"),
        }

    def get_monthly_forecast(self, vendor_id: int, months: int = 3) -> Dict[str, Any]:
        """Predict monthly order volume for the next N months."""
        from datetime import date
        today = date.today()
        
        six_months_ago = today - timedelta(days=180)
        historical = self.db.query(
            func.date_trunc("month", Order.created_at).label("month_start"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= six_months_ago,
        ).group_by(func.date_trunc("month", Order.created_at)).all()
        
        monthly_counts = [row.order_count for row in historical]
        avg_monthly = sum(monthly_counts) / len(monthly_counts) if monthly_counts else 0
        
        forecast = []
        for i in range(months):
            month_start = today.replace(day=1) + timedelta(days=30 * i)
            predicted = max(0, int(avg_monthly * (1 + i * 0.05)))
            forecast.append({
                "month": month_start.strftime("%B %Y"),
                "predicted_orders": predicted,
            })
        
        return {
            "vendor_id": vendor_id,
            "forecast": forecast,
            "monthly_average": round(avg_monthly, 1),
        }

    # ── Popular Items Prediction ───────────────────────────────────────────

    def get_popular_items(self, vendor_id: int, limit: int = 10) -> Dict[str, Any]:
        """Get popular menu items with order frequency and trends."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        
        popular = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label("order_count"),
        ).join(
            OrderItem, OrderItem.menu_item_id == MenuItem.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(
            MenuItem.id, MenuItem.name, MenuItem.price
        ).order_by(
            func.count(OrderItem.id).desc()
        ).limit(limit).all()
        
        total_orders = sum(row.order_count for row in popular) if popular else 1
        
        items = []
        for row in popular:
            percentage = round(row.order_count / total_orders * 100, 1)
            items.append({
                "item_id": row.id,
                "name": row.name,
                "price": float(row.price),
                "order_count": row.order_count,
                "popularity_percentage": percentage,
                "trend": self._get_item_trend(vendor_id, row.id),
            })
        
        return {
            "vendor_id": vendor_id,
            "popular_items": items,
            "total_items_analyzed": len(items),
            "top_item": items[0]["name"] if items else None,
        }

    def _get_item_trend(self, vendor_id: int, item_id: int) -> str:
        """Determine if an item's popularity is trending up, down, or stable."""
        now = utcnow_naive()
        recent = now - timedelta(days=7)
        older = now - timedelta(days=14)
        
        recent_count = self.db.query(func.count(OrderItem.id)).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            OrderItem.menu_item_id == item_id,
            Order.vendor_id == vendor_id,
            Order.created_at.between(recent, now),
        ).scalar() or 0
        
        older_count = self.db.query(func.count(OrderItem.id)).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            OrderItem.menu_item_id == item_id,
            Order.vendor_id == vendor_id,
            Order.created_at.between(older, recent),
        ).scalar() or 0
        
        if recent_count > older_count * 1.2:
            return "up"
        elif recent_count < older_count * 0.8:
            return "down"
        return "stable"

    # ── Stationery Workload Prediction ─────────────────────────────────────

    def get_stationery_workload(self, vendor_id: int) -> Dict[str, Any]:
        """Predict stationery service workload."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        
        service_counts = self.db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).group_by(extract("hour", Order.created_at)).all()
        
        hourly_distribution = {row.hour: row.count for row in service_counts}
        
        # Predict today's workload by hour
        current_hour = utcnow_naive().hour
        today_workload = []
        for hour in range(8, 20):  # 8 AM to 8 PM
            historical_avg = hourly_distribution.get(hour, 0)
            predicted = max(1, historical_avg)
            today_workload.append({
                "hour": f"{hour}:00",
                "predicted_orders": predicted,
                "load_level": "high" if predicted > 15 else ("medium" if predicted > 8 else "low"),
            })
        
        total_predicted = sum(w["predicted_orders"] for w in today_workload)
        
        return {
            "vendor_id": vendor_id,
            "vendor_type": "stationery",
            "hourly_workload": today_workload,
            "total_predicted_today": total_predicted,
            "peak_hour": max(today_workload, key=lambda w: w["predicted_orders"])["hour"],
            "recommendation": "Expect higher than usual workload" if total_predicted > 50 else "Normal workload expected",
        }

    # ── Peak Time Prediction ───────────────────────────────────────────────

    def get_peak_time_prediction(self, vendor_id: int) -> Dict[str, Any]:
        """Predict peak hours for the vendor."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        
        hourly_orders = self.db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).group_by(extract("hour", Order.created_at)).all()
        
        distribution = {int(row.hour): row.count for row in hourly_orders}
        total = sum(distribution.values()) or 1
        
        peak_hours = []
        for hour in sorted(distribution.keys()):
            percentage = distribution[hour] / total * 100
            peak_hours.append({
                "hour": hour,
                "percentage": round(percentage, 1),
                "is_peak": percentage > 10,
            })
        
        peak_hours_list = [p for p in peak_hours if p["is_peak"]]
        
        return {
            "vendor_id": vendor_id,
            "peak_hours": peak_hours,
            "busiest_hour": max(peak_hours, key=lambda p: p["percentage"])["hour"] if peak_hours else None,
            "peak_periods": [
                {"start": p["hour"], "label": f"{p['hour']}:00 - {(p['hour'] + 1) % 24}:00", "intensity": round(p["percentage"], 1)}
                for p in peak_hours_list
            ],
        }

    # ── Food Waste Reduction Insights ──────────────────────────────────────

    def get_waste_reduction_insights(self, vendor_id: int) -> Dict[str, Any]:
        """Generate food waste reduction insights based on order data."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        
        # Count cancelled orders (potential waste)
        cancelled = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0
        
        total = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 1
        
        cancellation_rate = round(cancelled / total * 100, 1)
        
        # Items that are ordered but cancelled frequently
        wasted_items = self.db.query(
            MenuItem.name,
            func.count(OrderItem.id).label("cancelled_count"),
        ).join(
            OrderItem, OrderItem.menu_item_id == MenuItem.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).group_by(MenuItem.name).order_by(
            func.count(OrderItem.id).desc()
        ).limit(5).all()
        
        return {
            "vendor_id": vendor_id,
            "cancellation_rate": cancellation_rate,
            "wasted_items": [
                {"name": item.name, "cancelled_count": item.cancelled_count}
                for item in wasted_items
            ],
            "insights": [
                f"Cancellation rate is {cancellation_rate}% - {'high' if cancellation_rate > 10 else 'low'}",
                f"Top wasted item: {wasted_items[0].name if wasted_items else 'N/A'}",
                "Consider reducing portions for frequently cancelled items" if cancellation_rate > 10 else "Waste levels are acceptable",
            ],
            "recommendations": [
                "Reduce inventory for low-demand items",
                "Offer smaller portions for top cancelled items",
                "Implement pre-order cutoff times",
            ] if cancellation_rate > 10 else [
                "Current inventory management is efficient",
                "Continue monitoring cancellation patterns",
            ],
        }

    # ── Inventory Suggestions ──────────────────────────────────────────────

    def get_inventory_suggestions(self, vendor_id: int) -> Dict[str, Any]:
        """Generate inventory stocking suggestions."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        
        item_demand = self.db.query(
            MenuItem.id,
            MenuItem.name,
            func.count(OrderItem.id).label("demand"),
        ).join(
            OrderItem, OrderItem.menu_item_id == MenuItem.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(MenuItem.id, MenuItem.name).order_by(
            func.count(OrderItem.id).desc()
        ).all()
        
        total_demand = sum(row.demand for row in item_demand) or 1
        
        suggestions = []
        for row in item_demand:
            percentage = row.demand / total_demand * 100
            if percentage > 15:
                action = "increase_stock"
                reason = "High demand item"
            elif percentage > 5:
                action = "maintain_stock"
                reason = "Steady demand"
            else:
                action = "reduce_stock"
                reason = "Low demand"
            
            suggestions.append({
                "item_id": row.id,
                "name": row.name,
                "demand_count": row.demand,
                "demand_percentage": round(percentage, 1),
                "suggested_action": action,
                "reason": reason,
            })
        
        high_demand = [s for s in suggestions if s["suggested_action"] == "increase_stock"]
        low_demand = [s for s in suggestions if s["suggested_action"] == "reduce_stock"]
        
        return {
            "vendor_id": vendor_id,
            "suggestions": suggestions,
            "high_demand_items": high_demand,
            "low_demand_items": low_demand,
            "summary": f"Stock up on {len(high_demand)} high-demand items, reduce {len(low_demand)} low-demand items",
        }

    # ── AI Recommendations ─────────────────────────────────────────────────

    def get_ai_recommendations(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Generate comprehensive AI recommendations for the vendor."""
        recommendations = []
        
        # 1. Capacity Recommendation
        forecast = self.get_daily_forecast(vendor_id, days=7)
        daily_avg = forecast["daily_average"]
        
        # Check current slot capacity
        total_capacity = self.db.query(func.sum(Slot.max_orders)).filter(
            Slot.vendor_id == vendor_id,
        ).scalar() or 0
        
        slots_per_day = max(1, self.db.query(func.count(Slot.id)).filter(
            Slot.vendor_id == vendor_id,
        ).scalar() or 1)
        
        avg_capacity_per_slot = total_capacity / slots_per_day if slots_per_day else 10
        
        if daily_avg > avg_capacity_per_slot * 0.8:
            recommendations.append({
                "type": "capacity",
                "action": "increase_capacity",
                "priority": "high",
                "message": f"Daily forecast ({daily_avg}) exceeds 80% of slot capacity ({avg_capacity_per_slot}). Consider increasing slot capacity.",
                "details": {"current_capacity": avg_capacity_per_slot, "forecast": daily_avg},
            })
        elif daily_avg < avg_capacity_per_slot * 0.3:
            recommendations.append({
                "type": "capacity",
                "action": "reduce_capacity",
                "priority": "low",
                "message": f"Daily forecast ({daily_avg}) is below 30% of slot capacity. Consider reducing slot capacity to save resources.",
                "details": {"current_capacity": avg_capacity_per_slot, "forecast": daily_avg},
            })
        
        # 2. Staff Recommendation
        peak = self.get_peak_time_prediction(vendor_id)
        peak_hours = [p for p in peak["peak_hours"] if p.get("is_peak")]
        if len(peak_hours) > 2:
            recommendations.append({
                "type": "staff",
                "action": "add_staff",
                "priority": "medium",
                "message": f"Multiple peak periods detected ({len(peak_hours)}). Consider adding staff during peak hours.",
                "details": {"peak_hours": peak_hours},
            })
        
        # 3. Stock Recommendation
        inventory = self.get_inventory_suggestions(vendor_id)
        if inventory["high_demand_items"]:
            recommendations.append({
                "type": "inventory",
                "action": "prepare_extra_stock",
                "priority": "medium",
                "message": f"Prepare extra stock for {len(inventory['high_demand_items'])} high-demand items.",
                "details": {"items": [i["name"] for i in inventory["high_demand_items"]]},
            })
        
        # 4. Trend-based recommendation
        weekly = self.get_weekly_forecast(vendor_id, weeks=4)
        if weekly["trend_direction"] == "up":
            recommendations.append({
                "type": "trend",
                "action": "increase_capacity",
                "priority": "medium",
                "message": "Upward trend detected. Plan for increased capacity in coming weeks.",
                "details": {"trend": weekly["trend_direction"], "weekly_avg": weekly["weekly_average"]},
            })
        elif weekly["trend_direction"] == "down":
            recommendations.append({
                "type": "trend",
                "action": "reduce_capacity",
                "priority": "medium",
                "message": "Downward trend detected. Consider reducing capacity and inventory.",
                "details": {"trend": weekly["trend_direction"], "weekly_avg": weekly["weekly_average"]},
            })
        
        return recommendations

    # ── Full AI Dashboard Data ──────────────────────────────────────────────

    def get_full_ai_dashboard(self, vendor_id: int) -> Dict[str, Any]:
        """Get complete AI dashboard data for the vendor."""
        return {
            "vendor_id": vendor_id,
            "daily_forecast": self.get_daily_forecast(vendor_id, days=7),
            "weekly_forecast": self.get_weekly_forecast(vendor_id, weeks=4),
            "monthly_forecast": self.get_monthly_forecast(vendor_id, months=3),
            "popular_items": self.get_popular_items(vendor_id),
            "peak_times": self.get_peak_time_prediction(vendor_id),
            "waste_insights": self.get_waste_reduction_insights(vendor_id),
            "inventory_suggestions": self.get_inventory_suggestions(vendor_id),
            "recommendations": self.get_ai_recommendations(vendor_id),
        }

    def _get_capacity_recommendation(self, daily_average: float) -> str:
        if daily_average > 50:
            return "Increase capacity"
        elif daily_average > 20:
            return "Maintain current capacity"
        else:
            return "Reduce capacity"