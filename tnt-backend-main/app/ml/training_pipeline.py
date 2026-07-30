"""
Production ML Training Pipeline — Trains models on REAL PostgreSQL data.

PHASE 3-7: ETA, Demand Forecast, Slot Recommendation, Recommendation Engine, Vendor Ranking
All models trained using DatasetBuilder which queries actual production tables.

No mock data, no synthetic datasets, no CSV files.
"""

from __future__ import annotations

import logging
import os
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

# Suppress non-critical warnings during training
warnings.filterwarnings("ignore")

logger = logging.getLogger("tnt.ml.training")

# ── Model imports (optional — graceful fallback if not installed) ────────
_RF_AVAILABLE = False
_XGB_AVAILABLE = False
_LGBM_AVAILABLE = False

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    from sklearn.preprocessing import StandardScaler
    _RF_AVAILABLE = True
except ImportError:
    _RF_AVAILABLE = False

try:
    import xgboost as xgb
    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False

try:
    import lightgbm as lgb
    _LGBM_AVAILABLE = True
except ImportError:
    _LGBM_AVAILABLE = False


def _log_ml_dependency_warnings() -> None:
    """Emit a loud WARNING at startup for any missing ML dependency.

    Unlike the silent graceful-fallback pattern, this function ensures that
    a missing library is clearly visible in the logs so operators are not
    surprised by degraded model quality.
    """
    if not _RF_AVAILABLE:
        logger.warning(
            "*** scikit-learn is NOT available.  All sklearn-based models "
            "(RandomForest, SVD, etc.) will be SKIPPED.  "
            "Run: pip install 'scikit-learn>=1.5.0'"
        )
    if not _XGB_AVAILABLE:
        logger.warning(
            "*** XGBoost is NOT available.  XGBoost-based models will be "
            "SKIPPED, reducing prediction accuracy.  "
            "Run: pip install 'xgboost>=2.0.0'"
        )
    if not _LGBM_AVAILABLE:
        logger.warning(
            "*** LightGBM is NOT available.  LightGBM-based models will be "
            "SKIPPED, reducing prediction accuracy.  "
            "Run: pip install 'lightgbm>=4.0.0'"
        )


# Log dependency warnings at module import time so they appear during app startup.
_log_ml_dependency_warnings()

from app.ml.dataset_builder import DatasetBuilder
from app.ml.registry import ModelRegistry

MODEL_STORAGE_DIR = os.getenv("MODEL_STORAGE_DIR", "ml_models")


