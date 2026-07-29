"""
ML Retraining Module — Handles scheduled fault-tolerant model retraining and logging.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from app.ml.retraining_log_model import RetrainingLog

logger = logging.getLogger("tnt.ml.retraining")


def run_single_model_retraining(model_type: str, db: Session) -> Dict[str, Any]:
    """
    Retrains a single model type and logs the attempt in ml_retraining_logs.
    Never raises an exception — captures all errors and returns a status dictionary.
    """
    from app.ml.training_pipeline import (
        train_eta,
        train_demand,
        train_slot_recommendation,
        train_vendor_ranking,
        train_fraud_detection,
    )

    triggered_at = datetime.now(timezone.utc)
    status = "failed"
    version_id = None
    error_msg = None
    result: Dict[str, Any] = {}

    try:
        if model_type == "eta_prediction":
            result = train_eta(db)
        elif model_type == "demand_forecast":
            result = train_demand(db)
        elif model_type == "slot_recommendation":
            result = train_slot_recommendation(db)
        elif model_type == "vendor_ranking":
            result = train_vendor_ranking(db)
        elif model_type == "fraud_detection":
            result = train_fraud_detection(db)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        if isinstance(result, dict):
            res_status = result.get("status")
            if res_status == "insufficient_data":
                status = "insufficient_data"
                error_msg = str(result.get("reason") or result.get("error") or "Insufficient training data")
            elif res_status in ["success", "trained"]:
                version_id = result.get("version_id")
                if version_id:
                    from app.ml.promotion import promote_if_better
                    is_promoted = promote_if_better(model_type, version_id)
                    result["promoted"] = is_promoted
                    status = "promoted" if is_promoted else "not_promoted"
                else:
                    status = "success"
            elif res_status == "failed":
                status = "failed"
                error_msg = str(result.get("error") or "Training failed")
            else:
                version_id = result.get("version_id")
                if version_id:
                    from app.ml.promotion import promote_if_better
                    is_promoted = promote_if_better(model_type, version_id)
                    result["promoted"] = is_promoted
                    status = "promoted" if is_promoted else "not_promoted"
                else:
                    status = "completed"
        else:
            status = "success"

    except Exception as exc:
        logger.warning(f"Retraining failed for model_type '{model_type}': {exc}")
        status = "failed"
        error_msg = str(exc)
        result = {"status": "failed", "error": error_msg}

    # Record log entry to DB
    try:
        log_entry = RetrainingLog(
            model_type=model_type,
            triggered_at=triggered_at,
            status=status,
            version_id=version_id,
            error_message=error_msg,
        )
        db.add(log_entry)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.error(f"Failed to save RetrainingLog for {model_type}: {db_err}")

    return result


def run_scheduled_retraining(
    model_types: Optional[List[str]] = None,
    db: Optional[Session] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Executes retraining sequentially for specified model types.
    Fault-tolerant: if one model type fails or encounters an exception,
    it logs and continues to the remaining model types.
    """
    if model_types is None:
        model_types = [
            "eta_prediction",
            "demand_forecast",
            "slot_recommendation",
            "vendor_ranking",
            "fraud_detection",
        ]

    close_db_at_end = False
    if db is None:
        from app.database.session import SessionLocal
        db = SessionLocal()
        close_db_at_end = True

    overall_results = {}
    try:
        for m_type in model_types:
            logger.info(f"Scheduled Retraining: starting model '{m_type}'")
            try:
                res = run_single_model_retraining(m_type, db)
                overall_results[m_type] = res
                logger.info(f"Scheduled Retraining: finished model '{m_type}' -> status={res.get('status')}")
            except Exception as outer_err:
                logger.error(f"Scheduled Retraining: unhandled exception for '{m_type}': {outer_err}")
                overall_results[m_type] = {"status": "failed", "error": str(outer_err)}
    finally:
        if close_db_at_end:
            db.close()

    return overall_results
