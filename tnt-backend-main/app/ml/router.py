"""ML-Powered AI Analytics Dashboard API Router.

Provides ML-powered predictions, rankings, forecasts, and recommendations
with model storage, retraining, accuracy tracking, versioning, and explainability.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user, require_role
from app.ml.registry import ModelRegistry
from app.database.session import SessionLocal

router = APIRouter(prefix="/ml", tags=["ML Analytics Dashboard"])


def _get_ml_service(db: Session) -> Any:
    """Lazy-import MLPredictionService so numpy/scikit-learn deps
    are not imported at module load time (Python 3.15 compat)."""
    from app.ml.predictions import MLPredictionService  # lazy
    return MLPredictionService(db)


def _get_retraining_service() -> Any:
    """Lazy-import RetrainingService so ML deps are not loaded at import time."""
    from app.ml.training_pipeline import RetrainingService  # lazy
    return RetrainingService(SessionLocal)


# ── Model Registry Endpoints ────────────────────────────────────────────

@router.get("/registry", summary="Get model registry summary")
def get_registry(
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Get summary of all registered ML models with version info."""
    return ModelRegistry.get_registry_summary()


@router.get("/registry/{model_type}", summary="List model versions")
def list_model_versions(
    model_type: str,
    user=Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    """List all versions of a specific model type."""
    return ModelRegistry.list_versions(model_type)


@router.post("/registry/{model_type}/rollback/{version_num}", summary="Rollback model")
def rollback_model(
    model_type: str,
    version_num: int,
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Rollback a model to a previous version."""
    result = ModelRegistry.rollback(model_type, version_num)
    if not result:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"status": "rolled_back", "latest_version": result}


# ── Training Endpoints ──────────────────────────────────────────────────

@router.post("/train/all", summary="Train all ML models")
def train_all_models(
    days: int = Query(90, description="Training window in days"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Run full training pipeline for all model types."""
    from app.ml.training_pipeline import run_full_training_pipeline  # lazy
    return run_full_training_pipeline(db, days=days)


@router.post("/train/eta", summary="Train ETA prediction model")
def train_eta(
    days: int = Query(90, description="Training window in days"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the ETA prediction model (XGBoost vs LightGBM vs RandomForest comparison)."""
    from app.ml.training_pipeline import train_eta_models  # lazy
    return train_eta_models(db, days=days)


@router.post("/train/demand/{vendor_id}", summary="Train demand forecast")
def train_demand(
    vendor_id: int,
    days: int = Query(90, description="Training window in days"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Train/retrain demand forecast model for a specific vendor."""
    from app.ml.training_pipeline import train_demand_forecast  # lazy
    return train_demand_forecast(db, vendor_id, days=days)


@router.post("/train/fraud", summary="Train fraud detection model")
def train_fraud(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the fraud detection model."""
    from app.ml.training_pipeline import train_fraud_detection  # lazy
    return train_fraud_detection(db)


@router.post("/train/vendor-ranking", summary="Train vendor ranking model")
def train_vendor_ranking_endpoint(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the vendor ranking model."""
    from app.ml.training_pipeline import train_vendor_ranking  # lazy
    return train_vendor_ranking(db)


@router.post("/train/slot-recommendation", summary="Train slot recommendation model")
def train_slot_rec(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the slot recommendation model."""
    from app.ml.training_pipeline import train_slot_recommendation  # lazy
    return train_slot_recommendation(db)


# ── Retraining Service (scheduled) ──────────────────────────────────────

@router.post("/retrain", summary="Retrain all models (background)")
def retrain_all(
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Trigger background retraining of all models using latest data."""
    service = _get_retraining_service()
    return service.retrain_all()


# ── ETA Prediction ──────────────────────────────────────────────────────

@router.get("/predict/eta", summary="Predict ETA with ML")
def predict_eta(
    vendor_id: int = Query(..., description="Vendor ID"),
    slot_id: int = Query(..., description="Slot ID"),
    item_count: int = Query(1, description="Number of items in order"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Predict ETA for an order using the best ML model with confidence score."""
    service = _get_ml_service(db)
    return service.predict_eta(vendor_id, slot_id, item_count)


# ── Demand Forecasting ──────────────────────────────────────────────────

@router.get("/forecast/demand", summary="Forecast vendor demand")
def forecast_demand(
    vendor_id: int = Query(..., description="Vendor ID"),
    days: int = Query(7, description="Forecast horizon in days"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Predict hourly demand for a vendor over the next N days using ML."""
    service = _get_ml_service(db)
    return service.forecast_demand(vendor_id, days)


# ── Smart Slot Recommendation ───────────────────────────────────────────

@router.get("/recommend/slots", summary="Recommend slots")
def recommend_slots(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Recommend fastest, least crowded, and best slots using ML."""
    service = _get_ml_service(db)
    return service.recommend_slot(user["id"])


# ── Personalized Recommendations ────────────────────────────────────────

@router.get("/recommend/personalized", summary="Personalized item recommendations")
def get_personalized_recs(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Get hybrid (collaborative + content-based) personalized item recommendations."""
    service = _get_ml_service(db)
    return service.get_personalized_recommendations(user["id"])


# ── Vendor Ranking ──────────────────────────────────────────────────────

@router.get("/rank/vendors", summary="Rank vendors")
def rank_vendors(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Rank vendors by ML-powered score based on rating, speed, cancellations, refunds."""
    service = _get_ml_service(db)
    return service.rank_vendors()


# ── Fraud Detection ─────────────────────────────────────────────────────

@router.get("/detect/fraud", summary="Detect fraud")
def detect_fraud(
    user_id: int = Query(..., description="User ID to check"),
    order_id: int = Query(..., description="Order ID to check"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Detect potentially fraudulent orders using ML classifier."""
    service = _get_ml_service(db)
    return service.detect_fraud(user_id, order_id)


# ── Explainability ──────────────────────────────────────────────────────

@router.get("/explain/{model_type}", summary="Get feature importance")
def get_model_explainability(
    model_type: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Get feature importance for a trained model."""
    model_data = ModelRegistry.load(model_type)
    if model_data is None:
        raise HTTPException(status_code=404, detail=f"No model found for type '{model_type}'")
    from app.ml.explain import get_feature_importance  # lazy
    model, metadata = model_data
    feature_names = metadata.get("features", [])
    importance = get_feature_importance(model, feature_names)
    return {
        "model_type": model_type,
        "version_id": metadata.get("version_id"),
        "feature_importance": importance,
        "metrics": metadata.get("metrics", {}),
    }


# ── Accuracy Tracking ───────────────────────────────────────────────────

def _get_combined_accuracy(model_type: str, db: Session) -> dict[str, Any]:
    from app.ml.registry import ModelRegistry
    from app.ml.backtest import backtest_eta, backtest_vendor_ranking
    from app.ml.drift_report_model import DriftReport

    # 1. Training-time version metrics
    versions = ModelRegistry.compare_versions(model_type)
    active_version = next((v for v in versions if v.get("status") == "active"), None)
    if not active_version and versions:
        active_version = versions[0]

    # 2. Latest backtest metrics
    latest_backtest = None
    if model_type == "eta_prediction":
        latest_backtest = backtest_eta(db, days=30)
    elif model_type == "vendor_ranking":
        latest_backtest = backtest_vendor_ranking(db, days=30)

    # 3. Latest drift status
    latest_drift = None
    drift_row = db.query(DriftReport).filter(
        DriftReport.model_type == model_type,
        DriftReport.check_type == "data_drift",
    ).order_by(DriftReport.created_at.desc()).first()

    if drift_row:
        latest_drift = {
            "has_drift": drift_row.has_drift,
            "drifted_features": drift_row.report_data.get("drifted_features", []),
            "feature_psi": drift_row.report_data.get("feature_psi", {}),
            "created_at": drift_row.created_at.isoformat(),
        }
    else:
        latest_drift = {
            "has_drift": False,
            "drifted_features": [],
            "feature_psi": {},
            "created_at": None,
        }

    # 4. Feature Importance
    feature_importance = []
    try:
        model_data = ModelRegistry.load(model_type)
        if model_data:
            model, metadata = model_data
            from app.ml.explain import get_feature_importance
            feature_importance = get_feature_importance(model, metadata.get("features", []))
    except Exception:
        feature_importance = []

    return {
        "model_type": model_type,
        "active_version": active_version,
        "versions": versions,
        "latest_backtest": latest_backtest,
        "latest_drift": latest_drift,
        "feature_importance": feature_importance,
    }


@router.get("/accuracy/summary", summary="Combined model accuracy summary")
def get_accuracy_summary(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Get combined accuracy, backtest, and drift status across all 5 model types."""
    model_types = [
        "eta_prediction",
        "demand_forecast",
        "slot_recommendation",
        "vendor_ranking",
        "fraud_detection",
    ]
    return {m_type: _get_combined_accuracy(m_type, db) for m_type in model_types}


@router.get("/accuracy/{model_type}", summary="Track model accuracy")
def get_model_accuracy(
    model_type: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Get combined accuracy, version history, backtest, and drift status for a model type."""
    return _get_combined_accuracy(model_type, db)


# ── Model Backtesting Endpoints ─────────────────────────────────────────

@router.get("/backtest/eta", summary="Backtest ETA predictions")
def get_backtest_eta(
    days: int = Query(30, description="Backtest window in days"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Replay historical orders and measure real-world ETA prediction accuracy."""
    from app.ml.backtest import backtest_eta  # lazy
    return backtest_eta(db, days=days)


@router.get("/backtest/vendor-ranking", summary="Backtest vendor ranking model")
def get_backtest_vendor_ranking(
    days: int = Query(30, description="Backtest window in days"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Replay historical order selections and measure vendor ranking hit rates."""
    from app.ml.backtest import backtest_vendor_ranking  # lazy
    return backtest_vendor_ranking(db, days=days)


@router.post("/shadow-log/backfill", summary="Backfill shadow log actuals")
def backfill_shadow_log(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Backfill actual outcomes into shadow_log entries once known."""
    from app.ml.backtest import backfill_shadow_actuals  # lazy
    return backfill_shadow_actuals(db)


# ── Data & Prediction Drift Endpoints ────────────────────────────────────

@router.post("/drift/check", summary="Run drift checks for all ML models")
def run_drift_checks(
    lookback_days: int = Query(7, description="Lookback window in days for recent data"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Run data and prediction drift checks for all 5 model types."""
    from app.ml.drift import run_all_drift_checks  # lazy
    return run_all_drift_checks(db, lookback_days=lookback_days)


@router.get("/drift/reports", summary="Get historical drift reports")
def get_drift_reports(
    model_type: Optional[str] = Query(None, description="Optional model type filter"),
    limit: int = Query(50, description="Max reports to return"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    """List historical data and prediction drift reports."""
    from app.ml.drift_report_model import DriftReport
    query = db.query(DriftReport)
    if model_type:
        query = query.filter(DriftReport.model_type == model_type)
    reports = query.order_by(DriftReport.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "model_type": r.model_type,
            "check_type": r.check_type,
            "has_drift": r.has_drift,
            "report_data": r.report_data,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


# ── Scheduled Retraining & Retraining Logs Endpoints ────────────────────

@router.post("/retrain", summary="Trigger fault-tolerant ML retraining")
def trigger_ml_retraining(
    model_types: Optional[list[str]] = Query(None, description="Optional list of model types to retrain"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Trigger scheduled ML model retraining across specified model types."""
    from app.ml.retraining import run_scheduled_retraining
    return run_scheduled_retraining(model_types=model_types, db=db)


@router.get("/retrain/logs", summary="Get retraining logs")
def get_retraining_logs(
    model_type: Optional[str] = Query(None, description="Optional model type filter"),
    limit: int = Query(50, description="Max log entries to return"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    """Get recent model retraining attempt logs."""
    from app.ml.retraining_log_model import RetrainingLog
    query = db.query(RetrainingLog)
    if model_type:
        query = query.filter(RetrainingLog.model_type == model_type)
    logs = query.order_by(RetrainingLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "model_type": l.model_type,
            "triggered_at": l.triggered_at.isoformat(),
            "status": l.status,
            "version_id": l.version_id,
            "error_message": l.error_message,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]



