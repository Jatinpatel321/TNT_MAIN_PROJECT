"""Vendor Analytics Suite - Real data analytics with sample data generation."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple
from math import ceil

from sqlalchemy import func, extract, text
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot


class VendorAnalyticsService:
    """Vendor analytics powered by real order data with sample data fallback."""

    def __init__(self, db: Session):
        self.db = db

    def _ensure_sample_data(self, vendor_id: int) -> bool:
        """Generate sample analytics data if insufficient real data exists."""
        count = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
        ).scalar() or 0

        if count >= 50:
            return False

        # Generate sample orders for the past 90 days
        from app.modules.menu.model import MenuItem
        from app.modules.orders.model import OrderItem

        menu_items = self.db.query(MenuItem).filter(MenuItem.vendor_id == vendor_id).all()
        if not menu_items:
            return False

        today = date.today()
        sample_order_count = 100

        # Get a user to assign orders to (use first regular user or admin)
        from app.modules.users.model import User
        user = self.db.query(User).filter(User.role != "vendor").first()
        if not user:
            return False

        # Get slots for this vendor
        slots = self.db.query(Slot).filter(Slot.vendor_id == vendor_id).all()

        import random
        statuses = [s.value for s in OrderStatus]

        orders_created = 0
        for day_offset in range(90):
            orders_today = random.randint(0, 5)
            for _ in range(orders_today):
                order_date = datetime.combine(
                    today - timedelta(days=day_offset),
                    datetime.min.time().replace(hour=random.randint(8, 20))
                )

                slot_id = slots[random.randint(0, len(slots)-1)].id if slots else None
                status = random.choice(statuses)
                total = 0

                order = Order(
                    user_id=user.id,
                    vendor_id=vendor_id,
                    slot_id=slot_id,
                    status=status,
                    total_amount=total,
                    created_at=order_date,
                )
                self.db.add(order)
                self.db.flush()

                # Add 1-4 items
                num_items = random.randint(1, 4)
                for _ in range(num_items):
                    item = random.choice(menu_items)
                    qty = random.randint(1, 3)
                    price = (item.price or 50) * qty
                    total += price

                    order_item = OrderItem(
                        order_id=order.id,
                        menu_item_id=item.id,
                        quantity=qty,
                        price=price,
                    )
                    self.db.add(order_item)

                order.total_amount = total
                orders_created += 1

        self.db.flush()
        return True

    # ── Daily Sales ────────────────────────────────────────────────────────

    def get_daily_sales(self, vendor_id: int, days: int = 30) -> Dict[str, Any]:
        """Get daily sales data for the last N days."""
        self._ensure_sample_data(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=days)

        daily = self.db.query(
            func.date(Order.created_at).label("order_date"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        ).group_by(func.date(Order.created_at)).order_by(
            func.date(Order.created_at)
        ).all()

        sales_data = []
        for row in daily:
            sales_data.append({
                "date": row.order_date.isoformat() if hasattr(row.order_date, 'isoformat') else str(row.order_date),
                "orders": row.order_count,
                "revenue": float(row.revenue or 0),
            })

        total_revenue = sum(d["revenue"] for d in sales_data)
        total_orders = sum(d["orders"] for d in sales_data)

        return {
            "vendor_id": vendor_id,
            "period": f"last_{days}_days",
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "daily_average_revenue": round(total_revenue / max(1, days), 2),
            "daily_average_orders": round(total_orders / max(1, days), 1),
            "sales_data": sales_data,
        }

    # ── Weekly Sales ───────────────────────────────────────────────────────

    def get_weekly_sales(self, vendor_id: int, weeks: int = 12) -> Dict[str, Any]:
        """Get weekly sales data for the last N weeks."""
        self._ensure_sample_data(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(weeks=weeks)

        weekly = self.db.query(
            func.date_trunc("week", Order.created_at).label("week_start"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start_date,
        ).group_by(func.date_trunc("week", Order.created_at)).order_by(
            func.date_trunc("week", Order.created_at)
        ).all()

        weekly_data = []
        for row in weekly:
            weekly_data.append({
                "week_start": row.week_start.isoformat() if hasattr(row.week_start, 'isoformat') else str(row.week_start),
                "orders": row.order_count,
                "revenue": float(row.revenue or 0),
            })

        total_revenue = sum(w["revenue"] for w in weekly_data)
        total_orders = sum(w["orders"] for w in weekly_data)

        # Calculate growth
        growth = 0
        if len(weekly_data) >= 2:
            prev_avg = sum(w["revenue"] for w in weekly_data[:len(weekly_data)//2]) / max(1, len(weekly_data)//2)
            curr_avg = sum(w["revenue"] for w in weekly_data[len(weekly_data)//2:]) / max(1, len(weekly_data) - len(weekly_data)//2)
            growth = round((curr_avg - prev_avg) / prev_avg * 100, 1) if prev_avg > 0 else 0

        return {
            "vendor_id": vendor_id,
            "period": f"last_{weeks}_weeks",
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "weekly_average_revenue": round(total_revenue / max(1, weeks), 2),
            "weekly_average_orders": round(total_orders / max(1, weeks), 1),
            "growth_percentage": growth,
            "weekly_data": weekly_data,
        }

    # ── Monthly Sales ──────────────────────────────────────────────────────

    def get_monthly_sales(self, vendor_id: int, months: int = 12) -> Dict[str, Any]:
        """Get monthly sales data for the last N months."""
        self._ensure_sample_data(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=30 * months)

        monthly = self.db.query(
            func.date_trunc("month", Order.created_at).label("month_start"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start_date,
        ).group_by(func.date_trunc("month", Order.created_at)).order_by(
            func.date_trunc("month", Order.created_at)
        ).all()

        monthly_data = []
        for row in monthly:
            monthly_data.append({
                "month": row.month_start.strftime("%B %Y") if hasattr(row.month_start, 'strftime') else str(row.month_start),
                "orders": row.order_count,
                "revenue": float(row.revenue or 0),
            })

        total_revenue = sum(m["revenue"] for m in monthly_data)
        total_orders = sum(m["orders"] for m in monthly_data)

        return {
            "vendor_id": vendor_id,
            "period": f"last_{months}_months",
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "monthly_average_revenue": round(total_revenue / max(1, months), 2),
            "monthly_average_orders": round(total_orders / max(1, months), 1),
            "monthly_data": monthly_data,
        }

    # ── Yearly Sales ───────────────────────────────────────────────────────

    def get_yearly_sales(self, vendor_id: int) -> Dict[str, Any]:
        """Get yearly sales data."""
        self._ensure_sample_data(vendor_id)

        yearly = self.db.query(
            extract("year", Order.created_at).label("year"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
        ).group_by(extract("year", Order.created_at)).order_by(
            extract("year", Order.created_at)
        ).all()

        yearly_data = []
        for row in yearly:
            yearly_data.append({
                "year": int(row.year),
                "orders": row.order_count,
                "revenue": float(row.revenue or 0),
            })

        total_revenue = sum(y["revenue"] for y in yearly_data)
        total_orders = sum(y["orders"] for y in yearly_data)

        return {
            "vendor_id": vendor_id,
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "years_analyzed": len(yearly_data),
            "yearly_data": yearly_data,
        }

    # ── Peak Hour Analysis ─────────────────────────────────────────────────

    def get_peak_hour_analysis(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze order distribution by hour of day."""
        self._ensure_sample_data(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=90)

        hourly = self.db.query(
            extract("hour", Order.created_at).label("hour"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start_date,
        ).group_by(extract("hour", Order.created_at)).order_by(
            extract("hour", Order.created_at)
        ).all()

        hourly_data = []
        hour_map = {}

        for row in hourly:
            hour = int(row.hour)
            hour_map[hour] = {
                "orders": row.order_count,
                "revenue": float(row.revenue or 0),
            }

        for hour in range(24):
            data = hour_map.get(hour, {"orders": 0, "revenue": 0})
            hourly_data.append({
                "hour": f"{hour}:00",
                "orders": data["orders"],
                "revenue": round(data["revenue"], 2),
                "is_peak": data["orders"] > 5,
            })

        total_orders = sum(h["orders"] for h in hourly_data)
        peak_hours = [h for h in hourly_data if h["is_peak"]]
        busiest = max(hourly_data, key=lambda h: h["orders"]) if hourly_data else None

        return {
            "vendor_id": vendor_id,
            "total_orders_analyzed": total_orders,
            "peak_hours_count": len(peak_hours),
            "busiest_hour": busiest["hour"] if busiest else None,
            "hourly_distribution": hourly_data,
            "peak_periods": [
                {"label": f"{h['hour']} - {int(h['hour'].split(':')[0])+1}:00", "orders": h["orders"]}
                for h in peak_hours
            ],
        }

    # ── Popular Items ──────────────────────────────────────────────────────

    def get_item_analysis(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze item sales performance."""
        self._ensure_sample_data(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=90)

        items = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            func.count(OrderItem.id).label("order_count"),
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.price * OrderItem.quantity).label("total_revenue"),
        ).join(
            OrderItem, OrderItem.menu_item_id == MenuItem.id
        ).join(
            Order, Order.id == OrderItem.order_id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            Order.status != OrderStatus.CANCELLED,
            Order.created_at >= start_date,
        ).group_by(
            MenuItem.id, MenuItem.name, MenuItem.price
        ).order_by(
            func.count(OrderItem.id).desc()
        ).all()

        total_orders = sum(i.order_count for i in items) or 1
        popular = []
        low_selling = []

        for item in items:
            percentage = round(item.order_count / total_orders * 100, 1)
            entry = {
                "item_id": item.id,
                "name": item.name,
                "price": float(item.price),
                "order_count": item.order_count,
                "total_quantity": item.total_quantity,
                "total_revenue": float(item.total_revenue or 0),
                "percentage": percentage,
            }
            if percentage > 5:
                popular.append(entry)
            else:
                low_selling.append(entry)

        return {
            "vendor_id": vendor_id,
            "total_items_analyzed": len(items),
            "popular_items": popular[:10],
            "low_selling_items": low_selling[:10],
            "top_item": popular[0]["name"] if popular else None,
        }

    # ── Food Waste Analysis ────────────────────────────────────────────────

    def get_food_waste_analysis(self, vendor_id: int) -> Dict[str, Any]:
        """Analyze potential food waste from cancelled orders."""
        self._ensure_sample_data(vendor_id)

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=90)

        # Cancelled orders
        cancelled = self.db.query(
            func.count(Order.id).label("count"),
            func.sum(Order.total_amount).label("wasted_revenue"),
        ).filter(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= start_date,
        ).first()

        total = self.db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor_id,
            Order.created_at >= start_date,
        ).scalar() or 1

        cancelled_count = cancelled.count or 0
        wasted_revenue = float(cancelled.wasted_revenue or 0)
        cancellation_rate = round(cancelled_count / total * 100, 1)

        # Items most often cancelled
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
            Order.created_at >= start_date,
        ).group_by(MenuItem.name).order_by(
            func.count(OrderItem.id).desc()
        ).limit(5).all()

        return {
            "vendor_id": vendor_id,
            "period": "last_90_days",
            "total_orders": total,
            "cancelled_orders": cancelled_count,
            "cancellation_rate": cancellation_rate,
            "wasted_revenue": round(wasted_revenue, 2),
            "wasted_items": [
                {"name": item.name, "cancelled_count": item.cancelled_count}
                for item in wasted_items
            ],
            "daily_waste_average": round(wasted_revenue / 90, 2),
        }

    # ── Revenue Trends ────────────────────────────────────────────────────

    def get_revenue_trends(self, vendor_id: int) -> Dict[str, Any]:
        """Get revenue trend analysis."""
        self._ensure_sample_data(vendor_id)

        daily = self.get_daily_sales(vendor_id, 90)
        weekly = self.get_weekly_sales(vendor_id, 12)
        monthly = self.get_monthly_sales(vendor_id, 12)

        # Calculate growth rates
        daily_data = daily["sales_data"]
        weekly_data = weekly["weekly_data"]
        monthly_data = monthly["monthly_data"]

        return {
            "vendor_id": vendor_id,
            "daily": daily,
            "weekly": weekly,
            "monthly": monthly,
            "summary": {
                "daily_average_revenue": daily["daily_average_revenue"],
                "weekly_average_revenue": weekly["weekly_average_revenue"],
                "monthly_average_revenue": monthly["monthly_average_revenue"],
                "weekly_growth": weekly.get("growth_percentage", 0),
                "total_revenue_all_time": daily["total_revenue"],
            },
        }

    # ── Full Analytics Dashboard ────────────────────────────────────────────

    def get_full_analytics(self, vendor_id: int) -> Dict[str, Any]:
        """Get complete analytics dashboard data."""
        return {
            "vendor_id": vendor_id,
            "daily_sales": self.get_daily_sales(vendor_id, 30),
            "weekly_sales": self.get_weekly_sales(vendor_id, 12),
            "monthly_sales": self.get_monthly_sales(vendor_id, 12),
            "yearly_sales": self.get_yearly_sales(vendor_id),
            "peak_hour_analysis": self.get_peak_hour_analysis(vendor_id),
            "item_analysis": self.get_item_analysis(vendor_id),
            "food_waste_analysis": self.get_food_waste_analysis(vendor_id),
            "revenue_trends": self.get_revenue_trends(vendor_id),
        }

    # ── Export Functions ───────────────────────────────────────────────────

    def export_csv(self, vendor_id: int, report_type: str) -> str:
        """Export analytics data as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "daily":
            data = self.get_daily_sales(vendor_id, 30)
            writer.writerow(["Date", "Orders", "Revenue"])
            for d in data["sales_data"]:
                writer.writerow([d["date"], d["orders"], d["revenue"]])

        elif report_type == "weekly":
            data = self.get_weekly_sales(vendor_id, 12)
            writer.writerow(["Week Start", "Orders", "Revenue"])
            for w in data["weekly_data"]:
                writer.writerow([w["week_start"], w["orders"], w["revenue"]])

        elif report_type == "monthly":
            data = self.get_monthly_sales(vendor_id, 12)
            writer.writerow(["Month", "Orders", "Revenue"])
            for m in data["monthly_data"]:
                writer.writerow([m["month"], m["orders"], m["revenue"]])

        elif report_type == "items":
            data = self.get_item_analysis(vendor_id)
            writer.writerow(["Item", "Price", "Orders", "Quantity", "Revenue", "Percentage"])
            for item in data["popular_items"]:
                writer.writerow([item["name"], item["price"], item["order_count"], item["total_quantity"], item["total_revenue"], item["percentage"]])

        elif report_type == "peak_hours":
            data = self.get_peak_hour_analysis(vendor_id)
            writer.writerow(["Hour", "Orders", "Revenue", "Is Peak"])
            for h in data["hourly_distribution"]:
                writer.writerow([h["hour"], h["orders"], h["revenue"], h["is_peak"]])

        return output.getvalue()