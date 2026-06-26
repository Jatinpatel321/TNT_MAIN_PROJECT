"""ML-Powered AI Analytics Dashboard API Router.

Provides ML-powered predictions, rankings, forecasts, and recommendations
with model storage, retraining, accuracy tracking, versioning, and explainability.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user, require_role
from app.ml.predictions import MLPredictionService
from app.ml.registry import ModelRegistry
from app.ml.training_pipeline import (
    RetrainingService,
    run_full_training_pipeline,
    train_eta_models,
    train_demand_forecast,
    train_fraud_detection,
    train_vendor_ranking,
    train_slot_recommendation,
)
from app.ml.explain import get_feature_importance
from app.database.session import SessionLocal

router = APIRouter(prefix="/ml", tags=["ML Analytics Dashboard"])


def _get_ml_service(db: Session) -> MLPredictionService:
    return MLPredictionService(db)


def _get_retraining_service() -> RetrainingService:
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
    return run_full_training_pipeline(db, days=days)


@router.post("/train/eta", summary="Train ETA prediction model")
def train_eta(
    days: int = Query(90, description="Training window in days"),
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the ETA prediction model (XGBoost vs LightGBM vs RandomForest comparison)."""
    return train_eta_models(db, days=days)


@router.post("/train/demand/{vendor_id}", summary="Train demand forecast")
def train_demand(
    vendor_id: int,
    days: int = Query(90, description="Training window in days"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Train/retrain demand forecast model for a specific vendor."""
    return train_demand_forecast(db, vendor_id, days=days)


@router.post("/train/fraud", summary="Train fraud detection model")
def train_fraud(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the fraud detection model."""
    return train_fraud_detection(db)


@router.post("/train/vendor-ranking", summary="Train vendor ranking model")
def train_vendor_ranking_endpoint(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the vendor ranking model."""
    return train_vendor_ranking(db)


@router.post("/train/slot-recommendation", summary="Train slot recommendation model")
def train_slot_rec(
    db: Session = Depends(get_db),
    user=Depends(require_role("admin")),
) -> dict[str, Any]:
    """Train/retrain the slot recommendation model."""
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

@router.get("/accuracy/{model_type}", summary="Track model accuracy")
def get_model_accuracy(
    model_type: str,
    user=Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    """Compare accuracy metrics across all versions of a model type."""
    return ModelRegistry.compare_versions(model_type)