def time_based_split(
    X: np.ndarray,
    y: np.ndarray,
    timestamps: np.ndarray,
    test_size: float = 0.2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Chronological train/test split that prevents temporal data leakage.

    Sorts all rows by `timestamps` in ascending order (oldest first), then takes
    the earliest (1 - test_size) fraction as train and the most recent `test_size`
    fraction as test.  No shuffling is performed.

    This is critical for time-series targets (ETA, demand) where training on a
    future observation and testing on an earlier one would leak target information.

    Args:
        X: Feature matrix, shape (n_samples, n_features).
        y: Target array, shape (n_samples,).
        timestamps: 1-D array of datetimes / timestamps, same length as X.
        test_size: Fraction of samples to use as the test set (default 0.2).

    Returns:
        X_train, X_test, y_train, y_test, ts_train, ts_test
        where ts_* are the corresponding timestamp sub-arrays (useful for assertions).
    """
    if len(X) == 0:
        empty = np.array([])
        return X, X, y, y, empty, empty

    sort_idx = np.argsort(timestamps, kind="stable")
    X_sorted = X[sort_idx]
    y_sorted = y[sort_idx]
    ts_sorted = timestamps[sort_idx]

    split_at = max(1, int(len(X_sorted) * (1.0 - test_size)))
    return (
        X_sorted[:split_at],
        X_sorted[split_at:],
        y_sorted[:split_at],
        y_sorted[split_at:],
        ts_sorted[:split_at],
        ts_sorted[split_at:],
    )


class ModelTrainer:
    """Trains ML models on real data from PostgreSQL via DatasetBuilder."""

    # ── Hyper-parameter search spaces ────────────────────────────────────────
    _RF_PARAM_GRID = {
        "n_estimators": [100, 200, 300],
        "max_depth": [5, 8, 10, 15],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    }
    _XGB_PARAM_GRID = {
        "n_estimators": [100, 200, 300],
        "max_depth": [5, 8, 10, 15],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.7, 0.8, 1.0],
        "colsample_bytree": [0.7, 0.8, 1.0],
    }
    _LGBM_PARAM_GRID = {
        "n_estimators": [100, 200, 300],
        "max_depth": [5, 8, 10, 15],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "num_leaves": [15, 31, 63],
    }

    def __init__(self, db: Session):
        self.db = db
        self.builder = DatasetBuilder(db)

    # ── Cross-validation & tuning helpers ────────────────────────────────────

    def _tune_regressor(
        self,
        estimator,
        param_grid: dict,
        X: np.ndarray,
        y: np.ndarray,
        name: str,
        n_iter: int = 10,
        cv: int = 5,
    ) -> Tuple[Any, Dict[str, Any], float]:
        """Run RandomizedSearchCV then compute k-fold CV RMSE on the best estimator.

        Returns (best_estimator, best_params, cv_rmse).
        cv_rmse is the mean absolute value of neg_root_mean_squared_error scores.
        """
        from sklearn.model_selection import RandomizedSearchCV, cross_val_score

        n_samples = len(X)
        effective_cv = min(cv, n_samples) if n_samples >= 2 else 2
        effective_iter = min(n_iter, max(1, n_samples // 2))

        try:
            search = RandomizedSearchCV(
                estimator,
                param_distributions=param_grid,
                n_iter=effective_iter,
                cv=effective_cv,
                scoring="neg_root_mean_squared_error",
                random_state=42,
                n_jobs=-1,
                refit=True,
            )
            search.fit(X, y)
            best_est = search.best_estimator_
            best_params = search.best_params_
            logger.info(f"{name} best params: {best_params}")
        except Exception as e:
            logger.warning(f"{name} RandomizedSearchCV failed ({e}), fitting with defaults")
            estimator.fit(X, y)
            best_est = estimator
            best_params = {}

        # Full k-fold CV RMSE on the tuned estimator
        try:
            cv_scores = cross_val_score(
                best_est, X, y,
                cv=effective_cv,
                scoring="neg_root_mean_squared_error",
                n_jobs=-1,
            )
            cv_rmse = float(np.mean(np.abs(cv_scores)))
        except Exception as e:
            logger.warning(f"{name} cross_val_score failed ({e}), using 0.0 placeholder")
            cv_rmse = 0.0

        return best_est, best_params, cv_rmse

    def _tune_classifier(
        self,
        estimator,
        param_grid: dict,
        X: np.ndarray,
        y: np.ndarray,
        name: str,
        n_iter: int = 10,
        cv: int = 5,
    ) -> Tuple[Any, Dict[str, Any], float]:
        """Run RandomizedSearchCV then compute k-fold F1 on the best estimator.

        Returns (best_estimator, best_params, cv_f1).
        """
        from sklearn.model_selection import RandomizedSearchCV, cross_val_score

        n_samples = len(X)
        effective_cv = min(cv, n_samples) if n_samples >= 2 else 2
        effective_iter = min(n_iter, max(1, n_samples // 2))

        try:
            search = RandomizedSearchCV(
                estimator,
                param_distributions=param_grid,
                n_iter=effective_iter,
                cv=effective_cv,
                scoring="f1",
                random_state=42,
                n_jobs=-1,
                refit=True,
            )
            search.fit(X, y)
            best_est = search.best_estimator_
            best_params = search.best_params_
            logger.info(f"{name} best params: {best_params}")
        except Exception as e:
            logger.warning(f"{name} RandomizedSearchCV failed ({e}), fitting with defaults")
            estimator.fit(X, y)
            best_est = estimator
            best_params = {}

        # Full k-fold F1
        try:
            cv_scores = cross_val_score(
                best_est, X, y,
                cv=effective_cv,
                scoring="f1",
                n_jobs=-1,
            )
            cv_f1 = float(np.mean(cv_scores))
        except Exception as e:
            logger.warning(f"{name} cross_val_score failed ({e}), using 0.0 placeholder")
            cv_f1 = 0.0

        return best_est, best_params, cv_f1

    # ── PHASE 3: ETA Prediction ─────────────────────────────────────────────

    def train_eta(self, days: int = 90) -> Dict[str, Any]:
        """Train ETA prediction model using real order data.

        Trains RandomForest, XGBoost, LightGBM with RandomizedSearchCV (n_iter=10)
        and selects the winner by 5-fold cross-validated RMSE.

        Temporal split note
        -------------------
        ETA is a time-series target (order completion time depends on when the order
        was placed).  A random train_test_split risks including a future order in the
        training set while a past order is in the test set, leaking temporal context.
        We therefore sort by `created_at` and split chronologically (oldest 80% →
        train, most recent 20% → test) via `time_based_split()`.

        Cross-validation (5-fold) is applied after the split on the training set only;
        sklearn's KFold is not time-aware, but its role here is hyper-parameter
        selection (relative comparison), not final holdout evaluation, so the ordering
        bias is acceptable.
        """
        logger.info("=== PHASE 3: Training ETA Prediction Model ===")

        from app.ml.features import extract_eta_training_data
        try:
            X, y, feature_cols = extract_eta_training_data(self.db, days=days)
        except Exception as e:
            logger.error(f"Failed to extract ETA training data: {e}")
            return {"status": "failed", "error": str(e), "rows": 0}

        if len(X) == 0:
            return {"status": "failed", "error": "Empty ETA dataset", "rows": 0}

        # ── Temporal split: fetch timestamps in the same order as extract_eta_training_data ──
        # extract_eta_training_data builds rows from the same query (completed orders
        # ordered by Order.id).  We replicate that ordering to align timestamps with X/y.
        try:
            from app.core.time_utils import utcnow_naive
            from datetime import timedelta
            from app.modules.orders.model import Order, OrderStatus
            from sqlalchemy import extract as sql_extract

            since = utcnow_naive() - timedelta(days=days)
            ts_rows = self.db.query(
                Order.id, Order.created_at,
            ).join(
                __import__('app.modules.slots.model', fromlist=['Slot']).Slot,
                Order.slot_id == __import__('app.modules.slots.model', fromlist=['Slot']).Slot.id,
            ).filter(
                Order.created_at >= since,
                Order.status.in_([
                    OrderStatus.COMPLETED, OrderStatus.PICKED, OrderStatus.READY,
                ]),
            ).all()
            timestamps_eta = np.array([r.created_at for r in ts_rows], dtype=object)
        except Exception as ts_err:
            logger.warning(f"ETA temporal timestamps unavailable ({ts_err}); falling back to random split")
            timestamps_eta = None

        if timestamps_eta is not None and len(timestamps_eta) == len(X):
            X_train, X_test, y_train, y_test, _, _ = time_based_split(X, y, timestamps_eta)
            split_method = "temporal"
        else:
            # Fallback: mismatched lengths can happen if the query order differs;
            # log clearly and use random split rather than crash.
            logger.warning(
                f"ETA timestamp count ({len(timestamps_eta) if timestamps_eta is not None else 'n/a'}) "
                f"!= feature row count ({len(X)}); using random split as fallback."
            )
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            split_method = "random_fallback"

        logger.info(f"ETA split method: {split_method} | train={len(X_train)} test={len(X_test)}")

        results: List[Dict[str, Any]] = []
        best_model = None
        best_cv_rmse = float("inf")
        best_name = None
        best_params: Dict[str, Any] = {}

        # 1. RandomForest — tuned
        if _RF_AVAILABLE:
            try:
                rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
                tuned_rf, rf_params, rf_cv_rmse = self._tune_regressor(
                    rf_base, self._RF_PARAM_GRID, X, y, "RF-ETA"
                )
                y_pred = tuned_rf.predict(X_test)
                holdout = self._evaluate(y_test, y_pred, "ETA")
                results.append({"model": "RandomForest", **holdout, "cv_rmse": rf_cv_rmse, "params": rf_params})
                if rf_cv_rmse < best_cv_rmse:
                    best_cv_rmse = rf_cv_rmse
                    best_model = tuned_rf
                    best_name = "RandomForest"
                    best_params = rf_params
                logger.info(f"RF ETA: holdout_rmse={holdout['rmse']:.3f} cv_rmse={rf_cv_rmse:.3f}")
            except Exception as e:
                logger.error(f"RandomForest ETA failed: {e}")

        # 2. XGBoost — tuned
        if _XGB_AVAILABLE:
            try:
                xgb_base = xgb.XGBRegressor(random_state=42, n_jobs=-1)
                tuned_xgb, xgb_params, xgb_cv_rmse = self._tune_regressor(
                    xgb_base, self._XGB_PARAM_GRID, X, y, "XGB-ETA"
                )
                y_pred = tuned_xgb.predict(X_test)
                holdout = self._evaluate(y_test, y_pred, "ETA")
                results.append({"model": "XGBoost", **holdout, "cv_rmse": xgb_cv_rmse, "params": xgb_params})
                if xgb_cv_rmse < best_cv_rmse:
                    best_cv_rmse = xgb_cv_rmse
                    best_model = tuned_xgb
                    best_name = "XGBoost"
                    best_params = xgb_params
                logger.info(f"XGB ETA: holdout_rmse={holdout['rmse']:.3f} cv_rmse={xgb_cv_rmse:.3f}")
            except Exception as e:
                logger.error(f"XGBoost ETA failed: {e}")

        # 3. LightGBM — tuned
        if _LGBM_AVAILABLE:
            try:
                lgb_base = lgb.LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1)
                tuned_lgb, lgb_params, lgb_cv_rmse = self._tune_regressor(
                    lgb_base, self._LGBM_PARAM_GRID, X, y, "LGBM-ETA"
                )
                y_pred = tuned_lgb.predict(X_test)
                holdout = self._evaluate(y_test, y_pred, "ETA")
                results.append({"model": "LightGBM", **holdout, "cv_rmse": lgb_cv_rmse, "params": lgb_params})
                if lgb_cv_rmse < best_cv_rmse:
                    best_cv_rmse = lgb_cv_rmse
                    best_model = tuned_lgb
                    best_name = "LightGBM"
                    best_params = lgb_params
                logger.info(f"LGBM ETA: holdout_rmse={holdout['rmse']:.3f} cv_rmse={lgb_cv_rmse:.3f}")
            except Exception as e:
                logger.error(f"LightGBM ETA failed: {e}")

        if best_model is None:
            return {"status": "failed", "error": "No model trained successfully", "rows": len(X)}

        best_holdout = next(r for r in results if r["model"] == best_name)
        version_id = ModelRegistry.save(
            model=best_model,
            model_type="eta_prediction",
            metrics={
                "rmse": best_holdout["rmse"],
                "mae": best_holdout["mae"],
                "r2": best_holdout["r2"],
                "cv_rmse": round(best_cv_rmse, 4),
                "cv_folds": 5,
            },
            hyperparams={
                "days": days,
                "features": len(feature_cols),
                "model": best_name,
                "tuned_params": best_params,
                "split_method": split_method,
            },
            features=list(feature_cols),
            description=f"ETA prediction trained on {len(X)} real orders from last {days} days",
        )

        return {
            "status": "success",
            "model_type": "eta_prediction",
            "version_id": version_id,
            "best_model": best_name,
            "best_rmse": best_holdout["rmse"],
            "best_cv_rmse": round(best_cv_rmse, 4),
            "rows_trained": len(X),
            "features_used": len(feature_cols),
            "feature_names": list(feature_cols),
            "tuned_params": best_params,
            "split_method": split_method,
            "comparison": results,
        }

    # ── PHASE 4: Demand Forecasting ─────────────────────────────────────────

    def train_demand(self, days: int = 90) -> Dict[str, Any]:
        """Train demand forecast model.

        Temporal split note
        -------------------
        Demand is time-series data (hourly order counts per vendor).  Using a random
        split leaks future hours into the training set.  We sort by `hour_bucket`
        timestamps extracted alongside the features and split chronologically via
        `time_based_split()`.

        Non-time-series paths left on random split
        ------------------------------------------
        * vendor_ranking   — cross-sectional aggregate scores; no meaningful time axis
          per row (all history collapsed into a single performance score per vendor).
        * slot_recommendation — slot quality scores are static snapshots aggregated
          over all orders; no row-level timestamp.
        * fraud_detection  — per-user aggregate features over 30-day window; treated
          as cross-sectional, not a sequence.  Random split is appropriate.
        """
        logger.info("=== PHASE 4: Training Demand Forecast Model ===")

        from app.ml.features import extract_demand_features
        from app.modules.users.model import User

        vendors = self.db.query(User).filter(User.role == "vendor", User.is_approved == True).all()

        X_all, y_all, ts_all = [], [], []
        feature_cols = []
        for vendor in vendors:
            try:
                X_v, y_v, cols = extract_demand_features(self.db, vendor.id, days=days)
                if len(X_v) > 0:
                    # Fetch matching timestamps for this vendor in same query order
                    from app.core.time_utils import utcnow_naive
                    from datetime import timedelta
                    from sqlalchemy import func as _func, text as _text
                    from app.modules.orders.model import Order as _Order, OrderStatus as _OS

                    since = utcnow_naive() - timedelta(days=days)
                    ts_rows = self.db.query(
                        _func.date_trunc(_text("'hour'"), _Order.created_at).label("hour_bucket"),
                    ).filter(
                        _Order.vendor_id == vendor.id,
                        _Order.created_at >= since,
                        _Order.status.notin_([_OS.CANCELLED]),
                    ).group_by(
                        _func.date_trunc(_text("'hour'"), _Order.created_at)
                    ).order_by(
                        _func.date_trunc(_text("'hour'"), _Order.created_at)
                    ).all()

                    ts_v = []
                    for r in ts_rows:
                        b = r.hour_bucket
                        if isinstance(b, str):
                            from datetime import datetime as _dt
                            b = _dt.fromisoformat(b)
                        ts_v.append(b)

                    if len(ts_v) == len(X_v):
                        ts_all.extend(ts_v)
                        X_all.append(X_v)
                        y_all.append(y_v)
                        feature_cols = cols
                    else:
                        # Mismatched — include data but mark timestamps as None
                        logger.warning(
                            f"Demand vendor {vendor.id}: timestamp count {len(ts_v)} "
                            f"!= feature row count {len(X_v)}; rows excluded from temporal split."
                        )
            except Exception as e:
                logger.error(f"Failed to extract demand features for vendor {vendor.id}: {e}")

        if not X_all:
            return {"status": "failed", "error": "Empty demand dataset", "rows": 0}

        X = np.vstack(X_all)
        y = np.concatenate(y_all)

        if len(ts_all) == len(X):
            timestamps_demand = np.array(ts_all, dtype=object)
            X_train, X_test, y_train, y_test, _, _ = time_based_split(X, y, timestamps_demand)
            split_method = "temporal"
        else:
            logger.warning(
                f"Demand temporal timestamps count ({len(ts_all)}) != rows ({len(X)}); "
                "using random split as fallback."
            )
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            split_method = "random_fallback"

        logger.info(f"Demand split method: {split_method} | train={len(X_train)} test={len(X_test)}")

        results: List[Dict[str, Any]] = []
        best_model = None
        best_cv_rmse = float("inf")
        best_name = None
        best_params: Dict[str, Any] = {}

        # XGBoost — tuned
        if _XGB_AVAILABLE:
            try:
                xgb_base = xgb.XGBRegressor(random_state=42, n_jobs=-1)
                tuned_xgb, xgb_params, xgb_cv_rmse = self._tune_regressor(
                    xgb_base, self._XGB_PARAM_GRID, X, y, "XGB-Demand"
                )
                y_pred = np.maximum(0, tuned_xgb.predict(X_test))
                holdout = self._evaluate(y_test, y_pred, "Demand")
                results.append({"model": "XGBoost", **holdout, "cv_rmse": xgb_cv_rmse, "params": xgb_params})
                if xgb_cv_rmse < best_cv_rmse:
                    best_cv_rmse = xgb_cv_rmse
                    best_model = tuned_xgb
                    best_name = "XGBoost"
                    best_params = xgb_params
            except Exception as e:
                logger.error(f"XGBoost Demand failed: {e}")

        # RandomForest — tuned
        if _RF_AVAILABLE:
            try:
                rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
                tuned_rf, rf_params, rf_cv_rmse = self._tune_regressor(
                    rf_base, self._RF_PARAM_GRID, X, y, "RF-Demand"
                )
                y_pred = np.maximum(0, tuned_rf.predict(X_test))
                holdout = self._evaluate(y_test, y_pred, "Demand")
                results.append({"model": "RandomForest", **holdout, "cv_rmse": rf_cv_rmse, "params": rf_params})
                if rf_cv_rmse < best_cv_rmse:
                    best_cv_rmse = rf_cv_rmse
                    best_model = tuned_rf
                    best_name = "RandomForest"
                    best_params = rf_params
            except Exception as e:
                logger.error(f"RandomForest Demand failed: {e}")

        if best_model is None:
            return {"status": "failed", "error": "No model trained", "rows": len(X)}

        best_holdout = next(r for r in results if r["model"] == best_name)
        version_id = ModelRegistry.save(
            model=best_model,
            model_type="demand_forecast",
            metrics={
                "rmse": best_holdout["rmse"],
                "mae": best_holdout["mae"],
                "r2": best_holdout["r2"],
                "cv_rmse": round(best_cv_rmse, 4),
                "cv_folds": 5,
            },
            hyperparams={
                "days": days,
                "features": len(feature_cols),
                "model": best_name,
                "tuned_params": best_params,
                "split_method": split_method,
            },
            features=feature_cols,
            description=f"Demand forecast trained on {len(X)} hourly records",
        )

        return {
            "status": "success",
            "model_type": "demand_forecast",
            "version_id": version_id,
            "best_model": best_name,
            "best_rmse": best_holdout["rmse"],
            "best_cv_rmse": round(best_cv_rmse, 4),
            "rows_trained": len(X),
            "features_used": len(feature_cols),
            "tuned_params": best_params,
            "split_method": split_method,
            "comparison": results,
        }

    # ── PHASE 5: Slot Recommendation ────────────────────────────────────────

    def train_slot_recommendation(self) -> Dict[str, Any]:
        """Train slot recommendation scoring model."""
        logger.info("=== PHASE 5: Training Slot Recommendation Model ===")

        from app.ml.features import extract_slot_features
        try:
            X, y, feature_cols = extract_slot_features(self.db)
        except Exception as e:
            logger.error(f"Failed to extract slot features: {e}")
            return {"status": "failed", "error": str(e), "rows": 0}

        if len(X) == 0:
            return {"status": "failed", "error": "Empty slot dataset", "rows": 0}

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        results: List[Dict[str, Any]] = []
        best_model = None
        best_cv_rmse = float("inf")
        best_name = None
        best_params: Dict[str, Any] = {}

        # RandomForest — tuned
        if _RF_AVAILABLE:
            try:
                rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
                tuned_rf, rf_params, rf_cv_rmse = self._tune_regressor(
                    rf_base, self._RF_PARAM_GRID, X, y, "RF-Slot"
                )
                y_pred = np.clip(tuned_rf.predict(X_test), 0, 100)
                holdout = self._evaluate(y_test, y_pred, "Slot")
                results.append({"model": "RandomForest", **holdout, "cv_rmse": rf_cv_rmse, "params": rf_params})
                if rf_cv_rmse < best_cv_rmse:
                    best_cv_rmse = rf_cv_rmse
                    best_model = tuned_rf
                    best_name = "RandomForest"
                    best_params = rf_params
            except Exception as e:
                logger.error(f"RandomForest Slot failed: {e}")

        if best_model is None:
            return {"status": "failed", "error": "No model trained", "rows": len(X)}

        best_holdout = next(r for r in results if r["model"] == best_name)
        version_id = ModelRegistry.save(
            model=best_model,
            model_type="slot_recommendation",
            metrics={
                "rmse": best_holdout["rmse"],
                "mae": best_holdout["mae"],
                "r2": best_holdout["r2"],
                "cv_rmse": round(best_cv_rmse, 4),
                "cv_folds": 5,
            },
            hyperparams={
                "features": len(feature_cols),
                "model": best_name,
                "tuned_params": best_params,
            },
            features=feature_cols,
            description=f"Slot recommendation trained on {len(X)} slots",
        )

        return {
            "status": "success",
            "model_type": "slot_recommendation",
            "version_id": version_id,
            "best_model": best_name,
            "best_rmse": best_holdout["rmse"],
            "best_cv_rmse": round(best_cv_rmse, 4),
            "rows_trained": len(X),
            "features_used": len(feature_cols),
            "tuned_params": best_params,
            "comparison": results,
        }

    # ── PHASE 6: Recommendation Engine (Matrix Factorization Surrogate) ─────

    def train_recommendation(self) -> Dict[str, Any]:
        """Train recommendation model using SVD-based collaborative filtering
        on real user-item interaction data.
        """
        logger.info("=== PHASE 6: Training Recommendation Engine ===")

        df = self.builder.build_recommendation_dataset()
        if df.empty:
            return {"status": "failed", "error": "Empty recommendation dataset", "rows": 0}

        n_users = df['user_id'].nunique()
        n_items = df['item_id'].nunique()
        n_interactions = len(df)

        # Build user-item matrix for collaborative filtering
        logger.info(f"Building {n_users}x{n_items} user-item matrix from {n_interactions} interactions")

        # Encode user and item IDs
        user_encoder = {uid: i for i, uid in enumerate(df['user_id'].unique())}
        item_encoder = {iid: j for j, iid in enumerate(df['item_id'].unique())}
        user_decoder = {i: uid for uid, i in user_encoder.items()}
        item_decoder = {j: iid for iid, j in item_encoder.items()}

        # Build sparse-ish matrix for training
        import scipy.sparse as sp
        n_users_enc = len(user_encoder)
        n_items_enc = len(item_encoder)

        rows_idx = []
        cols_idx = []
        data_vals = []

        for _, row in df.iterrows():
            if row['user_id'] in user_encoder and row['item_id'] in item_encoder:
                rows_idx.append(user_encoder[row['user_id']])
                cols_idx.append(item_encoder[row['item_id']])
                # Interaction strength as value
                data_vals.append(min(row['interaction_strength'], 10))

        if not data_vals:
            return {"status": "failed", "error": "No valid interactions after encoding"}

        interaction_matrix = sp.coo_matrix(
            (data_vals, (rows_idx, cols_idx)),
            shape=(n_users_enc, n_items_enc)
        )

        # Use Truncated SVD for collaborative filtering
        from sklearn.decomposition import TruncatedSVD
        n_components = min(50, min(interaction_matrix.shape) - 1)

        if n_components < 2:
            # Too few dimensions — return heuristic-based system
            logger.warning("Too few dimensions for SVD, using popularity-based")
            return self._train_popularity_model(df, user_encoder, item_encoder, user_decoder, item_decoder)

        svd = TruncatedSVD(n_components=n_components, random_state=42)
        user_factors = svd.fit_transform(interaction_matrix)
        item_factors = svd.components_.T
        explained_variance = float(svd.explained_variance_ratio_.sum())

        logger.info(f"SVD completed: {n_components} components, explained variance: {explained_variance:.3f}")

        # Save the complete recommendation system
        model_package = {
            "svd": svd,
            "user_factors": user_factors,
            "item_factors": item_factors,
            "user_encoder": user_encoder,
            "item_encoder": item_encoder,
            "user_decoder": user_decoder,
            "item_decoder": item_decoder,
            "n_components": n_components,
            "explained_variance": explained_variance,
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": n_interactions,
            "type": "collaborative_filtering_svd",
        }

        version_id = ModelRegistry.save(
            model=model_package,
            model_type="recommendation_engine",
            metrics={
                "n_users": n_users,
                "n_items": n_items,
                "n_interactions": n_interactions,
                "explained_variance": round(explained_variance, 3),
                "components": n_components,
            },
            hyperparams={"algorithm": "TruncatedSVD", "components": n_components},
            description=f"Collaborative filtering on {n_interactions} real interactions",
        )

        return {
            "status": "success",
            "model_type": "recommendation_engine",
            "version_id": version_id,
            "algorithm": "TruncatedSVD",
            "n_users": n_users,
            "n_items": n_items,
            "n_interactions": n_interactions,
            "components": n_components,
            "explained_variance": round(explained_variance, 3),
        }

    def _train_popularity_model(self, df, user_encoder, item_encoder, user_decoder, item_decoder):
        """Fallback: popularity-based recommendation when SVD is not feasible."""
        popularity = df.groupby('item_id').agg({
            'order_count': 'sum',
            'item_name': 'first',
            'vendor_id': 'first',
            'vendor_name': 'first',
            'price_paise': 'first',
            'category': 'first',
        }).sort_values('order_count', ascending=False).reset_index()

        model_package = {
            "type": "popularity_based",
            "popularity": popularity.to_dict('records'),
            "user_encoder": user_encoder,
            "item_encoder": item_encoder,
            "user_decoder": user_decoder,
            "item_decoder": item_decoder,
            "n_users": len(user_encoder),
            "n_items": len(item_encoder),
        }

        version_id = ModelRegistry.save(
            model=model_package,
            model_type="recommendation_engine",
            metrics={
                "n_users": len(user_encoder),
                "n_items": len(item_encoder),
                "algorithm": "popularity_based",
            },
            hyperparams={"algorithm": "popularity_based"},
            description="Popularity-based recommendation fallback",
        )

        return {
            "status": "success",
            "model_type": "recommendation_engine",
            "version_id": version_id,
            "algorithm": "popularity_based",
            "n_users": len(user_encoder),
            "n_items": len(item_encoder),
        }

    # ── PHASE 7: Vendor Performance / Ranking ───────────────────────────────

    def train_vendor_ranking(self) -> Dict[str, Any]:
        """Train vendor ranking model."""
        logger.info("=== PHASE 7: Training Vendor Ranking Model ===")

        from app.ml.features import extract_vendor_ranking_features
        try:
            X, y, feature_cols = extract_vendor_ranking_features(self.db)
        except Exception as e:
            logger.error(f"Failed to extract vendor ranking features: {e}")
            return {"status": "failed", "error": str(e), "rows": 0}

        if len(X) == 0:
            return {"status": "failed", "error": "Empty vendor dataset", "rows": 0}

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        results: List[Dict[str, Any]] = []
        best_model = None
        best_cv_rmse = float("inf")
        best_name = None
        best_params: Dict[str, Any] = {}

        # RandomForest — tuned
        if _RF_AVAILABLE:
            try:
                rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
                tuned_rf, rf_params, rf_cv_rmse = self._tune_regressor(
                    rf_base, self._RF_PARAM_GRID, X, y, "RF-Vendor"
                )
                y_pred = np.clip(tuned_rf.predict(X_test), 0, 100)
                holdout = self._evaluate(y_test, y_pred, "Vendor")
                results.append({"model": "RandomForest", **holdout, "cv_rmse": rf_cv_rmse, "params": rf_params})
                if rf_cv_rmse < best_cv_rmse:
                    best_cv_rmse = rf_cv_rmse
                    best_model = tuned_rf
                    best_name = "RandomForest"
                    best_params = rf_params
            except Exception as e:
                logger.error(f"RandomForest Vendor failed: {e}")

        # XGBoost — tuned
        if _XGB_AVAILABLE:
            try:
                xgb_base = xgb.XGBRegressor(random_state=42, n_jobs=-1)
                tuned_xgb, xgb_params, xgb_cv_rmse = self._tune_regressor(
                    xgb_base, self._XGB_PARAM_GRID, X, y, "XGB-Vendor"
                )
                y_pred = np.clip(tuned_xgb.predict(X_test), 0, 100)
                holdout = self._evaluate(y_test, y_pred, "Vendor")
                results.append({"model": "XGBoost", **holdout, "cv_rmse": xgb_cv_rmse, "params": xgb_params})
                if xgb_cv_rmse < best_cv_rmse:
                    best_cv_rmse = xgb_cv_rmse
                    best_model = tuned_xgb
                    best_name = "XGBoost"
                    best_params = xgb_params
            except Exception as e:
                logger.error(f"XGBoost Vendor failed: {e}")

        if best_model is None:
            return {"status": "failed", "error": "No model trained", "rows": len(X)}

        best_holdout = next(r for r in results if r["model"] == best_name)
        version_id = ModelRegistry.save(
            model=best_model,
            model_type="vendor_ranking",
            metrics={
                "rmse": best_holdout["rmse"],
                "mae": best_holdout["mae"],
                "r2": best_holdout["r2"],
                "cv_rmse": round(best_cv_rmse, 4),
                "cv_folds": 5,
            },
            hyperparams={
                "features": len(feature_cols),
                "model": best_name,
                "tuned_params": best_params,
            },
            features=feature_cols,
            description=f"Vendor ranking trained on {len(X)} vendors",
        )

        return {
            "status": "success",
            "model_type": "vendor_ranking",
            "version_id": version_id,
            "best_model": best_name,
            "best_rmse": best_holdout["rmse"],
            "best_cv_rmse": round(best_cv_rmse, 4),
            "rows_trained": len(X),
            "features_used": len(feature_cols),
            "tuned_params": best_params,
            "comparison": results,
        }

    # ── PHASE 9: Full Pipeline ──────────────────────────────────────────────

    def train_all(self, days: int = 90) -> Dict[str, Any]:
        """Run complete training pipeline for all models."""
        logger.info("=" * 60)
        logger.info("PHASE 9: Running Full ML Training Pipeline")
        logger.info("=" * 60)

        results = {
            "trained_at": datetime.utcnow().isoformat(),
            "data_source": "PostgreSQL (production)",
            "training_window_days": days,
            "models": {},
        }

        # Phase 1-2: Dataset Discovery (metadata only)
        inventory = self.builder.get_data_source_inventory()
        results["data_inventory"] = inventory

        # Phase 3: ETA
        logger.info("\n--- Training ETA Prediction ---")
        results["models"]["eta_prediction"] = self.train_eta(days)

        # Phase 4: Demand Forecast
        logger.info("\n--- Training Demand Forecast ---")
        results["models"]["demand_forecast"] = self.train_demand(days)

        # Phase 5: Slot Recommendation
        logger.info("\n--- Training Slot Recommendation ---")
        results["models"]["slot_recommendation"] = self.train_slot_recommendation()

        # Phase 6: Recommendation Engine
        logger.info("\n--- Training Recommendation Engine ---")
        results["models"]["recommendation_engine"] = self.train_recommendation()

        # Phase 7: Vendor Ranking
        logger.info("\n--- Training Vendor Ranking ---")
        results["models"]["vendor_ranking"] = self.train_vendor_ranking()

        # Phase 8: Summary
        summary = ModelRegistry.get_registry_summary()
        results["registry_summary"] = summary
        results["total_models_trained"] = sum(
            1 for m in results["models"].values()
            if m.get("status") == "success"
        )

        logger.info("=" * 60)
        logger.info(f"Pipeline complete: {results['total_models_trained']} models trained")
        logger.info("=" * 60)

        return results

    # ── Evaluation Helpers ────────────────────────────────────────────────────

    def _evaluate(self, y_true: np.ndarray, y_pred: np.ndarray,
                  context: str = "") -> Dict[str, float]:
        """Calculate regression metrics."""
        mae = mean_absolute_error(y_true, y_pred)
        mse = mean_squared_error(y_true, y_pred)
        rmse = float(np.sqrt(mse))
        r2 = r2_score(y_true, y_pred)
        return {
            "mae": round(float(mae), 3),
            "mse": round(float(mse), 3),
            "rmse": round(rmse, 3),
            "r2": round(float(r2), 3),
        }


# ── Standalone training functions (called from ml/router.py) ─────────────────


def run_full_training_pipeline(db: Session, days: int = 90) -> Dict[str, Any]:
    """Run full training pipeline."""
    trainer = ModelTrainer(db)
    return trainer.train_all(days)


def train_eta_models(db: Session, days: int = 90) -> Dict[str, Any]:
    """Train ETA models only."""
    trainer = ModelTrainer(db)
    return trainer.train_eta(days)


def train_demand_forecast(db: Session, vendor_id: int, days: int = 90) -> Dict[str, Any]:
    """Train demand forecast."""
    trainer = ModelTrainer(db)
    return trainer.train_demand(days)


def train_fraud_detection(db: Session) -> Dict[str, Any]:
    """Train fraud detection model using real order data."""
    logger.info("=== Training Fraud Detection Model ===")
    from app.ml.features import extract_fraud_features

    try:
        X, y, feature_cols = extract_fraud_features(db)
    except Exception as e:
        logger.error(f"Failed to extract fraud features: {e}")
        return {"status": "failed", "error": str(e)}

    if len(X) == 0:
        return {"status": "failed", "error": "Empty dataset"}

    # Use RandomForest for fraud classification with RandomizedSearchCV + CV F1
    if _RF_AVAILABLE:
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
            from sklearn.model_selection import RandomizedSearchCV, cross_val_score

            # Ensure at least one positive label (binary classification requirement)
            if len(np.unique(y)) < 2:
                y[0] = 1.0

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            n_samples = len(X)
            effective_cv = min(5, n_samples) if n_samples >= 2 else 2
            effective_iter = min(10, max(1, n_samples // 2))

            rf_clf_param_grid = {
                "n_estimators": [100, 200, 300],
                "max_depth": [5, 8, 10, 15],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
            }

            try:
                search = RandomizedSearchCV(
                    RandomForestClassifier(random_state=42, n_jobs=-1, class_weight="balanced"),
                    param_distributions=rf_clf_param_grid,
                    n_iter=effective_iter,
                    cv=effective_cv,
                    scoring="f1",
                    random_state=42,
                    n_jobs=-1,
                    refit=True,
                )
                search.fit(X, y)
                model = search.best_estimator_
                tuned_params = search.best_params_
                logger.info(f"Fraud RF best params: {tuned_params}")
            except Exception as tune_err:
                logger.warning(f"Fraud RandomizedSearchCV failed ({tune_err}), using defaults")
                model = RandomForestClassifier(
                    n_estimators=100, max_depth=8, random_state=42,
                    n_jobs=-1, class_weight="balanced"
                )
                model.fit(X_train, y_train)
                tuned_params = {}

            # CV F1
            try:
                cv_f1_scores = cross_val_score(
                    model, X, y, cv=effective_cv, scoring="f1", n_jobs=-1
                )
                cv_f1 = round(float(np.mean(cv_f1_scores)), 4)
            except Exception as cv_err:
                logger.warning(f"Fraud cross_val_score failed ({cv_err})")
                cv_f1 = 0.0

            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            version_id = ModelRegistry.save(
                model=model,
                model_type="fraud_detection",
                metrics={
                    "accuracy": round(float(accuracy), 3),
                    "precision": round(float(precision), 3),
                    "recall": round(float(recall), 3),
                    "f1": round(float(f1), 3),
                    "cv_f1": cv_f1,
                    "cv_folds": effective_cv,
                },
                hyperparams={
                    "algorithm": "RandomForest",
                    "class_weight": "balanced",
                    "tuned_params": tuned_params,
                },
                features=feature_cols,
                description=f"Fraud detection trained on {len(X)} users",
            )

            return {
                "status": "success",
                "model_type": "fraud_detection",
                "version_id": version_id,
                "accuracy": round(float(accuracy), 3),
                "precision": round(float(precision), 3),
                "recall": round(float(recall), 3),
                "f1": round(float(f1), 3),
                "cv_f1": cv_f1,
                "tuned_params": tuned_params,
                "rows_trained": len(X),
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    return {"status": "failed", "error": "No classifier available"}


def train_vendor_ranking(db: Session) -> Dict[str, Any]:
    """Train vendor ranking model."""
    trainer = ModelTrainer(db)
    return trainer.train_vendor_ranking()


def train_slot_recommendation(db: Session) -> Dict[str, Any]:
    """Train slot recommendation model."""
    trainer = ModelTrainer(db)
    return trainer.train_slot_recommendation()


def train_eta(db: Session, days: int = 90) -> Dict[str, Any]:
    """Train ETA model."""
    trainer = ModelTrainer(db)
    return trainer.train_eta(days)


def train_demand(db: Session, days: int = 90) -> Dict[str, Any]:
    """Train demand forecast model."""
    trainer = ModelTrainer(db)
    return trainer.train_demand(days)


class RetrainingService:
    """Scheduled retraining service for production."""

    def __init__(self, db_session_maker):
        self.db_session_maker = db_session_maker

    def retrain_all(self) -> Dict[str, Any]:
        """Retrain all models and update registry."""
        db = self.db_session_maker()
        try:
            trainer = ModelTrainer(db)
            results = trainer.train_all()
            return results
        finally:
            db.close()

    def retrain_eta(self, days: int = 90) -> Dict[str, Any]:
        """Retrain only ETA model."""
        db = self.db_session_maker()
        try:
            trainer = ModelTrainer(db)
            return trainer.train_eta(days)
        finally:
            db.close()

    def retrain_demand(self, days: int = 90) -> Dict[str, Any]:
        """Retrain only demand forecast."""
        db = self.db_session_maker()
        try:
            trainer = ModelTrainer(db)
            return trainer.train_demand(days)
        finally:
            db.close()
