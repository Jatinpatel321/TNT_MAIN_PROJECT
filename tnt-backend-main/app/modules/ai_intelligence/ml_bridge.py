"""
ML Bridge Utility
=================

Shared safe integration bridge connecting heuristic planners in
app/modules/ai_intelligence/ to trained ML models in app/ml/.

Exposes `predict_with_fallback` which attempts to load and execute an ML model,
falling back lazily to a heuristic function when the model is missing, fails,
or receives invalid features.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from app.ml.registry import ModelRegistry

logger = logging.getLogger("tnt.ai_intelligence.ml_bridge")

# Global in-memory counter tracking fallback frequency per model_type and total
FALLBACK_EVENTS: dict[str, int] = defaultdict(int)


def _is_invalid_feature_value(val: Any) -> bool:
    """Check if a feature value is None, NaN, or Infinite."""
    if val is None:
        return True
    if isinstance(val, (float, int, np.number)):
        try:
            f_val = float(val)
            if math.isnan(f_val) or math.isinf(f_val):
                return True
        except (ValueError, TypeError):
            return True
    return False


def _log_shadow_entry(
    model_type: str,
    entity_id: Optional[int],
    model_val: Optional[float],
    heuristic_val: Optional[float],
    db: Optional[Session] = None,
) -> None:
    """Log predictions to shadow_log table safely."""
    try:
        from app.ml.shadow_log_model import ShadowLog
        close_session = False
        if db is None:
            from app.database.session import SessionLocal
            db = SessionLocal()
            close_session = True

        entry = ShadowLog(
            model_type=model_type,
            entity_id=entity_id,
            predicted_model=model_val,
            predicted_heuristic=heuristic_val,
            actual_value=None,
        )
        db.add(entry)
        db.commit()
        if close_session:
            db.close()
    except Exception as e:
        logger.warning("Failed to record shadow log for '%s': %s", model_type, e)


def predict_with_fallback(
    model_type: str,
    features: dict,
    heuristic_fn: Callable[[], Any],
    min_confidence: float = 0.0,
    db: Optional[Session] = None,
    entity_id: Optional[int] = None,
    shadow: bool = False,
) -> tuple[Any, str]:
    """
    Attempts to load and run the trained model for `model_type` via
    app.ml.registry.ModelRegistry and app.ml.predictions.MLPredictionService.
    Returns (result, source) where source is "model" or "heuristic".

    Falls back to heuristic_fn() — calling it lazily, not eagerly — when:
    - ModelRegistry has no trained version for model_type
    - Model loading raises any exception
    - Prediction raises any exception
    - Any missing/NaN value is found in `features`
    - (future hook) predicted confidence < min_confidence, if the model
      exposes a confidence/probability output

    If `shadow=True`:
    Runs BOTH model and heuristic, logs predictions to shadow_log, but returns
    only the heuristic result to the caller.
    """
    # If shadow mode is enabled, evaluate both model and heuristic and log to shadow_log
    if shadow:
        heuristic_res = heuristic_fn()
        try:
            h_val = float(heuristic_res)
        except (ValueError, TypeError):
            h_val = None

        m_val = None
        if isinstance(features, dict) and features:
            valid = not any(_is_invalid_feature_value(v) for v in features.values())
            if valid:
                try:
                    model_data = ModelRegistry.load(model_type)
                    if model_data is not None:
                        model, metadata = model_data if isinstance(model_data, tuple) else (model_data, {})
                        feature_names = metadata.get("features") if isinstance(metadata, dict) else None
                        if feature_names and all(name in features for name in feature_names):
                            feature_vector = [features[name] for name in feature_names]
                        else:
                            feature_vector = list(features.values())
                        input_data = np.array([feature_vector])
                        if callable(model) and not hasattr(model, "predict"):
                            raw_pred = model(input_data)
                        else:
                            try:
                                raw_pred = model.predict(input_data)
                            except Exception:
                                raw_pred = model.predict(features)
                        if hasattr(raw_pred, "__getitem__") and hasattr(raw_pred, "__len__") and len(raw_pred) > 0:
                            m_val = float(raw_pred[0])
                        else:
                            m_val = float(raw_pred)
                except Exception as shadow_err:
                    logger.debug("Shadow model evaluation exception for '%s': %s", model_type, shadow_err)

        _log_shadow_entry(model_type, entity_id, m_val, h_val, db)
        return heuristic_res, "heuristic"

    # 1. Input validation on features
    if not isinstance(features, dict) or not features:
        reason = f"Features payload is empty or invalid for model_type '{model_type}'"
        logger.warning("ML Fallback triggered for '%s': %s", model_type, reason)
        FALLBACK_EVENTS[model_type] += 1
        FALLBACK_EVENTS["_total"] += 1
        return heuristic_fn(), "heuristic"

    for k, v in features.items():
        if _is_invalid_feature_value(v):
            reason = f"Missing or NaN/Inf value found in feature '{k}': {v}"
            logger.warning("ML Fallback triggered for '%s': %s", model_type, reason)
            FALLBACK_EVENTS[model_type] += 1
            FALLBACK_EVENTS["_total"] += 1
            return heuristic_fn(), "heuristic"

    # 2. Model Loading
    try:
        model_data = ModelRegistry.load(model_type)
    except Exception as e:
        reason = f"Exception loading model artifact for '{model_type}': {e}"
        logger.warning("ML Fallback triggered for '%s': %s", model_type, reason)
        FALLBACK_EVENTS[model_type] += 1
        FALLBACK_EVENTS["_total"] += 1
        return heuristic_fn(), "heuristic"

    if model_data is None:
        reason = f"No trained/active model found in ModelRegistry for model_type '{model_type}'"
        logger.warning("ML Fallback triggered for '%s': %s", model_type, reason)
        FALLBACK_EVENTS[model_type] += 1
        FALLBACK_EVENTS["_total"] += 1
        return heuristic_fn(), "heuristic"

    model, metadata = model_data if isinstance(model_data, tuple) else (model_data, {})

    # 3. Model Prediction
    try:
        # Construct feature array / vector
        feature_names = metadata.get("features") if isinstance(metadata, dict) else None
        if feature_names and all(name in features for name in feature_names):
            feature_vector = [features[name] for name in feature_names]
        else:
            feature_vector = list(features.values())

        input_data = np.array([feature_vector])

        if callable(model) and not hasattr(model, "predict"):
            raw_prediction = model(input_data)
        else:
            try:
                raw_prediction = model.predict(input_data)
            except Exception:
                try:
                    import pandas as pd
                    df = pd.DataFrame([features])
                    raw_prediction = model.predict(df)
                except Exception:
                    raw_prediction = model.predict(features)

        # Extract prediction result value
        if hasattr(raw_prediction, "__getitem__") and hasattr(raw_prediction, "__len__") and len(raw_prediction) > 0:
            prediction = raw_prediction[0]
        else:
            prediction = raw_prediction

        # 4. Confidence Evaluation (if model exposes probability/confidence)
        confidence: Optional[float] = None
        if hasattr(model, "predict_proba"):
            try:
                probs = model.predict_proba(input_data)
                if hasattr(probs, "__getitem__") and len(probs) > 0:
                    confidence = float(np.max(probs[0]))
            except Exception:
                pass
        elif hasattr(model, "predict_confidence"):
            try:
                confidence = float(model.predict_confidence(input_data))
            except Exception:
                pass

        if min_confidence > 0.0 and confidence is not None and confidence < min_confidence:
            reason = f"Predicted confidence ({confidence:.3f}) below min_confidence ({min_confidence:.3f})"
            logger.warning("ML Fallback triggered for '%s': %s", model_type, reason)
            FALLBACK_EVENTS[model_type] += 1
            FALLBACK_EVENTS["_total"] += 1
            return heuristic_fn(), "heuristic"

        return prediction, "model"

    except Exception as e:
        reason = f"Exception during prediction execution for model_type '{model_type}': {e}"
        logger.warning("ML Fallback triggered for '%s': %s", model_type, reason)
        FALLBACK_EVENTS[model_type] += 1
        FALLBACK_EVENTS["_total"] += 1
        return heuristic_fn(), "heuristic"

