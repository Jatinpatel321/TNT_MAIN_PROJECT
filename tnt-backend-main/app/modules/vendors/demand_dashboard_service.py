"""Smart Demand Dashboard Service.

Combines ML-powered predictions with real-time data for:
- Demand forecasting (daily/weekly)
- Stock prediction (days until out, recommended restock)
- Rush hour prediction
"""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import Any

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive, ist_now
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem, Inventory
from app.modules.slots.model import Slot
from app.modules.vendors.vendor_ai_service import VendorAIService


class DemandDashboardService:
    """Smart demand dashboard combining real data with ML predictions."""

    def __init__(self, db: Session):
        self.db = db
        self.ai_service = VendorAIService(db)

    # ── Demand Overview ──────────────────────────────────────────────────

    def get_demand_overview(self, vendor_id: int) -> dict[str, Any]:
        """Get demand overview with predictions for next 7 days."""
        today = date.today()
        now = utcnow_naive()

        # Current orders today
        today_start = datetime.combine(today, datetime.min.time())
        orders_today = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= today_start,
        ).scalar() or 0

        # Predicted orders for today based on historical hourly average
        thirty_days_ago = now - timedelta(days=30)
        remaining_hours = max(1, 23 - now.hour)
        hourly_avg = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        hourly_avg = hourly_avg / max(1, 30 * 12)  # ~12 active hours per day
        predicted_remaining = int(hourly_avg * remaining_hours)
        predicted_today = orders_today + predicted_remaining

        # Tomorrow prediction
        tomorrow = today + timedelta(days=1)
        last_week_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
        ).scalar() or 0
        daily_avg = last_week_orders / 30.0
        tomorrow_prediction = max(0, int(daily_avg * (1 + (now.weekday() - 3) * 0.1)))

        # Weekly trend (compare last 7 days vs previous 7)
        last_7 = now - timedelta(days=7)
        prev_7 = now - timedelta(days=14)
        week_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= last_7,
        ).scalar() or 0
        prev_week_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= prev_7,
            Order.created_at < last_7,
        ).scalar() or 0

        if prev_week_orders > 0:
            change_pct = round((week_orders - prev_week_orders) / prev_week_orders * 100, 1)
        else:
            change_pct = 0

        if change_pct > 10:
            trend = "up"
        elif change_pct < -10:
            trend = "down"
        else:
            trend = "stable"

        # Peak hours today (based on historical distribution)
        peak_hours_today = self._get_todays_peak_hours(vendor_id)

        # Day comparison
        yesterday = today - timedelta(days=1)
        yesterday_start = datetime.combine(yesterday, datetime.min.time())
        yesterday_end = today_start
        yesterday_orders = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= yesterday_start,
            Order.created_at < yesterday_end,
        ).scalar() or 0

        vs_yesterday_pct = 0
        if yesterday_orders > 0:
            vs_yesterday_pct = round((orders_today - yesterday_orders) / yesterday_orders * 100, 1)

        # Same day last week
        last_week_day = today - timedelta(days=7)
        lw_start = datetime.combine(last_week_day, datetime.min.time())
        lw_end = datetime.combine(last_week_day + timedelta(days=1), datetime.min.time())
        last_week_same = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= lw_start,
            Order.created_at < lw_end,
        ).scalar() or 0

        vs_last_week_pct = 0
        if last_week_same > 0:
            vs_last_week_pct = round((orders_today - last_week_same) / last_week_same * 100, 1)

        return {
            "vendor_id": vendor_id,
            "date": today.isoformat(),
            "orders_today": orders_today,
            "predicted_today": predicted_today,
            "predicted_remaining": predicted_remaining,
            "tomorrow_prediction": tomorrow_prediction,
            "weekly_trend": trend,
            "weekly_change_pct": change_pct,
            "vs_yesterday_pct": vs_yesterday_pct,
            "vs_last_week_pct": vs_last_week_pct,
            "daily_average": round(daily_avg, 1),
            "peak_hours_today": peak_hours_today,
        }

    # ── Stock Prediction ─────────────────────────────────────────────────

    def get_stock_prediction(self, vendor_id: int) -> dict[str, Any]:
        """Predict stock requirements based on demand forecast."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        items_with_inventory = (
            self.db.query(
                MenuItem.id,
                MenuItem.name,
                MenuItem.price,
                MenuItem.is_available,
                Inventory.current_stock,
                Inventory.low_stock_threshold,
                Inventory.auto_disable,
            )
            .join(Inventory, Inventory.menu_item_id == MenuItem.id)
            .filter(MenuItem.vendor_id == vendor_id)
            .all()
        )

        # Calculate daily demand rate for each item
        item_demand: dict[int, int] = {}
        demand_rows = self.db.query(
            OrderItem.menu_item_id,
            func.sum(OrderItem.quantity).label("total_qty"),
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
            OrderItem.menu_item_id.in_([r.id for r in items_with_inventory]),
        ).group_by(OrderItem.menu_item_id).all()

        for row in demand_rows:
            item_demand[row.menu_item_id] = row.total_qty

        items_predictions = []
        items_critical = 0
        items_low = 0
        items_ok = 0

        for item in items_with_inventory:
            item_id = item.id
            current_stock = item.current_stock or 0
            threshold = item.low_stock_threshold or 10
            daily_demand = item_demand.get(item_id, 0) / 30.0

            if daily_demand > 0:
                days_until_out = round(current_stock / daily_demand, 1)
                recommended_restock = max(0, int(daily_demand * 7 - current_stock))
            else:
                days_until_out = float("inf")
                recommended_restock = max(0, threshold - current_stock)

            if current_stock <= 0:
                urgency = "critical"
                items_critical += 1
            elif current_stock <= threshold:
                urgency = "low"
                items_low += 1
            else:
                urgency = "ok"
                items_ok += 1

            items_predictions.append({
                "item_id": item_id,
                "name": item.name,
                "price": float(item.price),
                "current_stock": current_stock,
                "low_stock_threshold": threshold,
                "daily_demand_rate": round(daily_demand, 1),
                "days_until_out": days_until_out if days_until_out != float("inf") else None,
                "recommended_restock_qty": recommended_restock,
                "is_available": item.is_available,
                "auto_disable": item.auto_disable,
                "urgency": urgency,
            })

        items_predictions.sort(key=lambda x: (
            {"critical": 0, "low": 1, "ok": 2}[x["urgency"]],
            x.get("days_until_out") or 999,
        ))

        return {
            "vendor_id": vendor_id,
            "items": items_predictions,
            "summary": {
                "total_items": len(items_predictions),
                "critical": items_critical,
                "low": items_low,
                "ok": items_ok,
                "needs_attention": items_critical + items_low,
            },
        }

    # ── Rush Prediction ──────────────────────────────────────────────────

    def get_rush_prediction(self, vendor_id: int) -> dict[str, Any]:
        """Predict rush periods for today based on historical patterns."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        now = utcnow_naive()
        current_hour = now.hour

        # Historical hourly distribution (last 30 days)
        hourly_data = self.db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(extract("hour", Order.created_at)).all()

        hourly_map: dict[int, int] = {}
        for row in hourly_data:
            hourly_map[int(row.hour)] = row.count

        max_count = max(hourly_map.values()) if hourly_map else 1
        total_historical = sum(hourly_map.values()) or 1

        # Predict remaining hours today
        predictions = []
        rush_hours = 0
        next_rush_hour = None

        for hour in range(max(6, current_hour), 22):  # 6 AM to 10 PM
            historical = hourly_map.get(hour, 0)
            confidence = min(0.95, historical / max_count) if max_count > 0 else 0.3
            is_rush = (historical / max_count) > 0.6 if max_count > 0 else False

            if is_rush:
                rush_hours += 1
                if next_rush_hour is None:
                    next_rush_hour = hour

            predictions.append({
                "hour": hour,
                "label": f"{hour}:00 - {hour + 1}:00",
                "predicted_orders": int(historical),
                "confidence": round(confidence, 2),
                "is_rush": is_rush,
                "percentage": round(historical / total_historical * 100, 1),
            })

        # Staff recommendation
        if rush_hours > 2:
            staff_rec = "Add extra staff during peak hours for efficient service"
        elif rush_hours > 0:
            staff_rec = "Monitor peak hours for staffing needs"
        else:
            staff_rec = "Standard staffing should be sufficient"

        return {
            "vendor_id": vendor_id,
            "current_hour": current_hour,
            "predictions": predictions,
            "rush_hours_count": rush_hours,
            "next_rush_hour": next_rush_hour,
            "staff_recommendation": staff_rec,
            "busiest_hour": max(hourly_map, key=hourly_map.get) if hourly_map else None,
        }

    # ── Full Dashboard ───────────────────────────────────────────────────

    def get_full_dashboard(self, vendor_id: int) -> dict[str, Any]:
        """Get complete smart demand dashboard."""
        return {
            "vendor_id": vendor_id,
            "demand_overview": self.get_demand_overview(vendor_id),
            "stock_prediction": self.get_stock_prediction(vendor_id),
            "rush_prediction": self.get_rush_prediction(vendor_id),
            "ai_forecast": self.ai_service.get_daily_forecast(vendor_id, days=7),
            "recommendations": self.ai_service.get_ai_recommendations(vendor_id),
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_todays_peak_hours(self, vendor_id: int) -> list[dict[str, Any]]:
        """Get peak hours for today based on historical data."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        now = utcnow_naive()

        hourly = self.db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("count"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= thirty_days_ago,
            Order.status != OrderStatus.CANCELLED,
            extract("hour", Order.created_at).between(6, 22),
        ).group_by(extract("hour", Order.created_at)).all()

        hourly_map = {int(r.hour): r.count for r in hourly}
        max_val = max(hourly_map.values()) if hourly_map else 1

        peak_hours = []
        for hour in range(6, 22):
            count = hourly_map.get(hour, 0)
            is_peak = (count / max_val) > 0.6 if max_val > 0 else False
            peak_hours.append({
                "hour": hour,
                "label": f"{hour}:00",
                "is_peak": is_peak,
                "historical_orders": count,
            })

        return peak_hours
