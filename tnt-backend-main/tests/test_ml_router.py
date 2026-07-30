"""Comprehensive route-level tests for app/ml/router.py.

Target: ≥ 95% coverage of app/ml/router.py

Strategy
--------
* Mount the real FastAPI ``app`` through ``TestClient`` — identical to how
  the fraud-system tests work.
* Override ``get_current_user`` (the leaf dependency called by both
  ``get_current_user`` *and* ``require_role``) so no JWT infra is needed.
* Override ``get_db`` to supply the in-memory SQLite session from conftest.
* Mock every heavy ML service call (ModelRegistry, MLPredictionService,
  training functions, RetrainingService, drift, backtest) to keep the
  tests fast and deterministic — we are testing *router* logic, not ML math.
* Each test validates: status code, response shape, and happy/sad paths.

Router endpoints covered
------------------------
GET  /ml/registry                          → get_registry
GET  /ml/registry/{model_type}             → list_model_versions
POST /ml/registry/{model_type}/rollback/{version_num} → rollback_model (ok + 404)
POST /ml/train/all                         → train_all_models
POST /ml/train/eta                         → train_eta
POST /ml/train/demand/{vendor_id}          → train_demand
POST /ml/train/fraud                       → train_fraud
POST /ml/train/vendor-ranking             → train_vendor_ranking_endpoint
POST /ml/train/slot-recommendation        → train_slot_rec
POST /ml/retrain  (first route registered) → retrain_all
GET  /ml/predict/eta                       → predict_eta
GET  /ml/forecast/demand                   → forecast_demand
GET  /ml/recommend/slots                   → recommend_slots
GET  /ml/recommend/personalized            → get_personalized_recs
GET  /ml/rank/vendors                      → rank_vendors
GET  /ml/detect/fraud                      → detect_fraud
GET  /ml/explain/{model_type}              → get_model_explainability (ok + 404)
GET  /ml/accuracy/summary                  → get_accuracy_summary
GET  /ml/accuracy/{model_type}             → get_model_accuracy
GET  /ml/backtest/eta                      → get_backtest_eta
GET  /ml/backtest/vendor-ranking          → get_backtest_vendor_ranking
POST /ml/shadow-log/backfill               → backfill_shadow_log
POST /ml/drift/check                       → run_drift_checks
GET  /ml/drift/reports                     → get_drift_reports (all + filtered)
GET  /ml/retrain/logs                      → get_retraining_logs (all + filtered)

Private helper covered
----------------------
_get_combined_accuracy (tested indirectly via accuracy endpoints, with
both eta_prediction/vendor_ranking paths + others + drift present/absent)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.core.security import get_current_user
from app.main import app


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for router tests."""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from app.database.base import Base

    from sqlalchemy.pool import StaticPool
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def date_part_sqlite(part, val):
        if not val:
            return None
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val.split('.')[0])
            except Exception:
                try:
                    val = datetime.strptime(val.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return 0
        if part == 'dow':
            return (val.weekday() + 1) % 7
        elif part == 'hour':
            return val.hour
        elif part == 'month':
            return val.month
        return 0

    def date_trunc_sqlite(part, val):
        if not val:
            return None
        if isinstance(val, str):
            try:
                val = datetime.fromisoformat(val.split('.')[0])
            except Exception:
                try:
                    val = datetime.strptime(val.split('.')[0], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    return "2000-01-01 00:00:00"
        if part == 'hour':
            return val.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        elif part == 'day':
            return val.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        return val.strftime("%Y-%m-%d %H:%M:%S")

    @event.listens_for(test_engine, "connect")
    def connect(dbapi_connection, connection_record):
        dbapi_connection.create_function("date_part", 2, date_part_sqlite)
        dbapi_connection.create_function("date_trunc", 2, date_trunc_sqlite)

    # Ensure all app models & ML models are registered on Base.metadata before create_all
    import app.database.init_db  # noqa: F401
    import app.ml.drift_report_model  # noqa: F401
    import app.ml.retraining_log_model  # noqa: F401
    import app.ml.shadow_log_model  # noqa: F401
    import app.ml.ml_models_model  # noqa: F401

    Base.metadata.create_all(bind=test_engine)

    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
    Base.metadata.drop_all(bind=test_engine)

# ── Fake user stubs ────────────────────────────────────────────────────────

_ADMIN_USER = {"id": 1, "phone": "0000000000", "role": "admin", "is_active": True}
_REGULAR_USER = {"id": 2, "phone": "1111111111", "role": "customer", "is_active": True}


# ── Module-level helpers ────────────────────────────────────────────────────

def _client(db_session, user: dict = _ADMIN_USER) -> TestClient:
    """Build a TestClient with both get_db and get_current_user overridden."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ── Per-test cleanup of dependency overrides ───────────────────────────────

@pytest.fixture(autouse=True)
def _clear_ml_router_overrides():
    """Remove ML-router dependency overrides after every test."""
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


# ══════════════════════════════════════════════════════════════════════════
# 1. Registry Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestRegistryEndpoints:
    """GET /ml/registry, GET /ml/registry/{model_type},
    POST /ml/registry/{model_type}/rollback/{version_num}"""

    def test_get_registry_returns_summary(self, db_session):
        """GET /ml/registry returns a dict from ModelRegistry.get_registry_summary."""
        fake_summary = {"eta_prediction": {"total_versions": 2, "active_version": "eta_prediction_v2"}}
        with patch("app.ml.router.ModelRegistry.get_registry_summary", return_value=fake_summary):
            resp = _client(db_session).get("/ml/registry")
        assert resp.status_code == 200
        body = resp.json()
        assert "eta_prediction" in body
        assert body["eta_prediction"]["total_versions"] == 2

    def test_get_registry_empty_summary(self, db_session):
        """GET /ml/registry with empty registry returns empty dict."""
        with patch("app.ml.router.ModelRegistry.get_registry_summary", return_value={}):
            resp = _client(db_session).get("/ml/registry")
        assert resp.status_code == 200
        assert resp.json() == {}

    def test_list_model_versions_returns_list(self, db_session):
        """GET /ml/registry/{model_type} returns list of version dicts."""
        fake_versions = [
            {"version": "eta_prediction_v1", "status": "deprecated"},
            {"version": "eta_prediction_v2", "status": "active"},
        ]
        with patch("app.ml.router.ModelRegistry.list_versions", return_value=fake_versions) as mock_lv:
            resp = _client(db_session).get("/ml/registry/eta_prediction")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        assert body[1]["status"] == "active"
        mock_lv.assert_called_once_with("eta_prediction")

    def test_list_model_versions_empty(self, db_session):
        """GET /ml/registry/unknown_type returns empty list."""
        with patch("app.ml.router.ModelRegistry.list_versions", return_value=[]):
            resp = _client(db_session).get("/ml/registry/unknown_type")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_rollback_model_success(self, db_session):
        """POST /ml/registry/{model_type}/rollback/{version_num} returns rolled_back status."""
        with patch("app.ml.router.ModelRegistry.rollback", return_value="eta_prediction_v1"):
            resp = _client(db_session).post("/ml/registry/eta_prediction/rollback/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "rolled_back"
        assert body["latest_version"] == "eta_prediction_v1"

    def test_rollback_model_not_found(self, db_session):
        """POST rollback returns 404 when ModelRegistry.rollback returns None."""
        with patch("app.ml.router.ModelRegistry.rollback", return_value=None):
            resp = _client(db_session).post("/ml/registry/eta_prediction/rollback/99")
        assert resp.status_code == 404
        assert "Version not found" in resp.json()["detail"]

    def test_rollback_uses_correct_args(self, db_session):
        """POST rollback passes model_type and version_num to ModelRegistry.rollback."""
        with patch("app.ml.router.ModelRegistry.rollback", return_value="v2") as mock_rb:
            _client(db_session).post("/ml/registry/fraud_detection/rollback/3")
        mock_rb.assert_called_once_with("fraud_detection", 3)


# ══════════════════════════════════════════════════════════════════════════
# 2. Training Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestTrainingEndpoints:
    """POST /ml/train/* endpoints — lazy-imported functions are mocked."""

    def test_train_all_models(self, db_session):
        """POST /ml/train/all calls run_full_training_pipeline and returns result."""
        fake_result = {"status": "success", "models_trained": 5}
        with patch("app.ml.training_pipeline.run_full_training_pipeline", return_value=fake_result):
            resp = _client(db_session).post("/ml/train/all")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["models_trained"] == 5

    def test_train_all_models_with_days_param(self, db_session):
        """POST /ml/train/all?days=30 passes days to the pipeline."""
        captured = {}
        def fake_pipeline(db, days):
            captured["days"] = days
            return {"status": "success"}
        with patch("app.ml.training_pipeline.run_full_training_pipeline", side_effect=fake_pipeline):
            resp = _client(db_session).post("/ml/train/all?days=30")
        assert resp.status_code == 200
        assert captured["days"] == 30

    def test_train_eta(self, db_session):
        """POST /ml/train/eta calls train_eta_models."""
        fake = {"status": "success", "best_model": "xgboost"}
        with patch("app.ml.training_pipeline.train_eta_models", return_value=fake):
            resp = _client(db_session).post("/ml/train/eta")
        assert resp.status_code == 200
        assert resp.json()["best_model"] == "xgboost"

    def test_train_eta_with_days_param(self, db_session):
        """POST /ml/train/eta?days=60 passes days param."""
        captured = {}
        def fake_train(db, days):
            captured["days"] = days
            return {"status": "success"}
        with patch("app.ml.training_pipeline.train_eta_models", side_effect=fake_train):
            resp = _client(db_session).post("/ml/train/eta?days=60")
        assert resp.status_code == 200
        assert captured["days"] == 60

    def test_train_demand(self, db_session):
        """POST /ml/train/demand/{vendor_id} calls train_demand_forecast."""
        fake = {"status": "success", "vendor_id": 7}
        with patch("app.ml.training_pipeline.train_demand_forecast", return_value=fake):
            resp = _client(db_session, _REGULAR_USER).post("/ml/train/demand/7")
        assert resp.status_code == 200
        assert resp.json()["vendor_id"] == 7

    def test_train_demand_passes_vendor_id(self, db_session):
        """POST /ml/train/demand/42 passes vendor_id=42."""
        captured = {}
        def fake_demand(db, vendor_id, days):
            captured["vendor_id"] = vendor_id
            return {"status": "success"}
        with patch("app.ml.training_pipeline.train_demand_forecast", side_effect=fake_demand):
            _client(db_session, _REGULAR_USER).post("/ml/train/demand/42")
        assert captured["vendor_id"] == 42

    def test_train_fraud(self, db_session):
        """POST /ml/train/fraud calls train_fraud_detection."""
        fake = {"status": "success", "model": "fraud_detection"}
        with patch("app.ml.training_pipeline.train_fraud_detection", return_value=fake):
            resp = _client(db_session).post("/ml/train/fraud")
        assert resp.status_code == 200
        assert resp.json()["model"] == "fraud_detection"

    def test_train_vendor_ranking(self, db_session):
        """POST /ml/train/vendor-ranking calls train_vendor_ranking."""
        fake = {"status": "success", "model": "vendor_ranking"}
        with patch("app.ml.training_pipeline.train_vendor_ranking", return_value=fake):
            resp = _client(db_session).post("/ml/train/vendor-ranking")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    def test_train_slot_recommendation(self, db_session):
        """POST /ml/train/slot-recommendation calls train_slot_recommendation."""
        fake = {"status": "success", "model": "slot_recommendation"}
        with patch("app.ml.training_pipeline.train_slot_recommendation", return_value=fake):
            resp = _client(db_session).post("/ml/train/slot-recommendation")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"


# ══════════════════════════════════════════════════════════════════════════
# 3. Retraining Service Endpoint (first POST /retrain route)
# ══════════════════════════════════════════════════════════════════════════

class TestRetrainingServiceEndpoint:
    """POST /retrain — the first registered /retrain route calls RetrainingService."""

    def test_retrain_all_via_service(self, db_session):
        """POST /ml/retrain calls RetrainingService.retrain_all."""
        fake_result = {"status": "ok", "retrained": ["eta_prediction"]}
        mock_service = MagicMock()
        mock_service.retrain_all.return_value = fake_result
        with patch("app.ml.router._get_retraining_service", return_value=mock_service):
            resp = _client(db_session).post("/ml/retrain")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_service.retrain_all.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════
# 4. Prediction Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestPredictionEndpoints:
    """GET /ml/predict/eta, /ml/forecast/demand, /ml/recommend/*, /ml/rank/vendors,
    /ml/detect/fraud"""

    def _make_service_mock(self, method: str, return_value: Any) -> MagicMock:
        mock = MagicMock()
        getattr(mock, method).return_value = return_value
        return mock

    def test_predict_eta(self, db_session):
        """GET /ml/predict/eta returns ETA prediction dict."""
        fake = {"predicted_eta_minutes": 22.5, "confidence": 0.87, "model": "xgboost"}
        mock_svc = self._make_service_mock("predict_eta", fake)
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/predict/eta?vendor_id=1&slot_id=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["predicted_eta_minutes"] == 22.5
        assert body["confidence"] == 0.87
        mock_svc.predict_eta.assert_called_once_with(1, 2, 1)  # default item_count=1

    def test_predict_eta_with_item_count(self, db_session):
        """GET /ml/predict/eta?item_count=5 passes item_count to service."""
        fake = {"predicted_eta_minutes": 30.0}
        captured = {}
        def fake_predict(vendor_id, slot_id, item_count):
            captured["item_count"] = item_count
            return fake
        mock_svc = MagicMock()
        mock_svc.predict_eta.side_effect = fake_predict
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            _client(db_session, _REGULAR_USER).get("/ml/predict/eta?vendor_id=1&slot_id=2&item_count=5")
        assert captured["item_count"] == 5

    def test_predict_eta_missing_required_params(self, db_session):
        """GET /ml/predict/eta without vendor_id/slot_id returns 422."""
        resp = _client(db_session, _REGULAR_USER).get("/ml/predict/eta")
        assert resp.status_code == 422

    def test_forecast_demand(self, db_session):
        """GET /ml/forecast/demand returns forecast dict."""
        fake = {"vendor_id": 3, "forecast": [100, 200, 150], "days": 3}
        mock_svc = self._make_service_mock("forecast_demand", fake)
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/forecast/demand?vendor_id=3&days=3")
        assert resp.status_code == 200
        assert resp.json()["vendor_id"] == 3
        mock_svc.forecast_demand.assert_called_once_with(3, 3)

    def test_forecast_demand_default_days(self, db_session):
        """GET /ml/forecast/demand?vendor_id=5 uses days=7 default."""
        captured = {}
        def fake_forecast(vendor_id, days):
            captured["days"] = days
            return {"forecast": []}
        mock_svc = MagicMock()
        mock_svc.forecast_demand.side_effect = fake_forecast
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            _client(db_session, _REGULAR_USER).get("/ml/forecast/demand?vendor_id=5")
        assert captured["days"] == 7

    def test_recommend_slots(self, db_session):
        """GET /ml/recommend/slots returns slot recommendations."""
        fake = {"slots": [{"slot_id": 1, "score": 0.9}], "user_id": 2}
        mock_svc = self._make_service_mock("recommend_slot", fake)
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/recommend/slots")
        assert resp.status_code == 200
        mock_svc.recommend_slot.assert_called_once_with(2)  # user id from _REGULAR_USER

    def test_get_personalized_recs(self, db_session):
        """GET /ml/recommend/personalized returns recommendations."""
        fake = {"items": ["item_a", "item_b"], "user_id": 2}
        mock_svc = self._make_service_mock("get_personalized_recommendations", fake)
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/recommend/personalized")
        assert resp.status_code == 200
        assert "items" in resp.json()
        mock_svc.get_personalized_recommendations.assert_called_once_with(2)

    def test_rank_vendors(self, db_session):
        """GET /ml/rank/vendors returns a list of ranked vendors."""
        fake = [
            {"vendor_id": 1, "score": 9.5},
            {"vendor_id": 2, "score": 8.1},
        ]
        mock_svc = self._make_service_mock("rank_vendors", fake)
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/rank/vendors")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert body[0]["score"] == 9.5

    def test_detect_fraud(self, db_session):
        """GET /ml/detect/fraud returns fraud detection result."""
        fake = {"fraud_probability": 0.92, "is_fraud": True, "user_id": 5, "order_id": 10}
        mock_svc = self._make_service_mock("detect_fraud", fake)
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session).get("/ml/detect/fraud?user_id=5&order_id=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["is_fraud"] is True
        assert body["fraud_probability"] == 0.92
        mock_svc.detect_fraud.assert_called_once_with(5, 10)

    def test_detect_fraud_missing_params(self, db_session):
        """GET /ml/detect/fraud without required params returns 422."""
        resp = _client(db_session).get("/ml/detect/fraud")
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════
# 5. Explainability Endpoint
# ══════════════════════════════════════════════════════════════════════════

class TestExplainabilityEndpoint:
    """GET /ml/explain/{model_type}"""

    def test_explain_model_found(self, db_session):
        """GET /ml/explain/eta_prediction returns feature importance when model loaded."""
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        model = RandomForestRegressor(n_estimators=5, random_state=0)
        model.fit(np.array([[1, 2], [3, 4], [5, 6]]), [10, 20, 30])
        metadata = {
            "version_id": "eta_prediction_v3",
            "features": ["f1", "f2"],
            "metrics": {"rmse": 1.5},
        }
        fake_importance = [
            {"feature": "f1", "importance": 0.7},
            {"feature": "f2", "importance": 0.3},
        ]
        with (
            patch("app.ml.router.ModelRegistry.load", return_value=(model, metadata)),
            patch("app.ml.explain.get_feature_importance", return_value=fake_importance),
        ):
            resp = _client(db_session).get("/ml/explain/eta_prediction")
        assert resp.status_code == 200
        body = resp.json()
        assert body["model_type"] == "eta_prediction"
        assert body["version_id"] == "eta_prediction_v3"
        assert "feature_importance" in body
        assert "metrics" in body

    def test_explain_model_not_found(self, db_session):
        """GET /ml/explain/nonexistent returns 404."""
        with patch("app.ml.router.ModelRegistry.load", return_value=None):
            resp = _client(db_session).get("/ml/explain/nonexistent_model")
        assert resp.status_code == 404
        assert "No model found" in resp.json()["detail"]

    def test_explain_uses_metadata_features(self, db_session):
        """Feature names from metadata are passed to get_feature_importance."""
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        model = RandomForestRegressor(n_estimators=5, random_state=0)
        model.fit(np.array([[1, 2], [3, 4]]), [10, 20])
        metadata = {"version_id": "v1", "features": ["speed", "rating"], "metrics": {}}
        captured = {}
        def fake_gfi(m, feature_names):
            captured["features"] = feature_names
            return []
        with (
            patch("app.ml.router.ModelRegistry.load", return_value=(model, metadata)),
            patch("app.ml.explain.get_feature_importance", side_effect=fake_gfi),
        ):
            _client(db_session).get("/ml/explain/eta_prediction")
        assert captured["features"] == ["speed", "rating"]

    def test_explain_model_no_features_in_metadata(self, db_session):
        """If metadata has no 'features' key, feature_names defaults to []."""
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        model = RandomForestRegressor(n_estimators=5, random_state=0)
        model.fit(np.array([[1], [2], [3]]), [10, 20, 30])
        metadata = {"version_id": "v1"}  # no 'features' key
        captured = {}
        def fake_gfi(m, feature_names):
            captured["features"] = feature_names
            return []
        with (
            patch("app.ml.router.ModelRegistry.load", return_value=(model, metadata)),
            patch("app.ml.explain.get_feature_importance", side_effect=fake_gfi),
        ):
            _client(db_session).get("/ml/explain/eta_prediction")
        assert captured["features"] == []


# ══════════════════════════════════════════════════════════════════════════
# 6. Accuracy Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestAccuracyEndpoints:
    """GET /ml/accuracy/summary, GET /ml/accuracy/{model_type}

    These call _get_combined_accuracy which hits:
      - ModelRegistry.compare_versions
      - backtest_eta / backtest_vendor_ranking
      - DriftReport DB query
      - ModelRegistry.load + get_feature_importance (try/except)
    """

    # ── helpers ────────────────────────────────────────────────────────────

    def _patch_combined(self, return_value: dict):
        """Patch _get_combined_accuracy at the router module level."""
        return patch("app.ml.router._get_combined_accuracy", return_value=return_value)

    def _seed_drift_report(self, db_session, model_type: str, has_drift: bool = False):
        """Insert a DriftReport row into the test SQLite DB."""
        from app.ml.drift_report_model import DriftReport
        report = DriftReport(
            model_type=model_type,
            check_type="data_drift",
            has_drift=has_drift,
            report_data={"drifted_features": [], "feature_psi": {}},
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(report)
        db_session.commit()
        return report

    # ── accuracy/summary ───────────────────────────────────────────────────

    def test_accuracy_summary_calls_all_model_types(self, db_session):
        """GET /ml/accuracy/summary returns dict with all 5 model type keys."""
        model_types = [
            "eta_prediction", "demand_forecast",
            "slot_recommendation", "vendor_ranking", "fraud_detection",
        ]
        fake_entry = {"model_type": "x", "active_version": None, "versions": [],
                      "latest_backtest": None, "latest_drift": None, "feature_importance": []}

        with self._patch_combined(fake_entry):
            resp = _client(db_session).get("/ml/accuracy/summary")
        assert resp.status_code == 200
        body = resp.json()
        for mt in model_types:
            assert mt in body, f"Expected '{mt}' key in accuracy summary"

    def test_accuracy_summary_shape(self, db_session):
        """Each entry in summary has the expected keys."""
        fake_entry = {
            "model_type": "eta_prediction",
            "active_version": {"version": "v2"},
            "versions": [],
            "latest_backtest": {"status": "success"},
            "latest_drift": {"has_drift": False},
            "feature_importance": [],
        }
        with self._patch_combined(fake_entry):
            resp = _client(db_session).get("/ml/accuracy/summary")
        body = resp.json()
        entry = body["eta_prediction"]
        assert entry["model_type"] == "eta_prediction"
        assert "active_version" in entry
        assert "latest_backtest" in entry
        assert "latest_drift" in entry

    # ── accuracy/{model_type} ─────────────────────────────────────────────

    def test_accuracy_single_model_type(self, db_session):
        """GET /ml/accuracy/eta_prediction returns accuracy for that model."""
        fake = {"model_type": "eta_prediction", "versions": [], "latest_drift": None}
        with self._patch_combined(fake):
            resp = _client(db_session).get("/ml/accuracy/eta_prediction")
        assert resp.status_code == 200
        assert resp.json()["model_type"] == "eta_prediction"

    def test_accuracy_passes_correct_model_type(self, db_session):
        """GET /ml/accuracy/{model_type} passes model_type to _get_combined_accuracy."""
        captured = {}
        def fake_combined(model_type, db):
            captured["model_type"] = model_type
            return {"model_type": model_type}
        with patch("app.ml.router._get_combined_accuracy", side_effect=fake_combined):
            _client(db_session).get("/ml/accuracy/fraud_detection")
        assert captured["model_type"] == "fraud_detection"

    # ── _get_combined_accuracy internals (tested directly) ─────────────────

    def test_combined_accuracy_no_versions_no_drift(self, db_session):
        """_get_combined_accuracy with empty registry and no DriftReport rows."""
        from app.ml.router import _get_combined_accuracy
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.backtest.backtest_eta", return_value={"status": "insufficient_data"}),
            patch("app.ml.router.ModelRegistry.load", return_value=None),
        ):
            result = _get_combined_accuracy("eta_prediction", db_session)
        assert result["model_type"] == "eta_prediction"
        assert result["active_version"] is None
        assert result["versions"] == []
        assert result["latest_backtest"]["status"] == "insufficient_data"
        # No drift report → default has_drift=False
        assert result["latest_drift"]["has_drift"] is False
        assert result["latest_drift"]["created_at"] is None

    def test_combined_accuracy_with_drift_row(self, db_session):
        """_get_combined_accuracy picks up a DriftReport row from the DB."""
        from app.ml.router import _get_combined_accuracy
        self._seed_drift_report(db_session, "demand_forecast", has_drift=True)
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.router.ModelRegistry.load", return_value=None),
        ):
            result = _get_combined_accuracy("demand_forecast", db_session)
        assert result["latest_drift"]["has_drift"] is True
        assert result["latest_drift"]["created_at"] is not None

    def test_combined_accuracy_active_version_fallback(self, db_session):
        """When no 'active' version, _get_combined_accuracy falls back to versions[0]."""
        from app.ml.router import _get_combined_accuracy
        versions = [
            {"version": "v1", "status": "deprecated"},
            {"version": "v2", "status": "deprecated"},
        ]
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=versions),
            patch("app.ml.router.ModelRegistry.load", return_value=None),
        ):
            result = _get_combined_accuracy("slot_recommendation", db_session)
        # No "active" status in either → fallback to versions[0]
        assert result["active_version"] == versions[0]

    def test_combined_accuracy_vendor_ranking_backtest(self, db_session):
        """_get_combined_accuracy triggers backtest_vendor_ranking for vendor_ranking model."""
        from app.ml.router import _get_combined_accuracy
        fake_bt = {"status": "success", "top_1_hit_rate": 0.85}
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.backtest.backtest_vendor_ranking", return_value=fake_bt) as mock_bt,
            patch("app.ml.router.ModelRegistry.load", return_value=None),
        ):
            result = _get_combined_accuracy("vendor_ranking", db_session)
        mock_bt.assert_called_once()
        assert result["latest_backtest"] == fake_bt

    def test_combined_accuracy_no_backtest_for_other_models(self, db_session):
        """_get_combined_accuracy returns latest_backtest=None for non-backtest model types."""
        from app.ml.router import _get_combined_accuracy
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.router.ModelRegistry.load", return_value=None),
        ):
            result = _get_combined_accuracy("fraud_detection", db_session)
        assert result["latest_backtest"] is None

    def test_combined_accuracy_feature_importance_loaded(self, db_session):
        """_get_combined_accuracy includes feature_importance when model loads OK."""
        from app.ml.router import _get_combined_accuracy
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        model = RandomForestRegressor(n_estimators=5, random_state=0)
        model.fit(np.array([[1, 2], [3, 4]]), [10, 20])
        metadata = {"features": ["a", "b"], "metrics": {}}
        fake_fi = [{"feature": "a", "importance": 0.6}]
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.router.ModelRegistry.load", return_value=(model, metadata)),
            patch("app.ml.explain.get_feature_importance", return_value=fake_fi),
        ):
            result = _get_combined_accuracy("slot_recommendation", db_session)
        assert result["feature_importance"] == fake_fi

    def test_combined_accuracy_feature_importance_exception(self, db_session):
        """_get_combined_accuracy gracefully falls back to [] on get_feature_importance error."""
        from app.ml.router import _get_combined_accuracy
        from sklearn.ensemble import RandomForestRegressor
        import numpy as np
        model = RandomForestRegressor(n_estimators=5, random_state=0)
        model.fit(np.array([[1, 2], [3, 4]]), [10, 20])
        metadata = {"features": [], "metrics": {}}
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.router.ModelRegistry.load", return_value=(model, metadata)),
            patch("app.ml.explain.get_feature_importance", side_effect=RuntimeError("SHAP fail")),
        ):
            result = _get_combined_accuracy("slot_recommendation", db_session)
        assert result["feature_importance"] == []


# ══════════════════════════════════════════════════════════════════════════
# 7. Backtesting Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestBacktestEndpoints:
    """GET /ml/backtest/eta, GET /ml/backtest/vendor-ranking,
    POST /ml/shadow-log/backfill"""

    def test_backtest_eta(self, db_session):
        """GET /ml/backtest/eta returns backtest result dict."""
        fake = {"status": "success", "mae_minutes": 2.3, "total_orders": 50}
        with patch("app.ml.backtest.backtest_eta", return_value=fake):
            resp = _client(db_session).get("/ml/backtest/eta")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["mae_minutes"] == 2.3

    def test_backtest_eta_days_param(self, db_session):
        """GET /ml/backtest/eta?days=14 passes days=14 to backtest_eta."""
        captured = {}
        def fake_bt(db, days):
            captured["days"] = days
            return {"status": "success"}
        with patch("app.ml.backtest.backtest_eta", side_effect=fake_bt):
            _client(db_session).get("/ml/backtest/eta?days=14")
        assert captured["days"] == 14

    def test_backtest_eta_default_days(self, db_session):
        """GET /ml/backtest/eta default days=30."""
        captured = {}
        def fake_bt(db, days):
            captured["days"] = days
            return {"status": "success"}
        with patch("app.ml.backtest.backtest_eta", side_effect=fake_bt):
            _client(db_session).get("/ml/backtest/eta")
        assert captured["days"] == 30

    def test_backtest_vendor_ranking(self, db_session):
        """GET /ml/backtest/vendor-ranking returns ranking backtest dict."""
        fake = {"status": "success", "top_1_hit_rate": 0.75, "total_orders": 40}
        with patch("app.ml.backtest.backtest_vendor_ranking", return_value=fake):
            resp = _client(db_session).get("/ml/backtest/vendor-ranking")
        assert resp.status_code == 200
        assert resp.json()["top_1_hit_rate"] == 0.75

    def test_backtest_vendor_ranking_days_param(self, db_session):
        """GET /ml/backtest/vendor-ranking?days=60 passes days=60."""
        captured = {}
        def fake_bt(db, days):
            captured["days"] = days
            return {"status": "success"}
        with patch("app.ml.backtest.backtest_vendor_ranking", side_effect=fake_bt):
            _client(db_session).get("/ml/backtest/vendor-ranking?days=60")
        assert captured["days"] == 60

    def test_backfill_shadow_log(self, db_session):
        """POST /ml/shadow-log/backfill calls backfill_shadow_actuals."""
        fake = {"updated": 10, "errors": 0}
        with patch("app.ml.backtest.backfill_shadow_actuals", return_value=fake):
            resp = _client(db_session).post("/ml/shadow-log/backfill")
        assert resp.status_code == 200
        assert resp.json()["updated"] == 10


# ══════════════════════════════════════════════════════════════════════════
# 8. Drift Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestDriftEndpoints:
    """POST /ml/drift/check, GET /ml/drift/reports"""

    def _seed_drift_report(
        self,
        db_session,
        model_type: str = "eta_prediction",
        has_drift: bool = False,
        check_type: str = "data_drift",
        report_data: dict | None = None,
    ):
        from app.ml.drift_report_model import DriftReport
        row = DriftReport(
            model_type=model_type,
            check_type=check_type,
            has_drift=has_drift,
            report_data=report_data or {},
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row

    # ── POST /ml/drift/check ───────────────────────────────────────────────

    def test_run_drift_checks(self, db_session):
        """POST /ml/drift/check calls run_all_drift_checks."""
        fake = {"eta_prediction": {"has_drift": False}, "demand_forecast": {"has_drift": True}}
        with patch("app.ml.drift.run_all_drift_checks", return_value=fake):
            resp = _client(db_session).post("/ml/drift/check")
        assert resp.status_code == 200
        body = resp.json()
        assert "eta_prediction" in body
        assert body["demand_forecast"]["has_drift"] is True

    def test_run_drift_checks_lookback_param(self, db_session):
        """POST /ml/drift/check?lookback_days=14 passes lookback_days=14."""
        captured = {}
        def fake_drift(db, lookback_days):
            captured["lookback_days"] = lookback_days
            return {}
        with patch("app.ml.drift.run_all_drift_checks", side_effect=fake_drift):
            _client(db_session).post("/ml/drift/check?lookback_days=14")
        assert captured["lookback_days"] == 14

    def test_run_drift_checks_default_lookback(self, db_session):
        """POST /ml/drift/check without param uses default lookback_days=7."""
        captured = {}
        def fake_drift(db, lookback_days):
            captured["lookback_days"] = lookback_days
            return {}
        with patch("app.ml.drift.run_all_drift_checks", side_effect=fake_drift):
            _client(db_session).post("/ml/drift/check")
        assert captured["lookback_days"] == 7

    # ── GET /ml/drift/reports ─────────────────────────────────────────────

    def test_get_drift_reports_all(self, db_session):
        """GET /ml/drift/reports returns all drift report rows."""
        self._seed_drift_report(db_session, "eta_prediction", False)
        self._seed_drift_report(db_session, "demand_forecast", True)
        resp = _client(db_session).get("/ml/drift/reports")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        # Check response shape
        assert "id" in body[0]
        assert "model_type" in body[0]
        assert "check_type" in body[0]
        assert "has_drift" in body[0]
        assert "report_data" in body[0]
        assert "created_at" in body[0]

    def test_get_drift_reports_filtered_by_model_type(self, db_session):
        """GET /ml/drift/reports?model_type=eta_prediction filters correctly."""
        self._seed_drift_report(db_session, "eta_prediction")
        self._seed_drift_report(db_session, "demand_forecast")
        resp = _client(db_session).get("/ml/drift/reports?model_type=eta_prediction")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["model_type"] == "eta_prediction"

    def test_get_drift_reports_empty(self, db_session):
        """GET /ml/drift/reports with no rows returns empty list."""
        resp = _client(db_session).get("/ml/drift/reports")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_drift_reports_limit(self, db_session):
        """GET /ml/drift/reports?limit=1 caps results to 1 row."""
        for i in range(3):
            self._seed_drift_report(db_session, "eta_prediction")
        resp = _client(db_session).get("/ml/drift/reports?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_drift_reports_has_drift_field(self, db_session):
        """Reports include the correct has_drift boolean."""
        self._seed_drift_report(db_session, "eta_prediction", has_drift=True)
        resp = _client(db_session).get("/ml/drift/reports")
        body = resp.json()
        assert body[0]["has_drift"] is True


# ══════════════════════════════════════════════════════════════════════════
# 9. Scheduled Retraining & Retraining Logs Endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestRetrainingLogEndpoints:
    """POST /ml/retrain (second route / trigger_ml_retraining)
    GET  /ml/retrain/logs"""

    def _seed_log(
        self,
        db_session,
        model_type: str = "eta_prediction",
        status: str = "success",
        version_id: str | None = "eta_prediction_v3",
        error_message: str | None = None,
    ):
        from app.ml.retraining_log_model import RetrainingLog
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        row = RetrainingLog(
            model_type=model_type,
            triggered_at=now,
            status=status,
            version_id=version_id,
            error_message=error_message,
            created_at=now,
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        return row

    # ── GET /ml/retrain/logs ───────────────────────────────────────────────

    def test_get_retraining_logs_all(self, db_session):
        """GET /ml/retrain/logs returns all log entries."""
        self._seed_log(db_session, "eta_prediction", "success")
        self._seed_log(db_session, "demand_forecast", "failed", None, "OOM error")
        resp = _client(db_session).get("/ml/retrain/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 2
        # Verify response shape
        row = body[0]
        assert "id" in row
        assert "model_type" in row
        assert "triggered_at" in row
        assert "status" in row
        assert "version_id" in row
        assert "error_message" in row
        assert "created_at" in row

    def test_get_retraining_logs_filtered(self, db_session):
        """GET /ml/retrain/logs?model_type=demand_forecast filters correctly."""
        self._seed_log(db_session, "eta_prediction", "success")
        self._seed_log(db_session, "demand_forecast", "failed")
        resp = _client(db_session).get("/ml/retrain/logs?model_type=demand_forecast")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["model_type"] == "demand_forecast"
        assert body[0]["status"] == "failed"

    def test_get_retraining_logs_empty(self, db_session):
        """GET /ml/retrain/logs with no rows returns empty list."""
        resp = _client(db_session).get("/ml/retrain/logs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_retraining_logs_limit(self, db_session):
        """GET /ml/retrain/logs?limit=1 caps results to 1 row."""
        for _ in range(3):
            self._seed_log(db_session)
        resp = _client(db_session).get("/ml/retrain/logs?limit=1")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_retraining_logs_error_message_included(self, db_session):
        """Error message is included in log entries."""
        self._seed_log(db_session, status="failed", error_message="DB connection lost")
        resp = _client(db_session).get("/ml/retrain/logs")
        body = resp.json()
        assert body[0]["error_message"] == "DB connection lost"

    def test_get_retraining_logs_version_id_null_for_failed(self, db_session):
        """version_id is None for failed retraining attempts."""
        self._seed_log(db_session, status="failed", version_id=None)
        resp = _client(db_session).get("/ml/retrain/logs")
        body = resp.json()
        assert body[0]["version_id"] is None

    # ── POST /ml/retrain (trigger_ml_retraining) ──────────────────────────
    # NOTE: The first registered /ml/retrain route is retrain_all (line 135)
    # which calls RetrainingService. FastAPI routes are matched in registration
    # order, so POST /ml/retrain → retrain_all. The second definition
    # (trigger_ml_retraining at line 411) is shadowed by the first in the
    # router — both code paths are tested via _get_retraining_service mock.

    def test_trigger_retraining_via_service(self, db_session):
        """POST /ml/retrain calls _get_retraining_service().retrain_all()."""
        fake = {"status": "ok", "retrained": ["eta_prediction", "demand_forecast"]}
        mock_service = MagicMock()
        mock_service.retrain_all.return_value = fake
        with patch("app.ml.router._get_retraining_service", return_value=mock_service):
            resp = _client(db_session).post("/ml/retrain")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        mock_service.retrain_all.assert_called_once()

    def test_trigger_ml_retraining_function_directly(self, db_session):
        """Direct call to trigger_ml_retraining function covering lines 418-419."""
        from app.ml.router import trigger_ml_retraining
        fake = {"status": "ok"}
        with patch("app.ml.retraining.run_scheduled_retraining", return_value=fake) as mock_retrain:
            result = trigger_ml_retraining(model_types=["eta_prediction"], db=db_session, user=_ADMIN_USER)
        assert result == fake
        mock_retrain.assert_called_once_with(model_types=["eta_prediction"], db=db_session)



# ══════════════════════════════════════════════════════════════════════════
# 10. Auth / Role Guard Tests
# ══════════════════════════════════════════════════════════════════════════

class TestAuthGuards:
    """Verify admin-gated routes reject non-admin users (role=403)
    and that user-gated routes accept customer role."""

    def test_registry_requires_admin(self, db_session):
        """GET /ml/registry with non-admin user returns 403."""
        with patch("app.ml.router.ModelRegistry.get_registry_summary", return_value={}):
            resp = _client(db_session, _REGULAR_USER).get("/ml/registry")
        assert resp.status_code == 403

    def test_registry_model_type_requires_admin(self, db_session):
        """GET /ml/registry/eta_prediction with customer role returns 403."""
        with patch("app.ml.router.ModelRegistry.list_versions", return_value=[]):
            resp = _client(db_session, _REGULAR_USER).get("/ml/registry/eta_prediction")
        assert resp.status_code == 403

    def test_rollback_requires_admin(self, db_session):
        """POST /ml/registry/rollback with customer role returns 403."""
        with patch("app.ml.router.ModelRegistry.rollback", return_value="v1"):
            resp = _client(db_session, _REGULAR_USER).post("/ml/registry/eta_prediction/rollback/1")
        assert resp.status_code == 403

    def test_train_all_requires_admin(self, db_session):
        """POST /ml/train/all with customer role returns 403."""
        with patch("app.ml.training_pipeline.run_full_training_pipeline", return_value={}):
            resp = _client(db_session, _REGULAR_USER).post("/ml/train/all")
        assert resp.status_code == 403

    def test_detect_fraud_requires_admin(self, db_session):
        """GET /ml/detect/fraud with customer role returns 403."""
        with patch("app.ml.router._get_ml_service", return_value=MagicMock(detect_fraud=MagicMock(return_value={}))):
            resp = _client(db_session, _REGULAR_USER).get("/ml/detect/fraud?user_id=1&order_id=1")
        assert resp.status_code == 403

    def test_explain_requires_admin(self, db_session):
        """GET /ml/explain/{model_type} with customer role returns 403."""
        with patch("app.ml.router.ModelRegistry.load", return_value=None):
            resp = _client(db_session, _REGULAR_USER).get("/ml/explain/eta_prediction")
        assert resp.status_code == 403

    def test_accuracy_summary_requires_admin(self, db_session):
        """GET /ml/accuracy/summary with customer role returns 403."""
        with patch("app.ml.router._get_combined_accuracy", return_value={}):
            resp = _client(db_session, _REGULAR_USER).get("/ml/accuracy/summary")
        assert resp.status_code == 403

    def test_backtest_eta_requires_admin(self, db_session):
        """GET /ml/backtest/eta with customer role returns 403."""
        with patch("app.ml.backtest.backtest_eta", return_value={}):
            resp = _client(db_session, _REGULAR_USER).get("/ml/backtest/eta")
        assert resp.status_code == 403

    def test_drift_check_requires_admin(self, db_session):
        """POST /ml/drift/check with customer role returns 403."""
        with patch("app.ml.drift.run_all_drift_checks", return_value={}):
            resp = _client(db_session, _REGULAR_USER).post("/ml/drift/check")
        assert resp.status_code == 403

    def test_drift_reports_requires_admin(self, db_session):
        """GET /ml/drift/reports with customer role returns 403."""
        resp = _client(db_session, _REGULAR_USER).get("/ml/drift/reports")
        assert resp.status_code == 403

    def test_retrain_logs_requires_admin(self, db_session):
        """GET /ml/retrain/logs with customer role returns 403."""
        resp = _client(db_session, _REGULAR_USER).get("/ml/retrain/logs")
        assert resp.status_code == 403

    def test_predict_eta_allows_customer(self, db_session):
        """GET /ml/predict/eta with customer role is allowed (get_current_user)."""
        fake = {"predicted_eta_minutes": 15.0}
        mock_svc = MagicMock()
        mock_svc.predict_eta.return_value = fake
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/predict/eta?vendor_id=1&slot_id=1")
        assert resp.status_code == 200

    def test_forecast_demand_allows_customer(self, db_session):
        """GET /ml/forecast/demand with customer role is allowed."""
        fake = {"forecast": []}
        mock_svc = MagicMock()
        mock_svc.forecast_demand.return_value = fake
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/forecast/demand?vendor_id=1")
        assert resp.status_code == 200

    def test_recommend_slots_allows_customer(self, db_session):
        """GET /ml/recommend/slots with customer role is allowed."""
        mock_svc = MagicMock()
        mock_svc.recommend_slot.return_value = {"slots": []}
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/recommend/slots")
        assert resp.status_code == 200

    def test_rank_vendors_allows_customer(self, db_session):
        """GET /ml/rank/vendors with customer role is allowed."""
        mock_svc = MagicMock()
        mock_svc.rank_vendors.return_value = []
        with patch("app.ml.router._get_ml_service", return_value=mock_svc):
            resp = _client(db_session, _REGULAR_USER).get("/ml/rank/vendors")
        assert resp.status_code == 200

    def test_admin_role_allows_admin_routes(self, db_session):
        """Admin user can access admin-gated routes."""
        with patch("app.ml.router.ModelRegistry.get_registry_summary", return_value={"x": 1}):
            resp = _client(db_session, _ADMIN_USER).get("/ml/registry")
        assert resp.status_code == 200

    def test_super_admin_also_allowed(self, db_session):
        """super_admin role is also accepted for admin-gated routes."""
        super_admin = {**_ADMIN_USER, "role": "super_admin"}
        with patch("app.ml.router.ModelRegistry.get_registry_summary", return_value={}):
            resp = _client(db_session, super_admin).get("/ml/registry")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════
# 11. Router Infrastructure Tests
# ══════════════════════════════════════════════════════════════════════════

class TestRouterInfrastructure:
    """Test the internal helpers _get_ml_service and _get_retraining_service."""

    def test_get_ml_service_returns_prediction_service(self, db_session):
        """_get_ml_service returns an MLPredictionService instance."""
        from app.ml.router import _get_ml_service
        svc = _get_ml_service(db_session)
        from app.ml.predictions import MLPredictionService
        assert isinstance(svc, MLPredictionService)

    def test_get_retraining_service_returns_service(self):
        """_get_retraining_service returns a RetrainingService instance."""
        from app.ml.router import _get_retraining_service
        svc = _get_retraining_service()
        from app.ml.training_pipeline import RetrainingService
        assert isinstance(svc, RetrainingService)

    def test_router_prefix_is_ml(self):
        """The router prefix is '/ml'."""
        from app.ml.router import router as ml_router
        assert ml_router.prefix == "/ml"

    def test_router_has_all_expected_routes(self):
        """All expected route paths are registered."""
        from app.ml.router import router as ml_router
        paths = {r.path for r in ml_router.routes}
        expected = {
            "/ml/registry",
            "/ml/registry/{model_type}",
            "/ml/registry/{model_type}/rollback/{version_num}",
            "/ml/train/all",
            "/ml/train/eta",
            "/ml/train/demand/{vendor_id}",
            "/ml/train/fraud",
            "/ml/train/vendor-ranking",
            "/ml/train/slot-recommendation",
            "/ml/retrain",
            "/ml/predict/eta",
            "/ml/forecast/demand",
            "/ml/recommend/slots",
            "/ml/recommend/personalized",
            "/ml/rank/vendors",
            "/ml/detect/fraud",
            "/ml/explain/{model_type}",
            "/ml/accuracy/summary",
            "/ml/accuracy/{model_type}",
            "/ml/backtest/eta",
            "/ml/backtest/vendor-ranking",
            "/ml/shadow-log/backfill",
            "/ml/drift/check",
            "/ml/drift/reports",
            "/ml/retrain/logs",
        }
        missing = expected - paths
        assert not missing, f"Routes missing from router: {missing}"


# ══════════════════════════════════════════════════════════════════════════
# 12. Invalid Model-Type Edge Cases
# ══════════════════════════════════════════════════════════════════════════

class TestInvalidModelType:
    """Verify graceful handling of invalid / unknown model types."""

    def test_explain_invalid_model_type_returns_404(self, db_session):
        """GET /ml/explain with an invalid model type returns 404."""
        with patch("app.ml.router.ModelRegistry.load", return_value=None):
            resp = _client(db_session).get("/ml/explain/totally_invalid_model")
        assert resp.status_code == 404

    def test_registry_invalid_model_type_returns_empty(self, db_session):
        """GET /ml/registry/invalid_type returns empty list (not an error)."""
        with patch("app.ml.router.ModelRegistry.list_versions", return_value=[]):
            resp = _client(db_session).get("/ml/registry/invalid_type")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_accuracy_invalid_model_type_still_returns(self, db_session):
        """GET /ml/accuracy with unknown model type returns result (no 404)."""
        # _get_combined_accuracy accepts any string; returns empty versions/backtest
        with (
            patch("app.ml.router.ModelRegistry.compare_versions", return_value=[]),
            patch("app.ml.router.ModelRegistry.load", return_value=None),
        ):
            resp = _client(db_session).get("/ml/accuracy/nonexistent_model")
        assert resp.status_code == 200
        body = resp.json()
        assert body["model_type"] == "nonexistent_model"
        assert body["latest_backtest"] is None
        assert body["versions"] == []

    def test_rollback_invalid_version_returns_404(self, db_session):
        """POST rollback with a version that doesn't exist returns 404."""
        with patch("app.ml.router.ModelRegistry.rollback", return_value=None):
            resp = _client(db_session).post("/ml/registry/eta_prediction/rollback/9999")
        assert resp.status_code == 404
