"""Unit tests for ModelRegistry (app/ml/registry.py).

Verifies model saving, loading, versioning, active model promotion,
rollback, metrics updates, deletion, registry summary, and filesystem artifact management.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ml.ml_models_model import MlModel
from app.ml.registry import ModelRegistry, _compute_hash, _dumps


@pytest.fixture(autouse=True)
def isolate_model_registry(tmp_path: Path, db_session: Session):
    """Isolate MODEL_STORAGE_DIR to pytest tmp_path and SessionLocal to db_session."""
    with (
        patch("app.ml.registry.MODEL_STORAGE_DIR", tmp_path),
        patch("app.ml.registry.SessionLocal", return_value=db_session),
        patch.object(db_session, "close", return_value=None),
    ):
        yield


# ── 1. Helpers & Utility Functions ───────────────────────────────────────────

class TestDumpsAndHash:
    def test_dumps_none(self):
        assert _dumps(None) is None

    def test_dumps_valid(self):
        assert _dumps({"a": 1}) == '{"a": 1}'

    def test_dumps_exception_fallback(self):
        class CustomObj:
            def __str__(self):
                return "custom_str_output"

        with patch("json.dumps", side_effect=TypeError("JSON serialisation failed")):
            assert _dumps(CustomObj()) == "custom_str_output"

    def test_compute_hash(self, tmp_path: Path):
        file_path = tmp_path / "dummy.pkl"
        file_path.write_bytes(b"test model bytes 12345")
        file_hash = _compute_hash(file_path)
        assert isinstance(file_hash, str)
        assert len(file_hash) == 16


# ── 2. Save & Load Tests ─────────────────────────────────────────────────────

class TestModelRegistrySaveAndLoad:
    def test_save_and_save_model_alias(self, db_session: Session, tmp_path: Path):
        dummy_model = {"coef": [1.0, 2.0]}

        v1 = ModelRegistry.save(
            model=dummy_model,
            model_type="eta_prediction",
            metrics={"rmse": 3.5, "accuracy": 0.92},
            hyperparams={"n_estimators": 100},
            features=["f1", "f2"],
            description="First version",
        )
        assert v1 == "eta_prediction_v1"
        assert (tmp_path / "eta_prediction" / "eta_prediction_v1.pkl").exists()

        v2 = ModelRegistry.save_model(
            model=dummy_model,
            model_type="eta_prediction",
            metrics={"r2": 0.88},
            hyperparams={"n_estimators": 200},
            features=["f1", "f2"],
        )
        assert v2 == "eta_prediction_v2"
        assert (tmp_path / "eta_prediction" / "eta_prediction_v2.pkl").exists()

    def test_save_metrics_parsing(self, db_session: Session):
        dummy_model = "model_obj"

        # 1. accuracy key present
        v1 = ModelRegistry.save(dummy_model, "test_m1", metrics={"accuracy": 0.95})
        row1 = db_session.query(MlModel).filter_by(model_version=v1).first()
        assert row1.accuracy == 0.95

        # 2. r2 key present
        v2 = ModelRegistry.save(dummy_model, "test_m1", metrics={"r2": 0.89})
        row2 = db_session.query(MlModel).filter_by(model_version=v2).first()
        assert row2.accuracy == 0.89

        # 3. non-accuracy metric
        v3 = ModelRegistry.save(dummy_model, "test_m1", metrics={"mae": 1.5})
        row3 = db_session.query(MlModel).filter_by(model_version=v3).first()
        assert row3.accuracy is None

    def test_save_sqlalchemy_error(self, db_session: Session):
        dummy_model = "model_obj"
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("DB commit crash")):
            with pytest.raises(SQLAlchemyError):
                ModelRegistry.save(dummy_model, "failing_save_model")

    def test_load_latest_active(self, db_session: Session):
        dummy_model = {"model_name": "eta_clf"}
        ModelRegistry.save(dummy_model, "eta_prediction", metrics={"rmse": 2.0})

        loaded = ModelRegistry.load("eta_prediction")
        assert loaded is not None
        model_obj, meta = loaded
        assert model_obj == dummy_model
        assert meta["model_type"] == "eta_prediction"
        assert meta["version_id"] == "eta_prediction_v1"
        assert meta["status"] == "active"
        assert meta["metrics"] == {"rmse": 2.0}

    def test_load_specific_version(self, db_session: Session):
        m1 = {"v": 1}
        m2 = {"v": 2}
        v1 = ModelRegistry.save(m1, "demand_forecast")
        v2 = ModelRegistry.save(m2, "demand_forecast")

        loaded_v1 = ModelRegistry.load("demand_forecast", version_id=v1)
        assert loaded_v1 is not None
        assert loaded_v1[0] == m1

        loaded_v2 = ModelRegistry.load("demand_forecast", version_id=v2)
        assert loaded_v2 is not None
        assert loaded_v2[0] == m2

    def test_load_missing_row(self, db_session: Session):
        assert ModelRegistry.load("nonexistent_model_type") is None

    def test_load_missing_file_artifact(self, db_session: Session, tmp_path: Path):
        v = ModelRegistry.save({"a": 1}, "missing_file_model")
        # Delete file from disk
        pkl_file = tmp_path / "missing_file_model" / f"{v}.pkl"
        if pkl_file.exists():
            pkl_file.unlink()

        assert ModelRegistry.load("missing_file_model") is None


# ── 3. Active Version & Listing Tests ────────────────────────────────────────

class TestModelRegistryActiveAndVersions:
    def test_get_active_version_success(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "slot_recommendation")
        active = ModelRegistry.get_active_version("slot_recommendation")
        assert active is not None
        assert active["version_id"] == v1
        assert active["status"] == "active"

    def test_get_active_version_none(self, db_session: Session):
        assert ModelRegistry.get_active_version("unknown_model") is None

    def test_get_version(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "vendor_ranking")
        meta = ModelRegistry.get_version("vendor_ranking", v1)
        assert meta is not None
        assert meta["version_id"] == v1

        assert ModelRegistry.get_version("vendor_ranking", "invalid_v99") is None

    def test_set_active_version_success(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "fraud_detection")
        v2 = ModelRegistry.save({"v": 2}, "fraud_detection")

        # Initially v2 is active
        assert ModelRegistry.get_active_version("fraud_detection")["version_id"] == v2

        # Promote v1
        success = ModelRegistry.set_active_version("fraud_detection", v1)
        assert success is True

        active = ModelRegistry.get_active_version("fraud_detection")
        assert active["version_id"] == v1

        # Check v2 is inactive
        v2_meta = ModelRegistry.get_version("fraud_detection", v2)
        assert v2_meta["status"] == "inactive"

    def test_set_active_version_missing(self, db_session: Session):
        assert ModelRegistry.set_active_version("fraud_detection", "nonexistent_v99") is False

    def test_set_active_version_db_error(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "err_model")
        with patch.object(db_session, "commit", side_effect=SQLAlchemyError("Set active error")):
            assert ModelRegistry.set_active_version("err_model", v1) is False

    def test_list_versions(self, db_session: Session):
        assert ModelRegistry.list_versions("empty_model") == []

        v1 = ModelRegistry.save({"v": 1}, "list_test_model", metrics={"rmse": 5.0})
        v2 = ModelRegistry.save({"v": 2}, "list_test_model", metrics={"rmse": 2.0})

        versions = ModelRegistry.list_versions("list_test_model")
        assert len(versions) == 2
        assert versions[0]["version_id"] == v2
        assert versions[1]["version_id"] == v1

    def test_compare_versions(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "compare_model", metrics={"rmse": 10.0})
        v2 = ModelRegistry.save({"v": 2}, "compare_model", metrics={"rmse": 2.5})
        v3 = ModelRegistry.save({"v": 3}, "compare_model", metrics={"rmse": 5.0})

        sorted_vers = ModelRegistry.compare_versions("compare_model")
        assert len(sorted_vers) == 3
        # Sorted by RMSE ascending (2.5 -> 5.0 -> 10.0)
        assert sorted_vers[0]["version_id"] == v2
        assert sorted_vers[1]["version_id"] == v3
        assert sorted_vers[2]["version_id"] == v1


# ── 4. Rollback & Update Metrics Tests ────────────────────────────────────────

class TestModelRegistryRollbackAndUpdateMetrics:
    def test_rollback_valid(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "rb_model")
        v2 = ModelRegistry.save({"v": 2}, "rb_model")

        # Active is v2; rollback to version_num=1 (v1)
        rolled_v = ModelRegistry.rollback("rb_model", version_num=1)
        assert rolled_v == v1
        assert ModelRegistry.get_active_version("rb_model")["version_id"] == v1

    def test_rollback_invalid_version_num(self, db_session: Session):
        ModelRegistry.save({"v": 1}, "rb_model2")

        assert ModelRegistry.rollback("rb_model2", version_num=0) is None
        assert ModelRegistry.rollback("rb_model2", version_num=99) is None

    def test_update_metrics(self, db_session: Session):
        v1 = ModelRegistry.save({"v": 1}, "metrics_model")

        # 1. Update with r2 metric
        ModelRegistry.update_metrics("metrics_model", v1, {"r2": 0.93, "rmse": 1.2})
        meta1 = ModelRegistry.get_version("metrics_model", v1)
        assert meta1["accuracy"] == 0.93
        assert meta1["metrics"] == {"r2": 0.93, "rmse": 1.2}

        # 2. Update with accuracy metric
        ModelRegistry.update_metrics("metrics_model", v1, {"accuracy": 0.97})
        meta2 = ModelRegistry.get_version("metrics_model", v1)
        assert meta2["accuracy"] == 0.97

        # 3. Update with other metric
        ModelRegistry.update_metrics("metrics_model", v1, {"mae": 0.8})
        meta3 = ModelRegistry.get_version("metrics_model", v1)
        assert meta3["metrics"] == {"mae": 0.8}

        # 4. Nonexistent version_id does nothing silently
        ModelRegistry.update_metrics("metrics_model", "invalid_v99", {"r2": 0.5})

    def test_get_latest_version(self, db_session: Session):
        assert ModelRegistry.get_latest_version("nonexistent") is None

        v1 = ModelRegistry.save({"v": 1}, "latest_model")
        assert ModelRegistry.get_latest_version("latest_model") == v1


# ── 5. Delete & Summary Tests ────────────────────────────────────────────────

class TestModelRegistryDeleteAndSummary:
    def test_delete_model_success(self, db_session: Session, tmp_path: Path):
        v1 = ModelRegistry.save({"v": 1}, "del_model")
        pkl_file = tmp_path / "del_model" / f"{v1}.pkl"
        assert pkl_file.exists()

        success = ModelRegistry.delete_model("del_model", v1)
        assert success is True
        assert not pkl_file.exists()
        assert ModelRegistry.get_version("del_model", v1) is None

    def test_delete_model_missing_file(self, db_session: Session, tmp_path: Path):
        v1 = ModelRegistry.save({"v": 1}, "del_model_no_file")
        pkl_file = tmp_path / "del_model_no_file" / f"{v1}.pkl"
        if pkl_file.exists():
            pkl_file.unlink()

        success = ModelRegistry.delete_model("del_model_no_file", v1)
        assert success is True
        assert ModelRegistry.get_version("del_model_no_file", v1) is None

    def test_delete_model_missing_row(self, db_session: Session):
        assert ModelRegistry.delete_model("del_model", "nonexistent_v99") is False

    def test_get_all_model_types(self, db_session: Session):
        ModelRegistry.save({"v": 1}, "model_type_a")
        ModelRegistry.save({"v": 1}, "model_type_b")

        types = ModelRegistry.get_all_model_types()
        assert "model_type_a" in types
        assert "model_type_b" in types

    def test_get_registry_summary(self, db_session: Session):
        ModelRegistry.save({"v": 1}, "sum_model_1", metrics={"rmse": 2.0, "accuracy": 0.90})
        ModelRegistry.save({"v": 2}, "sum_model_1", metrics={"rmse": 1.5, "accuracy": 0.95})
        ModelRegistry.save({"v": 1}, "sum_model_2", metrics={"mae": 0.5})

        summary = ModelRegistry.get_registry_summary()
        assert "sum_model_1" in summary
        assert summary["sum_model_1"]["total_versions"] == 2
        assert summary["sum_model_1"]["latest"] == "sum_model_1_v2"
        assert summary["sum_model_1"]["best_rmse"] == 1.5
        assert summary["sum_model_1"]["best_accuracy"] == 0.95

        assert "sum_model_2" in summary
        assert summary["sum_model_2"]["best_rmse"] is None

    def test_get_session_explicit_vs_default(self, db_session: Session):
        """Test _get_session with explicit session vs None default."""
        sess, should_close = ModelRegistry._get_session(db_session)
        assert sess == db_session
        assert should_close is False

        sess_def, should_close_def = ModelRegistry._get_session(None)
        assert sess_def == db_session
        assert should_close_def is True

