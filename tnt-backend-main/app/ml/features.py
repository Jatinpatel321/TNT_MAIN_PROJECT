"""Feature engineering pipelines for all ML models.

Extracts features from the database for ETA prediction, demand forecasting,
fraud detection, vendor ranking, and slot recommendations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot, SlotBooking
from app.modules.users.model import User
from app.modules.menu.model import MenuItem
from app.modules.feedback.model import VendorReview

logger = logging.getLogger("tnt.ml.features")

ETA_FEATURE_NAMES = [
    "vendor_id", "queue_length", "slot_occupancy",
    "item_count", "time_of_day", "weekday", "rush_hour",
]

RUSH_HOURS_MORNING = (8, 10)
RUSH_HOURS_LUNCH = (12, 14)
RUSH_HOURS_DINNER = (18, 20)


def is_rush_hour(dt: datetime) -> bool:
    h = dt.hour
    return (RUSH_HOURS_MORNING[0] <= h <= RUSH_HOURS_MORNING[1] or
            RUSH_HOURS_LUNCH[0] <= h <= RUSH_HOURS_LUNCH[1] or
            RUSH_HOURS_DINNER[0] <= h <= RUSH_HOURS_DINNER[1])


# ── ETA Prediction Features ─────────────────────────────────────────────

def extract_eta_features(db: Session, order_id: Optional[int] = None,
                         vendor_id: Optional[int] = None,
                         slot_id: Optional[int] = None) -> list[dict[str, Any]]:
    """Extract feature vectors for ETA prediction.

    Returns list of dicts (one per order) with:
        vendor, queue_length, slot_occupancy, item_count,
        time_of_day, weekday, rush_hour, target_eta (if available)
    """
    query = db.query(
        Order.id, Order.vendor_id, Order.slot_id, Order.created_at,
        Order.eta_minutes, Order.actual_completion_minutes,
        Slot.current_orders, Slot.max_orders,
    ).join(Slot, Order.slot_id == Slot.id)

    if order_id:
        query = query.filter(Order.id == order_id)
    if vendor_id:
        query = query.filter(Order.vendor_id == vendor_id)
    if slot_id:
        query = query.filter(Order.slot_id == slot_id)

    rows = query.all()
    features = []

    for row in rows:
        created = row.created_at or utcnow_naive()
        item_count = db.query(func.sum(OrderItem.quantity)).filter(
            OrderItem.order_id == row.id
        ).scalar() or 1

        features.append({
            "order_id": row.id,
            "vendor_id": row.vendor_id,
            "slot_id": row.slot_id,
            "queue_length": row.current_orders,
            "slot_occupancy": row.current_orders / max(row.max_orders, 1),
            "item_count": int(item_count),
            "time_of_day": created.hour,
            "weekday": created.weekday(),
            "rush_hour": 1 if is_rush_hour(created) else 0,
            "target_eta": row.actual_completion_minutes if row.actual_completion_minutes else None,
        })

    return features


def extract_eta_training_data(db: Session, days: int = 90) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract full training matrix for ETA prediction.

    Returns:
        X: numpy array of shape (n_samples, n_features)
        y: numpy array of target values (actual completion minutes)
        feature_names: list of column names
    """
    since = utcnow_naive() - timedelta(days=days)
    rows = db.query(
        Order.id, Order.vendor_id, Order.slot_id, Order.created_at,
        Order.actual_completion_minutes,
        Slot.current_orders, Slot.max_orders,
    ).join(Slot, Order.slot_id == Slot.id).filter(
        Order.created_at >= since,
        Order.actual_completion_minutes.isnot(None),
        Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED, OrderStatus.READY]),
    ).all()

    X_list, y_list = [], []
    for row in rows:
        created = row.created_at or utcnow_naive()
        item_count = db.query(func.sum(OrderItem.quantity)).filter(
            OrderItem.order_id == row.id
        ).scalar() or 1

        X_list.append([
            float(row.vendor_id),
            float(row.current_orders),
            float(row.current_orders / max(row.max_orders, 1)),
            float(item_count),
            float(created.hour),
            float(created.weekday()),
            float(1 if is_rush_hour(created) else 0),
        ])
        y_list.append(float(row.actual_completion_minutes))

    feature_names = [
        "vendor_id", "queue_length", "slot_occupancy",
        "item_count", "time_of_day", "weekday", "rush_hour",
    ]

    return np.array(X_list), np.array(y_list), feature_names


