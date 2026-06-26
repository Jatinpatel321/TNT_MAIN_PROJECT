"""ML Dataset Builder — Extracts training datasets directly from PostgreSQL.

PHASE 1-2: Data Source Discovery + Feature Engineering
Uses real production database records only. No mock data, no synthetic datasets.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import func, text, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot
from app.modules.users.model import User
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.feedback.model import Feedback, VendorReview

logger = logging.getLogger("tnt.ml.dataset")

# ── Academic Calendar (Parul University) ──────────────────────────────────────
# Real academic periods based on typical Indian university schedule
# These are holiday dates that affect campus order volumes

ACADEMIC_PERIODS = [
    {"name": "summer_vacation", "start": "06-01", "end": "07-15"},
    {"name": "diwali_break", "start": "10-20", "end": "11-05"},
    {"name": "winter_break", "start": "12-20", "end": "01-05"},
    {"name": "holi_break", "start": "03-10", "end": "03-20"},
    {"name": "exam_week", "start": "04-15", "end": "04-30"},
]

# Major Indian holidays that impact campus
PUBLIC_HOLIDAYS = [
    ("01-26", "Republic Day"),
    ("08-15", "Independence Day"),
    ("10-02", "Gandhi Jayanti"),
    ("01-01", "New Year"),
]


class DatasetBuilder:
    """Builds ML training datasets directly from PostgreSQL using pure SQL/ORM queries."""

    def __init__(self, db: Session):
        self.db = db

    # ── PHASE 1: Data Source Discovery ──────────────────────────────────────

    def get_data_source_inventory(self) -> Dict[str, Any]:
        """Inventory all available data sources with row counts and date ranges."""
        inventory = {}

        # Orders
        order_count = self.db.query(func.count(Order.id)).scalar() or 0
        order_min_date = self.db.query(func.min(Order.created_at)).scalar()
        order_max_date = self.db.query(func.max(Order.created_at)).scalar()
        inventory["orders"] = {
            "table": "orders",
            "rows": order_count,
            "min_date": str(order_min_date) if order_min_date else None,
            "max_date": str(order_max_date) if order_max_date else None,
            "columns": [
                "id", "user_id", "vendor_id", "slot_id",
                "status", "total_amount", "created_at",
                "eta_minutes", "actual_completion_minutes",
            ],
        }

        # Order Items
        item_count = self.db.query(func.count(OrderItem.id)).scalar() or 0
        inventory["order_items"] = {
            "table": "order_items",
            "rows": item_count,
            "columns": ["id", "order_id", "menu_item_id", "quantity", "price_at_time"],
        }

        # Menu Items
        menu_count = self.db.query(func.count(MenuItem.id)).scalar() or 0
        inventory["menu_items"] = {
            "table": "menu_items",
            "rows": menu_count,
            "columns": [
                "id", "vendor_id", "name", "description",
                "price", "is_available", "category",
                "prep_time_minutes", "available_quantity",
            ],
        }

        # Slots
        slot_count = self.db.query(func.count(Slot.id)).scalar() or 0
        inventory["slots"] = {
            "table": "slots",
            "rows": slot_count,
            "columns": [
                "id", "vendor_id", "start_time", "end_time",
                "max_orders", "current_orders", "status",
            ],
        }

        # Users (vendors only for vendor features)
        vendor_count = self.db.query(func.count(User.id)).filter(
            User.role == "vendor"
        ).scalar() or 0
        inventory["vendors"] = {
            "table": "users (role=vendor)",
            "rows": vendor_count,
            "columns": ["id", "name", "phone", "is_approved", "is_active"],
        }

        # Payments
        payment_count = self.db.query(func.count(Payment.id)).scalar() or 0
        inventory["payments"] = {
            "table": "payments",
            "rows": payment_count,
            "columns": [
                "id", "order_id", "amount", "status",
                "razorpay_order_id", "created_at",
            ],
        }

        # Feedback / Reviews
        feedback_count = self.db.query(func.count(Feedback.id)).scalar() or 0
        inventory["feedback"] = {
            "table": "feedback",
            "rows": feedback_count,
            "columns": [
                "id", "order_id", "vendor_id", "user_id",
                "overall_rating", "quality_rating",
                "time_rating", "behavior_rating",
            ],
        }

        review_count = self.db.query(func.count(VendorReview.id)).scalar() or 0
        inventory["vendor_reviews"] = {
            "table": "vendor_reviews",
            "rows": review_count,
            "columns": ["id", "vendor_id", "user_id", "rating", "review_text"],
        }

        return inventory

    # ── PHASE 2: Feature Engineering ────────────────────────────────────────

    def build_eta_dataset(self, days: int = 90) -> pd.DataFrame:
        """Build ETA prediction training dataset directly from orders table.
        
        Target: actual_completion_minutes (actual ETA)
        Features derived from real order data.
        """
        logger.info(f"Building ETA dataset from last {days} days of real orders")

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=days)

        # Query completed/picked orders with actual completion times
        orders = self.db.query(
            Order.id.label("order_id"),
            Order.vendor_id,
            Order.slot_id,
            Order.total_amount,
            Order.eta_minutes,
            Order.actual_completion_minutes,
            Order.created_at,
            Order.status,
            func.date_part('dow', Order.created_at).label("day_of_week"),
            func.date_part('hour', Order.created_at).label("hour_of_day"),
            func.date_part('month', Order.created_at).label("month"),
        ).filter(
            Order.created_at.between(start_date, end_date),
            Order.actual_completion_minutes.isnot(None),  # Only orders with actual times
            Order.status.in_([
                OrderStatus.PICKED, OrderStatus.COMPLETED, OrderStatus.READY,
            ]),
        ).all()

        if not orders:
            logger.warning("No completed orders with actual_completion_minutes found in database")
            # Fall back to all non-cancelled orders with created_at
            orders = self.db.query(
                Order.id.label("order_id"),
                Order.vendor_id,
                Order.slot_id,
                Order.total_amount,
                Order.eta_minutes,
                Order.actual_completion_minutes,
                Order.created_at,
                Order.status,
                func.date_part('dow', Order.created_at).label("day_of_week"),
                func.date_part('hour', Order.created_at).label("hour_of_day"),
                func.date_part('month', Order.created_at).label("month"),
            ).filter(
                Order.created_at.between(start_date, end_date),
                Order.status.notin_([OrderStatus.CANCELLED]),
            ).all()

        logger.info(f"Found {len(orders)} real orders for ETA training")

        rows = []
        for o in orders:
            # Get slot data
            slot = self.db.query(Slot).filter(Slot.id == o.slot_id).first()

            # Get vendor type from menu items
            menu_item = self.db.query(MenuItem).filter(
                MenuItem.vendor_id == o.vendor_id
            ).first()
            vendor_type = menu_item.category if menu_item else "food"

            # Get order item count
            item_count = self.db.query(func.count(OrderItem.id)).filter(
                OrderItem.order_id == o.order_id
            ).scalar() or 1

            # Calculate queue size at time of order
            queue_size = self.db.query(func.count(Order.id)).filter(
                Order.slot_id == o.slot_id,
                Order.id < o.order_id,
                Order.created_at <= o.created_at,
            ).scalar() or 0

            # Academic period / holiday flags
            order_date_str = o.created_at.strftime("%m-%d") if o.created_at else ""
            is_holiday = 0
            holiday_name = None
            for h_date, h_name in PUBLIC_HOLIDAYS:
                if order_date_str == h_date:
                    is_holiday = 1
                    holiday_name = h_name
                    break

            academic_period = "regular"
            for period in ACADEMIC_PERIODS:
                if period["start"] <= order_date_str <= period["end"]:
                    academic_period = period["name"]
                    break

            # Target: actual completion time
            target = o.actual_completion_minutes

            # If no actual completion time, estimate from created_at to pickup
            # by finding the max from order history
            if target is None:
                # Use ETA if available as fallback
                target = o.eta_minutes or 15

            rows.append({
                "order_id": o.order_id,
                "vendor_id": o.vendor_id,
                "slot_id": o.slot_id or 0,
                "vendor_type": 0 if vendor_type == "food" else 1,  # encode
                "order_amount": float(o.total_amount or 0) / 100,  # convert paise to rupees
                "item_count": item_count,
                "day_of_week": int(o.day_of_week or 0),
                "hour_of_day": int(o.hour_of_day or 12),
                "month": int(o.month or 1),
                "queue_size": queue_size,
                "slot_occupancy_pct": (slot.current_orders / max(slot.max_orders, 1) * 100) if slot else 0,
                "is_holiday": is_holiday,
                "is_rush_hour": 1 if 12 <= int(o.hour_of_day or 12) <= 14 or 18 <= int(o.hour_of_day or 12) <= 20 else 0,
                "is_weekend": 1 if int(o.day_of_week or 0) in (0, 6) else 0,
                "academic_period": self._encode_period(academic_period),
                "target_eta_minutes": float(target or 15),
                "eta_minutes": float(o.eta_minutes or 15),
            })

        df = pd.DataFrame(rows)
        df = self._clean_dataset(df, "target_eta_minutes")
        logger.info(f"ETA dataset: {len(df)} rows, {len(df.columns)} features")
        return df

    def build_demand_dataset(self, days: int = 90) -> pd.DataFrame:
        """Build demand forecasting dataset.
        
        Target: orders_per_hour (count of orders grouped by vendor+hour)
        """
        logger.info(f"Building demand forecast dataset from last {days} days")

        end_date = utcnow_naive()
        start_date = end_date - timedelta(days=days)

        # Get hourly order counts per vendor
        hourly = self.db.query(
            Order.vendor_id,
            func.date(Order.created_at).label("order_date"),
            func.date_part('hour', Order.created_at).label("hour"),
            func.date_part('dow', Order.created_at).label("day_of_week"),
            func.date_part('month', Order.created_at).label("month"),
            func.count(Order.id).label("order_count"),
        ).filter(
            Order.created_at.between(start_date, end_date),
            Order.status.notin_([OrderStatus.CANCELLED]),
        ).group_by(
            Order.vendor_id,
            func.date(Order.created_at),
            func.date_part('hour', Order.created_at),
            func.date_part('dow', Order.created_at),
            func.date_part('month', Order.created_at),
        ).all()

        rows = []
        for h in hourly:
            date_str = h.order_date.strftime("%m-%d") if h.order_date else ""
            is_holiday = 1 if any(h_date == date_str for h_date, _ in PUBLIC_HOLIDAYS) else 0

            # Vendor type
            menu_item = self.db.query(MenuItem).filter(
                MenuItem.vendor_id == h.vendor_id
            ).first()
            vendor_type = 0
            if menu_item and menu_item.category == "stationery":
                vendor_type = 1

            # Historical average for this vendor-hour-weekday
            hist_avg = self.db.query(func.avg(Order.id)).filter(
                Order.vendor_id == h.vendor_id,
                func.date_part('hour', Order.created_at) == int(h.hour),
                func.date_part('dow', Order.created_at) == int(h.day_of_week),
                Order.created_at < h.order_date,
            ).scalar() or 0

            academic_period = "regular"
            for period in ACADEMIC_PERIODS:
                if period["start"] <= date_str <= period["end"]:
                    academic_period = period["name"]
                    break

            rows.append({
                "vendor_id": h.vendor_id,
                "hour": int(h.hour or 0),
                "day_of_week": int(h.day_of_week or 0),
                "month": int(h.month or 1),
                "is_holiday": is_holiday,
                "is_rush_hour": 1 if 12 <= int(h.hour or 0) <= 14 or 18 <= int(h.hour or 0) <= 20 else 0,
                "is_weekend": 1 if int(h.day_of_week or 0) in (0, 6) else 0,
                "vendor_type": vendor_type,
                "historical_avg": float(hist_avg),
                "academic_period": self._encode_period(academic_period),
                "target_order_count": h.order_count,
            })

        df = pd.DataFrame(rows)
        df = self._clean_dataset(df, "target_order_count")
        logger.info(f"Demand dataset: {len(df)} rows, {len(df.columns)} features")
        return df

    def build_slot_recommendation_dataset(self, days: int = 90) -> pd.DataFrame:
        """Build slot recommendation dataset.
        
        Target: slot_quality_score (based on actual completion rates and waiting times)
        """
        logger.info("Building slot recommendation dataset from real slot data")

        slots = self.db.query(Slot).all()
        rows = []

        for slot in slots:
            # Get orders for this slot
            slot_orders = self.db.query(Order).filter(
                Order.slot_id == slot.id,
            ).all()

            if not slot_orders:
                continue

            # Calculate metrics from real order data
            completed = sum(1 for o in slot_orders if o.status in (
                OrderStatus.PICKED, OrderStatus.COMPLETED, OrderStatus.READY
            ))
            cancelled = sum(1 for o in slot_orders if o.status == OrderStatus.CANCELLED)
            total = len(slot_orders)

            actual_times = [
                o.actual_completion_minutes for o in slot_orders
                if o.actual_completion_minutes is not None
            ]
            avg_wait = sum(actual_times) / len(actual_times) if actual_times else 15

            # ETA accuracy
            eta_diffs = [
                abs((o.eta_minutes or 15) - (o.actual_completion_minutes or 15))
                for o in slot_orders
                if o.eta_minutes and o.actual_completion_minutes
            ]
            avg_eta_error = sum(eta_diffs) / len(eta_diffs) if eta_diffs else 5

            occupancy_pct = (slot.current_orders / max(slot.max_orders, 1)) * 100
            completion_rate = completed / max(total, 1)
            cancellation_rate = cancelled / max(total, 1)

            # Target: higher is better (composite score)
            quality_score = (
                completion_rate * 0.4 +
                (1 - cancellation_rate) * 0.2 +
                max(0, 1 - avg_wait / 30) * 0.2 +
                max(0, 1 - avg_eta_error / 15) * 0.2
            ) * 100

            rows.append({
                "slot_id": slot.id,
                "vendor_id": slot.vendor_id,
                "hour": slot.start_time.hour if slot.start_time else 12,
                "day_of_week": slot.start_time.weekday() if slot.start_time else 0,
                "max_orders": slot.max_orders,
                "current_orders": slot.current_orders,
                "occupancy_pct": occupancy_pct,
                "completion_rate": completion_rate,
                "cancellation_rate": cancellation_rate,
                "avg_wait_minutes": avg_wait,
                "avg_eta_error_minutes": avg_eta_error,
                "total_orders_served": total,
                "target_quality_score": quality_score,
            })

        df = pd.DataFrame(rows)
        df = self._clean_dataset(df, "target_quality_score")
        logger.info(f"Slot dataset: {len(df)} rows, {len(df.columns)} features")
        return df

    def build_vendor_performance_dataset(self) -> pd.DataFrame:
        """Build vendor performance/ranking dataset.
        
        Target: vendor_performance_score (0-100 based on real metrics)
        """
        logger.info("Building vendor performance dataset from real data")

        vendors = self.db.query(User).filter(
            User.role == "vendor",
            User.is_approved == True,
        ).all()

        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        rows = []
        for vendor in vendors:
            vendor_id = vendor.id

            # Real order metrics
            total_orders = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
            ).scalar() or 0

            recent_orders = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.created_at >= thirty_days_ago,
            ).scalar() or 0

            completed = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.status.in_([OrderStatus.PICKED, OrderStatus.COMPLETED]),
            ).scalar() or 0

            cancelled = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CANCELLED,
            ).scalar() or 0

            # Revenue
            total_revenue = self.db.query(func.sum(Payment.amount)).join(
                Order, Order.id == Payment.order_id
            ).filter(
                Order.vendor_id == vendor_id,
                Payment.status == PaymentStatus.SUCCESS,
            ).scalar() or 0

            # Ratings
            reviews = self.db.query(VendorReview.rating).filter(
                VendorReview.vendor_id == vendor_id,
            ).all()
            avg_rating = sum(r[0] for r in reviews) / len(reviews) if reviews else 3.0

            # Feedback ratings
            feedback = self.db.query(Feedback).filter(
                Feedback.vendor_id == vendor_id,
            ).all()
            avg_quality = sum(f.quality_rating for f in feedback) / len(feedback) if feedback else 3.0
            avg_time = sum(f.time_rating for f in feedback) / len(feedback) if feedback else 3.0

            # Repeat customers
            repeat_customers = self.db.query(
                Order.user_id
            ).filter(
                Order.vendor_id == vendor_id,
            ).group_by(
                Order.user_id
            ).having(
                func.count(Order.id) >= 2
            ).count() or 0

            total_customers = self.db.query(
                func.count(func.distinct(Order.user_id))
            ).filter(
                Order.vendor_id == vendor_id,
            ).scalar() or 1

            # Completion/cancellation rates
            completion_rate = completed / max(total_orders, 1)
            cancellation_rate = cancelled / max(total_orders, 1)
            repeat_rate = repeat_customers / max(total_customers, 1)

            # Average ETA accuracy
            eta_actuals = self.db.query(
                Order.eta_minutes, Order.actual_completion_minutes
            ).filter(
                Order.vendor_id == vendor_id,
                Order.eta_minutes.isnot(None),
                Order.actual_completion_minutes.isnot(None),
            ).all()
            eta_accuracy = 1.0
            if eta_actuals:
                errors = [abs(e - a) for e, a in eta_actuals if e and a]
                avg_error = sum(errors) / len(errors) if errors else 0
                eta_accuracy = max(0, 1 - avg_error / 30)

            # Revenue per order
            revenue_per_order = (total_revenue / 100) / max(total_orders, 1)

            # Composite performance score
            performance_score = (
                completion_rate * 0.25 * 100 +
                (1 - cancellation_rate) * 0.20 * 100 +
                (avg_rating / 5) * 0.20 * 100 +
                repeat_rate * 0.15 * 100 +
                eta_accuracy * 0.10 * 100 +
                min(revenue_per_order / 100, 1) * 0.10 * 100
            )
            performance_score = min(100, max(0, performance_score))

            rows.append({
                "vendor_id": vendor_id,
                "total_orders": total_orders,
                "recent_orders_30d": recent_orders,
                "completed_orders": completed,
                "cancelled_orders": cancelled,
                "completion_rate": completion_rate,
                "cancellation_rate": cancellation_rate,
                "avg_rating": avg_rating,
                "avg_quality_rating": avg_quality,
                "avg_time_rating": avg_time,
                "total_revenue_rs": float(total_revenue) / 100,
                "revenue_per_order_rs": revenue_per_order,
                "repeat_customers": repeat_customers,
                "total_customers": total_customers,
                "repeat_rate": repeat_rate,
                "eta_accuracy": eta_accuracy,
                "target_performance_score": performance_score,
            })

        df = pd.DataFrame(rows)
        df = self._clean_dataset(df, "target_performance_score")
        logger.info(f"Vendor performance dataset: {len(df)} rows, {len(df.columns)} features")
        return df

    def build_recommendation_dataset(self) -> pd.DataFrame:
        """Build recommendation training dataset from real order history.
        
        Used for collaborative filtering and content-based recommendations.
        Each row = user-item interaction.
        """
        logger.info("Building recommendation dataset from real order history")

        thirty_days_ago = utcnow_naive() - timedelta(days=90)

        interactions = self.db.query(
            Order.user_id,
            OrderItem.menu_item_id,
            func.count(OrderItem.id).label("order_count"),
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.max(Order.created_at).label("last_ordered"),
        ).join(
            OrderItem, OrderItem.order_id == Order.id
        ).filter(
            Order.created_at >= thirty_days_ago,
            Order.status.notin_([OrderStatus.CANCELLED]),
        ).group_by(
            Order.user_id, OrderItem.menu_item_id
        ).all()

        rows = []
        for i in interactions:
            menu_item = self.db.query(MenuItem).filter(
                MenuItem.id == i.menu_item_id
            ).first()
            if not menu_item:
                continue

            vendor = self.db.query(User).filter(User.id == menu_item.vendor_id).first()
            vendor_type = menu_item.category or "food"

            rows.append({
                "user_id": i.user_id,
                "item_id": i.menu_item_id,
                "vendor_id": menu_item.vendor_id,
                "item_name": menu_item.name,
                "vendor_name": vendor.name if vendor else f"Vendor {menu_item.vendor_id}",
                "vendor_type": vendor_type,
                "category": menu_item.category or "food",
                "price_paise": menu_item.price or 0,
                "order_count": i.order_count,
                "total_quantity": i.total_quantity,
                "days_since_last": (utcnow_naive() - i.last_ordered).days if i.last_ordered else 90,
                "interaction_strength": i.order_count * i.total_quantity,
            })

        df = pd.DataFrame(rows)
        logger.info(f"Recommendation dataset: {len(df)} interactions, {df['user_id'].nunique()} users, {df['item_id'].nunique()} items")
        return df

    # ── Helper Methods ──────────────────────────────────────────────────────

    def _encode_period(self, period: str) -> int:
        """Encode academic period as integer."""
        mapping = {
            "regular": 0,
            "exam_week": 1,
            "summer_vacation": 2,
            "diwali_break": 3,
            "winter_break": 4,
            "holi_break": 5,
        }
        return mapping.get(period, 0)

    def _clean_dataset(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Clean dataset: handle nulls, duplicates, infinite values."""
        if df.empty:
            return df

        # Remove duplicates
        df = df.drop_duplicates()

        # Remove rows with null target
        df = df.dropna(subset=[target_col])

        # Fill remaining nulls
        for col in df.columns:
            if col == target_col:
                continue
            if df[col].dtype in (np.float64, np.int64, float, int):
                df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 0)
            else:
                df[col] = df[col].fillna("unknown")

        # Remove infinite values
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna()

        # Remove extreme outliers (beyond 5 std devs) for numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col == target_col:
                continue
            mean, std = df[col].mean(), df[col].std()
            if std > 0:
                df = df[df[col].between(mean - 5*std, mean + 5*std)]

        return df

    def get_dataset_statistics(self, df: pd.DataFrame, name: str) -> Dict[str, Any]:
        """Generate comprehensive statistics for a dataset."""
        return {
            "dataset_name": name,
            "rows": len(df),
            "features": len(df.columns),
            "numeric_features": len(df.select_dtypes(include=[np.number]).columns),
            "categorical_features": len(df.select_dtypes(include=["object", "category"]).columns),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "columns": list(df.columns),
            "target_stats": {
                "mean": float(df.iloc[:, -1].mean()) if not df.empty else 0,
                "std": float(df.iloc[:, -1].std()) if not df.empty else 0,
                "min": float(df.iloc[:, -1].min()) if not df.empty else 0,
                "max": float(df.iloc[:, -1].max()) if not df.empty else 0,
            },
            "null_counts": df.isnull().sum().to_dict(),
        }