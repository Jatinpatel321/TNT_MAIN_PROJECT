"""ML Model Registry (DB-backed).

Replaces the previous file-based JSON registry with a Postgres-backed
metadata table `ml_models`.

- Models are still stored as pickle artifacts on disk.
- Metadata (model_type, version, trained_at, accuracy, file_path, status,
  metrics/hyperparams/features/description) lives in Postgres.

This registry is intentionally compatible with the existing training +
inference code: the public API matches the prior `ModelRegistry` class.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import and_, func, select, text as sql_text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ml.ml_models_model import MlModel
from app.database.session import SessionLocal

logger = logging.getLogger("tnt.ml.registry")

MODEL_STORAGE_DIR = Path(os.getenv("MODEL_STORAGE_DIR", "ml_models"))
MODEL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _dumps(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


def _compute_hash(path: Path) -> str:
    # Keep it cheap: hash only model bytes.
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


class ModelRegistry:
    """Postgres-backed registry + on-disk pickle artifacts."""

    @staticmethod
    def _get_session(explicit_session: Optional[Session] = None) -> tuple[Session, bool]:
        if explicit_session is not None:
            return explicit_session, False
        return SessionLocal(), True

    @staticmethod
    def save(
        model: Any,
        model_type: str,
        metrics: Optional[dict[str, float]] = None,
        hyperparams: Optional[dict[str, Any]] = None,
        features: Optional[list[str]] = None,
        description: str = "",
    ) -> str:
        """Save a model and create a metadata row in `ml_models`.

        Returns the generated model_version string (e.g. eta_prediction_v3).
        """

        session, should_close = ModelRegistry._get_session()
        try:
            # `model_version` column stores a version label string; we instead
            # infer version number by counting rows for this model_type.
            # This keeps DB schema simple and robust.
            version_num = (
                session.execute(
                    select(func.count())
                    .select_from(MlModel)
                    .where(MlModel.model_name == model_type)
                ).scalar()
                or 0
            ) + 1

            model_dir = MODEL_STORAGE_DIR / model_type
            model_dir.mkdir(parents=True, exist_ok=True)

            model_version = f"{model_type}_v{version_num}"
            file_path = model_dir / f"{model_version}.pkl"

            with open(file_path, "wb") as f:
                pickle.dump(model, f)

            model_hash = _compute_hash(file_path)

            # best-effort accuracy field
            accuracy: Optional[float] = None
            if metrics:
                # Support rmse/mae/r2 style. If r2 exists, interpret as accuracy.
                if "accuracy" in metrics and isinstance(metrics["accuracy"], (int, float)):
                    accuracy = float(metrics["accuracy"])
                elif "r2" in metrics and isinstance(metrics["r2"], (int, float)):
                    accuracy = float(metrics["r2"])

            row = MlModel(
                model_name=model_type,
                model_version=model_version,
                trained_at=datetime.utcnow(),
                accuracy=accuracy,
                file_path=str(file_path),
                status="active",
                metrics_json=_dumps(metrics),
                hyperparams_json=_dumps(hyperparams),
                features_json=_dumps(features),
            )

            session.add(row)
            session.commit()

            logger.info(
                "ModelRegistry.save: model_type=%s version=%s file=%s hash=%s",
                model_type,
                model_version,
                file_path,
                model_hash,
            )
            return model_version

        except SQLAlchemyError as e:
            session.rollback()
            raise
        finally:
            if should_close:
                session.close()

    @staticmethod
    def save_model(
        model: Any,
        model_type: str,
        metrics: Optional[dict[str, float]] = None,
        hyperparams: Optional[dict[str, Any]] = None,
        features: Optional[list[str]] = None,
        description: str = "",
    ) -> str:
        """Alias for save() for backward compatibility."""
        return ModelRegistry.save(
            model=model,
            model_type=model_type,
            metrics=metrics,
            hyperparams=hyperparams,
            features=features,
            description=description,
        )

    @staticmethod
    def load(model_type: str, version_id: Optional[str] = None) -> Optional[tuple[Any, dict[str, Any]]]:
        """Load a model artifact + metadata.

        - If version_id is None, loads latest active row by trained_at.
        """
        session, should_close = ModelRegistry._get_session()
        try:
            q = select(MlModel).where(MlModel.model_name == model_type, MlModel.status == "active")
            if version_id:
                q = q.where(MlModel.model_version == version_id)
            else:
                q = q.order_by(MlModel.trained_at.desc()).limit(1)

            row = session.execute(q).scalar_one_or_none()
            if row is None:
                return None

            file_path = Path(row.file_path)
            if not file_path.exists():
                logger.error("ModelRegistry.load: missing file_path=%s", row.file_path)
                return None

            with open(file_path, "rb") as f:
                model = pickle.load(f)

            metadata = {
                "version_id": row.model_version,
                "model_type": row.model_name,
                "trained_at": row.trained_at.isoformat() if row.trained_at else None,
                "accuracy": row.accuracy,
                "file_path": row.file_path,
                "status": row.status,
                "metrics": json.loads(row.metrics_json) if row.metrics_json else {},
                "hyperparams": json.loads(row.hyperparams_json) if row.hyperparams_json else {},
                "features": json.loads(row.features_json) if row.features_json else [],
                "description": None,
            }

            return model, metadata
        finally:
            if should_close:
                session.close()

    @staticmethod
    def list_versions(model_type: str) -> list[dict[str, Any]]:
        session, should_close = ModelRegistry._get_session()
        try:
            q = (
                select(MlModel)
                .where(MlModel.model_name == model_type)
                .order_by(MlModel.trained_at.desc())
            )
            rows = session.execute(q).scalars().all()

            out: list[dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "version_id": r.model_version,
                        "model_type": r.model_name,
                        "trained_at": r.trained_at.isoformat() if r.trained_at else None,
                        "accuracy": r.accuracy,
                        "file_path": r.file_path,
                        "status": r.status,
                        "metrics": json.loads(r.metrics_json) if r.metrics_json else {},
                        "hyperparams": json.loads(r.hyperparams_json) if r.hyperparams_json else {},
                        "features": json.loads(r.features_json) if r.features_json else [],
                    }
                )
            return out
        finally:
            if should_close:
                session.close()

    @staticmethod
    def compare_versions(model_type: str) -> list[dict[str, Any]]:
        versions = ModelRegistry.list_versions(model_type)
        return sorted(versions, key=lambda v: v.get("metrics", {}).get("rmse", float("inf")))

    @staticmethod
    def rollback(model_type: str, version_num: int) -> Optional[str]:
        """Rollback to a previous version by version_num.

        version_num is interpreted as the Nth saved row for that model_type.
        """
        session, should_close = ModelRegistry._get_session()
        try:
            # Fetch nth version (ordered by created)
            rows = (
                session.execute(
                    select(MlModel)
                    .where(MlModel.model_name == model_type)
                    .order_by(MlModel.trained_at.asc())
                ).scalars().all()
            )
            if version_num < 1 or version_num > len(rows):
                return None
            target = rows[version_num - 1]

            session.execute(
                MlModel.__table__.update()
                .where(MlModel.model_name == model_type)
                .values(status="inactive")
            )
            session.execute(
                MlModel.__table__.update()
                .where(MlModel.model_name == model_type, MlModel.model_version == target.model_version)
                .values(status="active")
            )
            session.commit()
            return target.model_version
        finally:
            if should_close:
                session.close()

    @staticmethod
    def update_metrics(model_type: str, version_id: str, metrics: dict[str, float]) -> None:
        session, should_close = ModelRegistry._get_session()
        try:
            row = (
                session.execute(
                    select(MlModel).where(MlModel.model_name == model_type, MlModel.model_version == version_id)
                ).scalar_one_or_none()
            )
            if row is None:
                return

            row.metrics_json = _dumps(metrics)
            # also update accuracy best-effort
            if metrics and "r2" in metrics and isinstance(metrics["r2"], (int, float)):
                row.accuracy = float(metrics["r2"])
            elif metrics and "accuracy" in metrics and isinstance(metrics["accuracy"], (int, float)):
                row.accuracy = float(metrics["accuracy"])

            session.commit()
        finally:
            if should_close:
                session.close()

    @staticmethod
    def get_latest_version(model_type: str) -> Optional[str]:
        session, should_close = ModelRegistry._get_session()
        try:
            row = (
                session.execute(
                    select(MlModel)
                    .where(MlModel.model_name == model_type, MlModel.status == "active")
                    .order_by(MlModel.trained_at.desc())
                    .limit(1)
                ).scalar_one_or_none()
            )
            return row.model_version if row else None
        finally:
            if should_close:
                session.close()

    @staticmethod
    def delete_model(model_type: str, version_id: str) -> bool:
        session, should_close = ModelRegistry._get_session()
        try:
            row = (
                session.execute(
                    select(MlModel).where(MlModel.model_name == model_type, MlModel.model_version == version_id)
                ).scalar_one_or_none()
            )
            if row is None:
                return False

            file_path = Path(row.file_path)
            if file_path.exists():
                file_path.unlink()

            session.delete(row)
            session.commit()
            return True
        finally:
            if should_close:
                session.close()

    @staticmethod
    def get_all_model_types() -> list[str]:
        session, should_close = ModelRegistry._get_session()
        try:
            rows = session.execute(select(MlModel.model_name).distinct()).scalars().all()
            return list(rows)
        finally:
            if should_close:
                session.close()

    @staticmethod
    def get_registry_summary() -> dict[str, Any]:
        session, should_close = ModelRegistry._get_session()
        try:
            # For each model_name, compute best rmse (if present) and best accuracy.
            result: dict[str, Any] = {}
            model_types = session.execute(select(MlModel.model_name).distinct()).scalars().all()
            for mt in model_types:
                vers = ModelRegistry.list_versions(mt)
                best_rmse = min((v.get("metrics", {}).get("rmse", float("inf")) for v in vers), default=None)
                best_accuracy = max((v.get("metrics", {}).get("accuracy", v.get("accuracy", 0) or 0) for v in vers), default=None)
                result[mt] = {
                    "total_versions": len(vers),
                    "latest": ModelRegistry.get_latest_version(mt),
                    "best_rmse": None if best_rmse == float("inf") else best_rmse,
                    "best_accuracy": best_accuracy,
                }
            return result
        finally:
            if should_close:
                session.close()