# ── Demand Forecasting Features ─────────────────────────────────────────

def extract_demand_features(db: Session, vendor_id: int,
                            days: int = 90) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract time-series features for demand forecasting.

    Returns hourly/daily aggregated order counts with temporal features.
    """
    since = utcnow_naive() - timedelta(days=days)

    hourly_counts = db.query(
        func.date_trunc("hour", Order.created_at).label("hour_bucket"),
        func.count(Order.id).label("order_count"),
    ).filter(
        Order.vendor_id == vendor_id,
        Order.created_at >= since,
        Order.status.notin_([OrderStatus.CANCELLED]),
    ).group_by(
        func.date_trunc("hour", Order.created_at)
    ).order_by(
        func.date_trunc("hour", Order.created_at)
    ).all()

    X_list, y_list = [], []
    for row in hourly_counts:
        bucket = row.hour_bucket
        if isinstance(bucket, str):
            bucket = datetime.fromisoformat(bucket)
        X_list.append([
            float(bucket.hour),
            float(bucket.weekday()),
            float(bucket.day),
            float(bucket.month),
            float(1 if is_rush_hour(bucket) else 0),
        ])
        y_list.append(float(row.order_count))

    feature_names = ["hour", "weekday", "day_of_month", "month", "rush_hour"]
    return np.array(X_list), np.array(y_list), feature_names


# ── Fraud Detection Features ─────────────────────────────────────────────

def extract_fraud_features(db: Session,
                           user_id: Optional[int] = None) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract features for fraud detection.

    Features: order frequency, cancellation rate, payment failures,
    account age, amount anomalies, device token presence.
    """
    thirty_days_ago = utcnow_naive() - timedelta(days=30)

    users = db.query(User).filter(User.role.in_(["student", "faculty"]))
    if user_id:
        users = users.filter(User.id == user_id)

    X_list, y_list = [], []
    for user in users.all():
        total_orders = db.query(func.count(Order.id)).filter(
            Order.user_id == user.id, Order.created_at >= thirty_days_ago
        ).scalar() or 0

        cancelled_orders = db.query(func.count(Order.id)).filter(
            Order.user_id == user.id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        total_amount = db.query(func.sum(Order.total_amount)).filter(
            Order.user_id == user.id, Order.created_at >= thirty_days_ago
        ).scalar() or 0

        fraud_flagged = db.query(func.count(Order.id)).filter(
            Order.user_id == user.id, Order.fraud_flag == True
        ).scalar() or 0

        cancel_rate = cancelled_orders / max(total_orders, 1)
        avg_amount = total_amount / max(total_orders, 1) if total_orders > 0 else 0

        has_device_token = 1 if user.device_token else 0

        X_list.append([
            float(total_orders),
            float(cancelled_orders),
            float(cancel_rate),
            float(avg_amount),
            float(has_device_token),
            float(fraud_flagged),
        ])
        y_list.append(float(fraud_flagged > 0))

    feature_names = [
        "total_orders_30d", "cancelled_orders_30d", "cancel_rate",
        "avg_amount", "has_device_token", "fraud_flagged_count",
    ]
    return np.array(X_list), np.array(y_list), feature_names


# ── Vendor Ranking Features ──────────────────────────────────────────────

def extract_vendor_ranking_features(db: Session) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract features for vendor ranking."""
    thirty_days_ago = utcnow_naive() - timedelta(days=30)

    vendors = db.query(User).filter(
        User.role == "vendor", User.is_approved == True
    ).all()

    X_list, y_list = [], []
    for vendor in vendors:
        total_orders = db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor.id, Order.created_at >= thirty_days_ago
        ).scalar() or 0

        completed = db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor.id,
            Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED, OrderStatus.READY]),
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        cancelled = db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor.id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        repeat_customers = db.query(
            Order.user_id, func.count(Order.id)
        ).filter(
            Order.vendor_id == vendor.id, Order.created_at >= thirty_days_ago
        ).group_by(Order.user_id).having(func.count(Order.id) > 1).count()

        unique_customers = db.query(Order.user_id).filter(
            Order.vendor_id == vendor.id, Order.created_at >= thirty_days_ago
        ).distinct().count()

        avg_rating = db.query(func.avg(VendorReview.rating)).filter(
            VendorReview.vendor_id == vendor.id
        ).scalar() or 0.0

        refunds = db.query(func.count(Order.id)).filter(
            Order.vendor_id == vendor.id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        completion_rate = completed / max(total_orders, 1)
        repeat_rate = repeat_customers / max(unique_customers, 1)

        X_list.append([
            float(completion_rate),
            float(avg_rating),
            float(repeat_rate),
            float(cancelled),
            float(refunds),
            float(total_orders),
        ])
        y_list.append(float(completion_rate))

    feature_names = [
        "completion_rate", "avg_rating", "repeat_customer_rate",
        "cancellations", "refunds", "total_orders",
    ]
    return np.array(X_list), np.array(y_list), feature_names


# ── Slot Recommendation Features ─────────────────────────────────────────

def extract_slot_features(db: Session) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Extract features for slot recommendation."""
    slots = db.query(Slot).filter(Slot.status != "blocked").all()

    X_list, y_list = [], []
    for slot in slots:
        avg_completion = db.query(func.avg(Order.actual_completion_minutes)).filter(
            Order.slot_id == slot.id,
            Order.actual_completion_minutes.isnot(None),
        ).scalar() or 15.0

        occupancy = slot.current_orders / max(slot.max_orders, 1)
        hour = slot.start_time.hour
        weekday = slot.start_time.weekday()

        X_list.append([
            float(occupancy),
            float(hour),
            float(weekday),
            float(1 if is_rush_hour(slot.start_time) else 0),
            float(avg_completion),
            float(slot.max_orders),
        ])
        y_list.append(float(occupancy))

    feature_names = [
        "occupancy", "hour", "weekday", "rush_hour",
        "avg_completion_minutes", "max_capacity",
    ]
    return np.array(X_list), np.array(y_list), feature_names


# ── Recommendation / Collaborative Filtering Features ────────────────────

def build_user_item_matrix(db: Session) -> dict[str, Any]:
    """Build user-item interaction matrix for collaborative filtering.

    Returns:
        Dict with user_ids, item_ids, and interaction matrix data.
    """
    thirty_days_ago = utcnow_naive() - timedelta(days=90)
    interactions = db.query(
        Order.user_id, OrderItem.menu_item_id,
        func.sum(OrderItem.quantity).label("total_qty"),
    ).join(OrderItem, OrderItem.order_id == Order.id).filter(
        Order.created_at >= thirty_days_ago,
        Order.status.notin_([OrderStatus.CANCELLED]),
    ).group_by(Order.user_id, OrderItem.menu_item_id).all()

    user_ids = sorted(set(r.user_id for r in interactions))
    item_ids = sorted(set(r.menu_item_id for r in interactions))
    user_idx = {uid: i for i, uid in enumerate(user_ids)}
    item_idx = {iid: j for j, iid in enumerate(item_ids)}

    matrix = np.zeros((len(user_ids), len(item_ids)))
    for r in interactions:
        i, j = user_idx[r.user_id], item_idx[r.menu_item_id]
        matrix[i, j] = float(r.total_qty)

    return {
        "user_ids": user_ids,
        "item_ids": item_ids,
        "user_idx": user_idx,
        "item_idx": item_idx,
        "matrix": matrix,
    }
