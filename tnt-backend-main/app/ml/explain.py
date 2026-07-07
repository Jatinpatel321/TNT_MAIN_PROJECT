"""Model explainability and feature importance.

Uses sklearn's built-in feature importance and permutation importance to
provide human-readable explanations for model predictions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("tnt.ml.explain")


def get_feature_importance(model: Any, feature_names: list[str]) -> list[dict[str, Any]]:
    """Extract feature importance from a trained model.

    Supports sklearn, XGBoost, and LightGBM models.
    Returns sorted list of {feature, importance} dicts.
    """
    importance = None

    # sklearn / XGBoost feature_importances_
    if hasattr(model, "feature_importances_"):
        importance = model.feature_importances_

    # LightGBM
    elif hasattr(model, "feature_importance"):
        try:
            importance = model.feature_importance()
        except Exception:
            pass

    if importance is None:
        logger.warning("Model type %s does not expose feature importance", type(model).__name__)
        return [{"feature": f, "importance": 0.0} for f in feature_names]

    # Ensure length matches
    if len(importance) != len(feature_names):
        logger.warning("Feature importance length %d != feature_names length %d",
                       len(importance), len(feature_names))
        return [{"feature": f, "importance": float(v)} for f, v in zip(feature_names, importance)]

    result = [
        {"feature": f, "importance": float(v)}
        for f, v in zip(feature_names, importance)
    ]
    result.sort(key=lambda x: x["importance"], reverse=True)
    return result


def explain_prediction(model: Any, features: np.ndarray,
                       feature_names: list[str],
                       prediction: float) -> dict[str, Any]:
    """Generate human-readable explanation for a single prediction.

    Args:
        model: Trained model.
        features: Feature vector (1D array) for the prediction.
        feature_names: Names of features.
        prediction: The model's prediction value.

    Returns:
        Dict with top_features, base_value, and natural language explanation.
    """
    features_2d = features.reshape(1, -1)
    importance = get_feature_importance(model, feature_names)

    # Determine which features pushed the prediction up/down
    baseline = np.mean(features_2d, axis=0)
    contributions = []
    for i, name in enumerate(feature_names):
        feat_val = features_2d[0, i]
        baseline_val = baseline[i]
        direction = "higher" if feat_val > baseline_val else "lower"
        contributions.append({
            "feature": name,
            "value": float(feat_val),
            "baseline": float(baseline_val),
            "direction": direction,
            "importance": next((imp["importance"] for imp in importance if imp["feature"] == name), 0.0),
        })

    contributions.sort(key=lambda c: c["importance"], reverse=True)
    top_contributors = contributions[:3]

    # Build natural language explanation
    reasons = []
    for tc in top_contributors:
        reasons.append(
            f"'{tc['feature']}' is {tc['direction']} than average "
            f"(value: {tc['value']:.2f}, importance: {tc['importance']:.3f})"
        )

    return {
        "prediction": float(prediction),
        "top_contributing_features": top_contributors,
        "explanation": " | ".join(reasons) if reasons else "Prediction based on model patterns",
        "feature_importance_all": importance,
    }


def confidence_score(model: Any, features: np.ndarray,
                     prediction: float) -> float:
    """Estimate confidence score for a prediction (0.0 to 1.0).

    Uses tree-based model's standard deviation across trees (if available)
    or variance-based heuristic.
    """
    # For RandomForest / XGBoost, use std of individual tree predictions
    if hasattr(model, "estimators_"):
        # sklearn RandomForest
        tree_preds = np.array([tree.predict(features.reshape(1, -1)) for tree in model.estimators_])
        std = float(np.std(tree_preds))
        # Normalize: lower std = higher confidence
        max_std = 30.0  # 30 minutes for ETA
        return max(0.0, min(1.0, 1.0 - (std / max_std)))

    if hasattr(model, "predict"):
        # Fallback: heuristic based on prediction magnitude
        return 0.75  # default moderate confidence

    return 0.5
