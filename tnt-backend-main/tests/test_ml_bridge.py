"""
Unit tests for app/modules/ai_intelligence/ml_bridge.py
=========================================================

Tests all fallback conditions and successful prediction execution:
(a) Model available and succeeds
(b) Model type not in registry
(c) Model raises exception during predict
(d) Missing or NaN feature triggers fallback without calling model
(e) Low confidence score triggers fallback
"""

import math
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

from app.modules.ai_intelligence.ml_bridge import predict_with_fallback, FALLBACK_EVENTS


@pytest.fixture(autouse=True)
def reset_fallback_events():
    """Reset FALLBACK_EVENTS counter before each test."""
    FALLBACK_EVENTS.clear()


def test_model_available_and_succeeds():
    """(a) Test model available and prediction succeeds -> returns (pred, 'model') without calling heuristic."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([18.5])
    mock_metadata = {"features": ["vendor_id", "item_count"], "version_id": "v1"}

    heuristic_fn = MagicMock(return_value=15.0)

    features = {"vendor_id": 1.0, "item_count": 2.0}

    with patch("app.ml.registry.ModelRegistry.load", return_value=(mock_model, mock_metadata)):
        result, source = predict_with_fallback(
            model_type="eta_prediction",
            features=features,
            heuristic_fn=heuristic_fn,
        )

    assert source == "model"
    assert result == 18.5
    heuristic_fn.assert_not_called()
    assert FALLBACK_EVENTS.get("eta_prediction", 0) == 0


def test_model_type_not_in_registry():
    """(b) Test model type not in registry -> logs warning, increments counter, calls heuristic."""
    heuristic_fn = MagicMock(return_value=20.0)
    features = {"vendor_id": 1.0}

    with patch("app.ml.registry.ModelRegistry.load", return_value=None):
        result, source = predict_with_fallback(
            model_type="non_existent_model",
            features=features,
            heuristic_fn=heuristic_fn,
        )

    assert source == "heuristic"
    assert result == 20.0
    heuristic_fn.assert_called_once()
    assert FALLBACK_EVENTS["non_existent_model"] == 1


def test_model_raises_exception_during_predict():
    """(c) Test model raises exception during predict -> logs warning, increments counter, calls heuristic."""
    mock_model = MagicMock()
    mock_model.predict.side_effect = RuntimeError("Model prediction failure")

    heuristic_fn = MagicMock(return_value=25.0)
    features = {"vendor_id": 1.0, "item_count": 3.0}

    with patch("app.ml.registry.ModelRegistry.load", return_value=(mock_model, {})):
        result, source = predict_with_fallback(
            model_type="eta_prediction",
            features=features,
            heuristic_fn=heuristic_fn,
        )

    assert source == "heuristic"
    assert result == 25.0
    heuristic_fn.assert_called_once()
    assert FALLBACK_EVENTS["eta_prediction"] == 1


def test_missing_or_nan_feature_triggers_fallback_without_calling_model():
    """(d) Test missing (None), NaN, or Inf feature -> triggers fallback without loading or calling model."""
    heuristic_fn = MagicMock(return_value=30.0)

    invalid_feature_sets = [
        {"vendor_id": None, "item_count": 2.0},
        {"vendor_id": 1.0, "item_count": float("nan")},
        {"vendor_id": float("inf"), "item_count": 2.0},
    ]

    with patch("app.ml.registry.ModelRegistry.load") as mock_load:
        for idx, features in enumerate(invalid_feature_sets, 1):
            heuristic_fn.reset_mock()
            result, source = predict_with_fallback(
                model_type="eta_prediction",
                features=features,
                heuristic_fn=heuristic_fn,
            )

            assert source == "heuristic"
            assert result == 30.0
            heuristic_fn.assert_called_once()
            assert FALLBACK_EVENTS["eta_prediction"] == idx

        # Ensure ModelRegistry.load was never called because feature check short-circuits
        mock_load.assert_not_called()


def test_min_confidence_fallback():
    """Test predicted confidence below min_confidence triggers fallback."""
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array([1])
    mock_model.predict_proba.return_value = np.array([[0.4, 0.6]])  # Max confidence 0.6

    heuristic_fn = MagicMock(return_value=10.0)
    features = {"vendor_id": 1.0}

    with patch("app.ml.registry.ModelRegistry.load", return_value=(mock_model, {})):
        result, source = predict_with_fallback(
            model_type="classification_model",
            features=features,
            heuristic_fn=heuristic_fn,
            min_confidence=0.8,  # Requires >= 0.8 confidence
        )

    assert source == "heuristic"
    assert result == 10.0
    heuristic_fn.assert_called_once()
    assert FALLBACK_EVENTS["classification_model"] == 1


def test_model_loading_exception_triggers_fallback():
    """Test exception raised during ModelRegistry.load triggers fallback."""
    heuristic_fn = MagicMock(return_value=12.0)
    features = {"vendor_id": 1.0}

    with patch("app.ml.registry.ModelRegistry.load", side_effect=Exception("Database connection error")):
        result, source = predict_with_fallback(
            model_type="eta_prediction",
            features=features,
            heuristic_fn=heuristic_fn,
        )

    assert source == "heuristic"
    assert result == 12.0
    heuristic_fn.assert_called_once()
    assert FALLBACK_EVENTS["eta_prediction"] == 1
