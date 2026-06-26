"""
fraud_rules.py  –  Lightweight, explainable fraud detection rules.

Each rule is a pure function that receives the current order and relevant
context, then returns either ``None`` (no suspicion) or a human-readable
reason string.

Rules run **after** the order is placed but **before** the response is
returned to the user, so checkout latency is only increased by the time
it takes to query a few historical rows.

Currently implemented rules
---------------------------
1. **Rapid-fire multi-vendor**  –  same user places N orders within M minutes
   across different vendors.
2. **Value outlier**  –  order value > 5× the user's last 10 orders' mean.
3. **Slot-hoarding abuse**  –  repeated cancellations right after slot
   lock-in (2+ cancelled orders in the last 10 minutes by the same user).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderStatus

logger = logging.getLogger("tnt.fraud.rules")

# ── Constants (tunable without a config layer) ──────────────────────────────
RAPID_ORDER_THRESHOLD_COUNT = 3      # N orders
RAPID_ORDER_WINDOW_MINUTES = 15      # M minutes
VALUE_OUTLIER_MULTIPLIER = 5         # × mean of last 10
VALUE_OUTLIER_MIN_SAMPLES = 3        # need at least this many past orders to compare
SLOT_HOARD_WINDOW_MINUTES = 10       # look-back window for cancellations
SLOT_HOARD_MIN_CANCELLATIONS = 2     # minimum recent cancellations


# ── Rule functions ──────────────────────────────────────────────────────────

def check_rapid_multi_vendor(
    order: Order,
    db: Session,
) -> Optional[str]:
    """Rule 1: Same user placing N+ orders within M minutes across different vendors."""
    now = utcnow_naive()
    window_start = now - timedelta(minutes=RAPID_ORDER_WINDOW_MINUTES)

    recent_orders = (
        db.query(Order)
        .filter(
            Order.user_id == order.user_id,
            Order.created_at >= window_start,
            Order.created_at <= now,
            Order.id != order.id,  # exclude the just-placed order
        )
        .all()
    )

    if len(recent_orders) < RAPID_ORDER_THRESHOLD_COUNT - 1:
        return None  # not enough orders to meet the threshold

    # Collect distinct vendor IDs involved
    vendor_ids: set[int] = set()
    for ro in recent_orders:
        vendor_ids.add(ro.vendor_id)

    # Include the current order's vendor
    vendor_ids.add(order.vendor_id)

    # If there are at least 2 different vendors involved, it's suspicious
    if len(vendor_ids) >= 2 and len(recent_orders) >= (RAPID_ORDER_THRESHOLD_COUNT - 1):
        return (
            f"Rapid multi-vendor: user placed {len(recent_orders) + 1} orders "
            f"across {len(vendor_ids)} different vendors within "
            f"{RAPID_ORDER_WINDOW_MINUTES} minutes"
        )

    return None


def check_value_outlier(
    order: Order,
    db: Session,
) -> Optional[str]:
    """Rule 2: Order value far outside the user's historical average."""
    past_orders = (
        db.query(func.coalesce(func.avg(Order.total_amount), 0.0))
        .filter(
            Order.user_id == order.user_id,
            Order.id != order.id,
            Order.total_amount > 0,
            Order.status != OrderStatus.CANCELLED,
        )
        .order_by(Order.created_at.desc())
        .limit(VALUE_OUTLIER_MIN_SAMPLES)
        .all()
    )

    # Need at least VALUE_OUTLIER_MIN_SAMPLES historical non-zero amounts
    past_amounts = [r[0] for r in past_orders if r[0] and r[0] > 0]
    if len(past_amounts) < VALUE_OUTLIER_MIN_SAMPLES:
        return None  # insufficient history to judge

    mean = sum(past_amounts) / len(past_amounts)
    current_amount = order.total_amount or 0

    if mean > 0 and current_amount > mean * VALUE_OUTLIER_MULTIPLIER:
        return (
            f"Value outlier: order amount ₹{current_amount / 100:.0f} is "
            f"{current_amount / mean:.1f}× the user's historical average "
            f"of ₹{mean / 100:.0f} (threshold: {VALUE_OUTLIER_MULTIPLIER}×)"
        )

    return None


def check_slot_hoarding(
    order: Order,
    db: Session,
) -> Optional[str]:
    """Rule 3: Repeated cancellations right after slot lock-in.

    We look at: has this user cancelled 2+ *other* orders in the last N
    minutes?  Slot lock-in happens when an order is placed (the slot capacity
    is consumed).  A pattern of place → cancel → place → cancel suggests
    slot hoarding.
    """
    now = utcnow_naive()
    window_start = now - timedelta(minutes=SLOT_HOARD_WINDOW_MINUTES)

    recent_cancellations = (
        db.query(Order)
        .filter(
            Order.user_id == order.user_id,
            Order.status == OrderStatus.CANCELLED,
            Order.created_at >= window_start,
            Order.created_at <= now,
            Order.id != order.id,
        )
        .count()
    )

    if recent_cancellations >= SLOT_HOARD_MIN_CANCELLATIONS:
        return (
            f"Slot-hoarding abuse: user cancelled {recent_cancellations} orders "
            f"within the last {SLOT_HOARD_WINDOW_MINUTES} minutes, "
            f"suggesting slot lock-in abuse"
        )

    return None


# ── Public API ──────────────────────────────────────────────────────────────

def run_fraud_checks(
    order: Order,
    db: Session,
) -> Optional[str]:
    """Run all configured fraud rules against *order*.

    Returns the **first** matching reason, or ``None`` if the order passes
    all checks.  Early-exit on first hit avoids spamming multiple reasons
    at once.
    """
    checks = [
        check_rapid_multi_vendor,
        check_value_outlier,
        check_slot_hoarding,
    ]

    for check in checks:
        try:
            reason = check(order, db)
            if reason:
                logger.info(
                    "fraud_rule_fired order_id=%s user_id=%s reason=%s",
                    order.id, order.user_id, reason,
                )
                return reason
        except Exception:
            logger.exception(
                "fraud_rule_error check=%s order_id=%s user_id=%s",
                check.__name__, order.id, order.user_id,
            )

    return None
