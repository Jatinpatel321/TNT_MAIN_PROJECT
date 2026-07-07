from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database.base import Base
from app.core.time_utils import utcnow_naive


class MlModel(Base):
    """Database-backed ML model registry.

    This replaces the previous file-based JSON registry.

    Notes:
    - `file_path` points to the pickled model artifact on disk.
    - `accuracy` is best-effort: for regressors we store R2 if available,
      otherwise RMSE/MAE are left in `metrics_json`.
    - `status` supports soft rollout / rollback.
    """

    __tablename__ = "ml_models"

    id = Column(Integer, primary_key=True, index=True)

    model_name = Column(String(200), nullable=False, index=True)
    model_version = Column(String(100), nullable=False)
    trained_at = Column(DateTime, default=utcnow_naive)

    # best-effort single accuracy field
    accuracy = Column(Float, nullable=True)

    file_path = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="active", server_default="active")

    # optional JSON-like string payload to store metrics/hyperparams/features
    metrics_json = Column(Text, nullable=True)
    hyperparams_json = Column(Text, nullable=True)
    features_json = Column(Text, nullable=True)

