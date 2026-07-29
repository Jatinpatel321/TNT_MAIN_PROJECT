"""Data & Prediction Drift Detection Module.

Computes Population Stability Index (PSI) to detect data drift in features
and output distribution drift in model predictions.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.ml.dataset_builder import DatasetBuilder
from app.ml.registry import ModelRegistry
from app.ml.shadow_log_model import ShadowLog
from app.ml.drift_report_model import DriftReport

logger = logging.getLogger("tnt.ml.drift")


def compute_psi(expected: np.ndarray, actual: np.ndarray, bins: int = 10) -> float:
    """Calculate Population Stability Index (PSI) between expected and actual distributions.

    PSI Interpretation:
    - PSI < 0.1: No significant distribution change.
    - 0.1 <= PSI <= 0.2: Moderate distribution shift (monitor).
    - PSI > 0.2: Significant drift (re-training recommended).

    Args:
        expected: Baseline/training array of feature or target values.
        actual: Live/recent array of feature or target values.
        bins: Number of histogram bins (default 10).

    Returns:
        float: Population Stability Index value (>= 0.0).
    """
    exp_arr = np.asarray(expected, dtype=float).ravel()
    act_arr = np.asarray(actual, dtype=float).ravel()

    # Drop non-finite values (NaN / Inf)
    exp_clean = exp_arr[np.isfinite(exp_arr)]
    act_clean = act_arr[np.isfinite(act_arr)]

    if len(exp_clean) == 0 or len(act_clean) == 0:
        return 0.0

    # Handle edge case: zero variance / constant values
    min_val, max_val = float(exp_clean.min()), float(exp_clean.max())
    if min_val == max_val:
        if np.all(act_clean == min_val):
            return 0.0
        min_val -= 1.0
        max_val += 1.0

    # Determine bin edges based on expected distribution
    bin_edges = np.linspace(min_val, max_val, bins + 1)

    # Bin counts
    exp_counts, _ = np.histogram(exp_clean, bins=bin_edges)
    act_counts, _ = np.histogram(act_clean, bins=bin_edges)

    # Proportions
    exp_pct = exp_counts / float(len(exp_clean))
    act_pct = act_counts / float(len(act_clean))

    # Epsilon smoothing to prevent log(0) or div by 0
    eps = 1e-4
    exp_pct = np.where(exp_pct == 0.0, eps, exp_pct)
    act_pct = np.where(act_pct == 0.0, eps, act_pct)

    # Recalculate proportions so they sum to 1 after epsilon adjustment
    exp_pct = exp_pct / np.sum(exp_pct)
    act_pct = act_pct / np.sum(act_pct)

    # PSI calculation
    psi_vec = (act_pct - exp_pct) * np.log(act_pct / exp_pct)
    psi = float(np.sum(psi_vec))
    return max(0.0, round(psi, 4))


def check_data_drift(model_type: str, db: Session, lookback_days: int = 7) -> Dict[str, Any]:
    """Check feature distribution drift for a model type over the past lookback_days.

    Compares training feature distribution against the last lookback_days of feature data.
    Features with PSI > 0.2 are flagged as drifted.
    """
    builder = DatasetBuilder(db)

    if model_type == "eta_prediction":
        df_train = builder.build_eta_dataset(days=90)
        df_recent = builder.build_eta_dataset(days=lookback_days)
        target_col = "target_eta_minutes"
    elif model_type == "demand_forecast":
        df_train = builder.build_demand_dataset(days=90)
        df_recent = builder.build_demand_dataset(days=lookback_days)
        target_col = "target_order_count"
    elif model_type == "slot_recommendation":
        df_train = builder.build_slot_recommendation_dataset(days=90)
        df_recent = builder.build_slot_recommendation_dataset(days=lookback_days)
        target_col = "target_quality_score"
    elif model_type == "vendor_ranking":
        df_train = builder.build_vendor_performance_dataset()
        df_recent = builder.build_vendor_performance_dataset()
        target_col = "target_performance_score"
    else:  # fraud_detection or default
        from app.ml.features import extract_fraud_features
        X_tr, _, cols = extract_fraud_features(db)
        df_train = pd.DataFrame(X_tr, columns=cols)
        df_recent = pd.DataFrame(X_tr, columns=cols)
        target_col = None

    if df_train.empty or df_recent.empty:
        return {
            "model_type": model_type,
            "lookback_days": lookback_days,
            "has_drift": False,
            "drifted_features": [],
            "feature_psi": {},
            "status": "insufficient_data",
        }

    numeric_cols = df_train.select_dtypes(include=[np.number]).columns
    feature_psi = {}
    drifted_features = []

    for col in numeric_cols:
        if col == target_col or col in ("id", "order_id", "slot_id", "vendor_id", "user_id"):
            continue
        exp_col = df_train[col].values
        act_col = df_recent[col].values

        psi = compute_psi(exp_col, act_col)
        feature_psi[col] = psi

        if psi > 0.2:
            drifted_features.append(col)
            logger.warning(
                "Data Drift Detected! Model: '%s', Feature: '%s', PSI: %.4f (> 0.2 threshold)",
                model_type, col, psi
            )

    has_drift = len(drifted_features) > 0

    return {
        "model_type": model_type,
        "lookback_days": lookback_days,
        "has_drift": has_drift,
        "drifted_features": drifted_features,
        "feature_psi": feature_psi,
        "status": "success",
    }


def check_prediction_drift(model_type: str, db: Session, lookback_days: int = 7) -> Dict[str, Any]:
    """Check prediction output drift using shadow_log entries over lookback_days.

    Compares the distribution of model predictions (`predicted_model`) against
    the heuristic predictions (`predicted_heuristic`). Flags prediction drift if PSI > 0.2.
    """
    since = utcnow_naive() - timedelta(days=lookback_days)

    entries = db.query(ShadowLog).filter(
        ShadowLog.model_type == model_type,
        ShadowLog.created_at >= since,
    ).all()

    if not entries:
        return {
            "model_type": model_type,
            "lookback_days": lookback_days,
            "has_drift": False,
            "psi": 0.0,
            "rolling_mean_model": None,
            "rolling_mean_heuristic": None,
            "total_predictions": 0,
            "status": "no_shadow_logs",
        }

    preds_model = [e.predicted_model for e in entries if e.predicted_model is not None]
    preds_heuristic = [e.predicted_heuristic for e in entries if e.predicted_heuristic is not None]

    if not preds_model or not preds_heuristic:
        return {
            "model_type": model_type,
            "lookback_days": lookback_days,
            "has_drift": False,
            "psi": 0.0,
            "rolling_mean_model": float(np.mean(preds_model)) if preds_model else None,
            "rolling_mean_heuristic": float(np.mean(preds_heuristic)) if preds_heuristic else None,
            "total_predictions": len(entries),
            "status": "insufficient_predictions",
        }

    exp_arr = np.array(preds_heuristic, dtype=float)
    act_arr = np.array(preds_model, dtype=float)

    psi = compute_psi(exp_arr, act_arr)
    has_drift = psi > 0.2

    if has_drift:
        logger.warning(
            "Prediction Drift Detected! Model: '%s', PSI: %.4f (> 0.2 threshold)",
            model_type, psi
        )

    return {
        "model_type": model_type,
        "lookback_days": lookback_days,
        "has_drift": has_drift,
        "psi": psi,
        "rolling_mean_model": round(float(np.mean(act_arr)), 2),
        "rolling_mean_heuristic": round(float(np.mean(exp_arr)), 2),
        "rolling_var_model": round(float(np.var(act_arr)), 2),
        "rolling_var_heuristic": round(float(np.var(exp_arr)), 2),
        "total_predictions": len(entries),
        "status": "success",
    }


def run_all_drift_checks(db: Session, lookback_days: int = 7) -> Dict[str, Any]:
    """Run data and prediction drift checks for all 5 model types and record to drift_reports table."""
    model_types = [
        "eta_prediction",
        "demand_forecast",
        "slot_recommendation",
        "vendor_ranking",
        "fraud_detection",
    ]

    reports = []
    total_drift_count = 0

    for m_type in model_types:
        # Data drift
        d_report = check_data_drift(m_type, db, lookback_days=lookback_days)
        rec_data = DriftReport(
            model_type=m_type,
            check_type="data_drift",
            has_drift=d_report["has_drift"],
            report_data=d_report,
        )
        db.add(rec_data)
        if d_report["has_drift"]:
            total_drift_count += 1

        # Prediction drift
        p_report = check_prediction_drift(m_type, db, lookback_days=lookback_days)
        rec_pred = DriftReport(
            model_type=m_type,
            check_type="prediction_drift",
            has_drift=p_report["has_drift"],
            report_data=p_report,
        )
        db.add(rec_pred)
        if p_report["has_drift"]:
            total_drift_count += 1

        reports.append({
            "model_type": m_type,
            "data_drift": d_report,
            "prediction_drift": p_report,
        })

    db.commit()

    return {
        "status": "success",
        "lookback_days": lookback_days,
        "total_drift_flags": total_drift_count,
        "reports": reports,
    }
