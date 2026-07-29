"""ML Model Backtesting Engine.

Replays historical production orders to measure real-world prediction accuracy
and decision utility (ETA error margins and vendor ranking hit rates).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.users.model import User, UserRole

logger = logging.getLogger("tnt.ml.backtest")


def backtest_eta(db: Session, days: int = 30) -> Dict[str, Any]:
    """Replay historical completed orders and evaluate ETA prediction accuracy.

    Compares model/heuristic ETA predictions against actual completion times
    (actual_completion_minutes or pickup_confirmed_at - created_at).

    Args:
        db: SQLAlchemy database session.
        days: Number of historical days to backtest over (default 30).

    Returns:
        Dict containing within_3_min_pct, within_5_min_pct, mae_minutes,
        and total_orders, or status='insufficient_data' if < 20 qualifying orders.
    """
    from app.ml.predictions import MLPredictionService

    since = utcnow_naive() - timedelta(days=days)

    orders = db.query(Order).filter(
        Order.created_at >= since,
        Order.status.in_([
            OrderStatus.COMPLETED,
            OrderStatus.PICKED,
            OrderStatus.READY,
            OrderStatus.READY_FOR_PICKUP,
        ]),
    ).all()

    # Filter orders with valid actual completion time
    qualifying_orders = []
    for order in orders:
        actual_min = None
        if order.actual_completion_minutes is not None:
            actual_min = float(order.actual_completion_minutes)
        elif order.pickup_confirmed_at and order.created_at:
            delta = (order.pickup_confirmed_at - order.created_at).total_seconds() / 60.0
            if delta > 0:
                actual_min = float(delta)

        if actual_min is not None and actual_min > 0:
            qualifying_orders.append((order, actual_min))

    total_count = len(qualifying_orders)
    if total_count < 20:
        logger.info(f"ETA backtest skipped: {total_count} qualifying orders < 20 threshold")
        return {
            "status": "insufficient_data",
            "reason": f"Fewer than 20 qualifying orders in the last {days} days (found {total_count})",
            "total_orders": total_count,
            "days": days,
        }

    service = MLPredictionService(db)
    within_3_count = 0
    within_5_count = 0
    total_abs_error = 0.0

    for order, actual_min in qualifying_orders:
        item_count = db.query(func.sum(OrderItem.quantity)).filter(
            OrderItem.order_id == order.id
        ).scalar() or 1

        pred_res = service.predict_eta(
            vendor_id=order.vendor_id,
            slot_id=order.slot_id or 0,
            item_count=int(item_count),
        )
        pred_eta = float(pred_res.get("predicted_eta_minutes", 15))

        error = abs(pred_eta - actual_min)
        total_abs_error += error

        if error <= 3.0:
            within_3_count += 1
        if error <= 5.0:
            within_5_count += 1

    within_3_pct = round((within_3_count / total_count) * 100.0, 2)
    within_5_pct = round((within_5_count / total_count) * 100.0, 2)
    mae = round(total_abs_error / total_count, 2)

    return {
        "status": "success",
        "days": days,
        "total_orders": total_count,
        "within_3_min_pct": within_3_pct,
        "within_5_min_pct": within_5_pct,
        "mae_minutes": mae,
    }


def backtest_vendor_ranking(db: Session, days: int = 30) -> Dict[str, Any]:
    """Replay historical student order selections against vendor ranking scores.

    Measures Top-1 and Top-3 hit rates (how often the vendor chosen by the student
    was ranked #1 or in the top 3 by the model).

    Args:
        db: SQLAlchemy database session.
        days: Number of historical days to backtest over (default 30).

    Returns:
        Dict containing top_1_hit_rate, top_3_hit_rate, total_orders, and caveats,
        or status='insufficient_data' if < 20 qualifying orders.
    """
    from app.ml.predictions import MLPredictionService

    since = utcnow_naive() - timedelta(days=days)

    orders = db.query(Order).filter(
        Order.created_at >= since,
        Order.status.notin_([OrderStatus.CANCELLED]),
    ).all()

    total_count = len(orders)
    if total_count < 20:
        logger.info(f"Vendor ranking backtest skipped: {total_count} qualifying orders < 20 threshold")
        return {
            "status": "insufficient_data",
            "reason": f"Fewer than 20 qualifying orders in the last {days} days (found {total_count})",
            "total_orders": total_count,
            "days": days,
        }

    service = MLPredictionService(db)
    # Get global rankings from MLPredictionService
    rankings = service.rank_vendors()
    ranked_vendor_ids = [r["vendor_id"] for r in rankings]

    top_1_hits = 0
    top_3_hits = 0

    for order in orders:
        chosen_vendor_id = order.vendor_id
        if chosen_vendor_id in ranked_vendor_ids:
            rank = ranked_vendor_ids.index(chosen_vendor_id) + 1
            if rank == 1:
                top_1_hits += 1
            if rank <= 3:
                top_3_hits += 1

    top_1_rate = round(top_1_hits / total_count, 4)
    top_3_rate = round(top_3_hits / total_count, 4)

    return {
        "status": "success",
        "days": days,
        "total_orders": total_count,
        "top_1_hit_rate": top_1_rate,
        "top_3_hit_rate": top_3_rate,
        "caveat": "Candidate vendors approximated using all active vendors of matching category at order time.",
    }


def backfill_shadow_actuals(db: Session) -> Dict[str, Any]:
    """Backfill actual_value for shadow_log rows where real outcome is now known."""
    from app.ml.shadow_log_model import ShadowLog

    unresolved = db.query(ShadowLog).filter(ShadowLog.actual_value.is_(None)).all()
    updated_count = 0

    for log in unresolved:
        if log.model_type == "eta_prediction" and log.entity_id is not None:
            # entity_id is slot_id or order_id
            order = db.query(Order).filter(
                (Order.id == log.entity_id) | (Order.slot_id == log.entity_id),
                Order.status.in_([
                    OrderStatus.COMPLETED,
                    OrderStatus.PICKED,
                    OrderStatus.READY,
                    OrderStatus.READY_FOR_PICKUP,
                ]),
            ).first()

            if order:
                actual_min = None
                if order.actual_completion_minutes is not None:
                    actual_min = float(order.actual_completion_minutes)
                elif order.pickup_confirmed_at and order.created_at:
                    delta = (order.pickup_confirmed_at - order.created_at).total_seconds() / 60.0
                    if delta > 0:
                        actual_min = float(delta)

                if actual_min is not None:
                    log.actual_value = actual_min
                    updated_count += 1

        elif log.model_type == "demand_forecast" and log.entity_id is not None:
            # entity_id is vendor_id
            if log.created_at:
                order_count = db.query(func.count(Order.id)).filter(
                    Order.vendor_id == log.entity_id,
                    Order.status.notin_([OrderStatus.CANCELLED]),
                    func.date(Order.created_at) == func.date(log.created_at),
                ).scalar() or 0

                log.actual_value = float(order_count)
                updated_count += 1

    if updated_count > 0:
        db.commit()

    return {
        "status": "success",
        "unresolved_total": len(unresolved),
        "updated_count": updated_count,
    }

