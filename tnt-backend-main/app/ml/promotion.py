"""
Model Promotion & Automatic Rollback Module — Manages Champion vs Candidate model evaluation and degradation-triggered rollback.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from app.ml.registry import ModelRegistry

logger = logging.getLogger("tnt.ml.promotion")


def _extract_primary_metric(model_type: str, metrics: Dict[str, Any]) -> Tuple[str, float]:
    """
    Extracts the primary metric name and numeric value for a given model_type.
    - Classification (fraud_detection): higher is better (cv_f1, f1, accuracy).
    - Regression (eta, demand, slot, vendor): lower is better (cv_rmse, rmse, mae).
    """
    if not isinstance(metrics, dict):
        metrics = {}

    if model_type == "fraud_detection":
        for k in ["cv_f1", "f1", "accuracy"]:
            val = metrics.get(k)
            if val is not None and isinstance(val, (int, float)):
                return k, float(val)
        return "f1", 0.0
    else:
        for k in ["cv_rmse", "rmse", "mae"]:
            val = metrics.get(k)
            if val is not None and isinstance(val, (int, float)):
                return k, float(val)
        # Fallback for R2 if present (higher R2 is better, translate to inverted metric if needed)
        if "r2" in metrics and isinstance(metrics["r2"], (int, float)):
            return "r2_inverted", 1.0 - float(metrics["r2"])
        return "rmse", float("inf")


def promote_if_better(model_type: str, candidate_version_id: str) -> bool:
    """
    Compares candidate model version against current active champion version.
    - Primary metric: RMSE for regression (lower is better), F1 for classification (higher is better).
    - Tie-breaking: Equal metrics promote candidate (prefers newer retrained model).
    - Promotes candidate if it matches or beats the champion.
    """
    candidate_ver = ModelRegistry.get_version(model_type, candidate_version_id)
    if not candidate_ver:
        logger.error(f"promote_if_better: candidate version '{candidate_version_id}' not found")
        return False

    all_versions = ModelRegistry.list_versions(model_type)
    # Find active champion version prior to this evaluation (excluding candidate if it's currently marked active)
    other_active = [
        v for v in all_versions
        if v.get("version_id") != candidate_version_id and v.get("status") == "active"
    ]

    # If no previous active champion exists, candidate becomes champion automatically
    if not other_active:
        logger.info(
            f"PROMOTED: Candidate '{candidate_version_id}' is the first/only active version for '{model_type}'."
        )
        ModelRegistry.set_active_version(model_type, candidate_version_id)
        return True

    champion_ver = other_active[0]
    champion_version_id = champion_ver["version_id"]

    cand_metric_name, cand_val = _extract_primary_metric(model_type, candidate_ver.get("metrics", {}))
    champ_metric_name, champ_val = _extract_primary_metric(model_type, champion_ver.get("metrics", {}))

    is_classification = (model_type == "fraud_detection")

    if is_classification:
        # Higher is better
        # Tie-breaking: cand_val >= champ_val -> candidate promotes
        promoted = cand_val >= champ_val
    else:
        # Lower is better (RMSE/MAE)
        # Tie-breaking: cand_val <= champ_val -> candidate promotes
        promoted = cand_val <= champ_val

    if promoted:
        ModelRegistry.set_active_version(model_type, candidate_version_id)
        logger.info(
            f"PROMOTED: Candidate '{candidate_version_id}' ({cand_metric_name}={cand_val}) "
            f"beat/matched champion '{champion_version_id}' ({champ_metric_name}={champ_val}) for '{model_type}'."
        )
        return True
    else:
        ModelRegistry.set_active_version(model_type, champion_version_id)
        logger.info(
            f"NOT PROMOTED: Candidate '{candidate_version_id}' ({cand_metric_name}={cand_val}) "
            f"was worse than champion '{champion_version_id}' ({champ_metric_name}={champ_val}) for '{model_type}'."
        )
        return False


def check_and_rollback_degraded_models(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Automatic rollback check:
    For each model type, checks if the currently active version has been live for < 7 days
    and its live accuracy has degraded by > 20% relative to the previous version.
    Triggers ModelRegistry.rollback() if degradation is detected.
    """
    model_types = [
        "eta_prediction",
        "demand_forecast",
        "slot_recommendation",
        "vendor_ranking",
        "fraud_detection",
    ]

    close_db = False
    if db is None:
        from app.database.session import SessionLocal
        db = SessionLocal()
        close_db = True

    results = {}
    try:
        from app.ml.backtest import backtest_eta, backtest_vendor_ranking
        from app.ml.retraining_log_model import RetrainingLog

        for m_type in model_types:
            all_vers = ModelRegistry.list_versions(m_type)
            if not all_vers:
                continue

            active_ver = ModelRegistry.get_active_version(m_type)
            if not active_ver:
                continue

            # Check age (< 7 days)
            trained_at_str = active_ver.get("trained_at")
            if not trained_at_str:
                continue

            try:
                trained_at = datetime.fromisoformat(trained_at_str.replace("Z", "+00:00"))
                if trained_at.tzinfo is None:
                    trained_at = trained_at.replace(tzinfo=timezone.utc)
            except Exception:
                trained_at = datetime.now(timezone.utc)

            age_days = (datetime.now(timezone.utc) - trained_at).total_seconds() / 86400.0
            if age_days >= 7.0:
                # Outside the 7-day rollback window
                continue

            # Find previous version
            previous_vers = [v for v in all_vers if v["version_id"] != active_ver["version_id"]]
            if not previous_vers:
                continue

            prev_ver = previous_vers[0]

            # Compute degradation
            live_metric = None
            baseline_metric = None
            is_degraded = False
            degradation_pct = 0.0

            if m_type == "eta_prediction":
                bt = backtest_eta(db, days=7)
                if bt.get("status") == "success" and bt.get("mae_minutes") is not None:
                    live_metric = float(bt["mae_minutes"])
                    _, baseline_metric = _extract_primary_metric(m_type, prev_ver.get("metrics", {}))
                    if baseline_metric != float("inf") and baseline_metric > 0:
                        degradation_pct = ((live_metric - baseline_metric) / baseline_metric) * 100.0
                        if degradation_pct > 20.0:
                            is_degraded = True
            elif m_type == "vendor_ranking":
                bt = backtest_vendor_ranking(db, days=7)
                if bt.get("status") == "success" and bt.get("top_1_hit_rate") is not None:
                    live_metric = float(bt["top_1_hit_rate"])
                    _, baseline_metric = _extract_primary_metric(m_type, prev_ver.get("metrics", {}))
                    if baseline_metric > 0:
                        degradation_pct = ((baseline_metric - live_metric) / baseline_metric) * 100.0
                        if degradation_pct > 20.0:
                            is_degraded = True
            else:
                # General metric comparison using active version recorded metrics vs live/previous
                _, cand_metric = _extract_primary_metric(m_type, active_ver.get("metrics", {}))
                _, baseline_metric = _extract_primary_metric(m_type, prev_ver.get("metrics", {}))
                if m_type == "fraud_detection":
                    if baseline_metric > 0:
                        degradation_pct = ((baseline_metric - cand_metric) / baseline_metric) * 100.0
                        if degradation_pct > 20.0:
                            is_degraded = True
                else:
                    if baseline_metric != float("inf") and baseline_metric > 0:
                        degradation_pct = ((cand_metric - baseline_metric) / baseline_metric) * 100.0
                        if degradation_pct > 20.0:
                            is_degraded = True

            if is_degraded:
                logger.warning(
                    f"AUTOMATIC ROLLBACK TRIGGERED: Model '{m_type}' version '{active_ver['version_id']}' "
                    f"degraded by {degradation_pct:.1f}% (live/current={live_metric or cand_metric}, "
                    f"baseline={baseline_metric}) within {age_days:.1f} days. "
                    f"Rolling back to previous champion '{prev_ver['version_id']}'."
                )

                ModelRegistry.set_active_version(m_type, prev_ver["version_id"])

                # Log rollback event to DB
                try:
                    log_entry = RetrainingLog(
                        model_type=m_type,
                        triggered_at=datetime.now(timezone.utc),
                        status="rollback",
                        version_id=prev_ver["version_id"],
                        error_message=(
                            f"Automated rollback from {active_ver['version_id']} due to "
                            f"{degradation_pct:.1f}% accuracy degradation within {age_days:.1f} days"
                        ),
                    )
                    db.add(log_entry)
                    db.commit()
                except Exception as log_err:
                    db.rollback()
                    logger.error(f"Failed to log rollback event: {log_err}")

                results[m_type] = {
                    "rolled_back": True,
                    "previous_version": prev_ver["version_id"],
                    "degraded_version": active_ver["version_id"],
                    "degradation_pct": round(degradation_pct, 2),
                }
            else:
                results[m_type] = {
                    "rolled_back": False,
                    "active_version": active_ver["version_id"],
                }

    finally:
        if close_db:
            db.close()

    return results
