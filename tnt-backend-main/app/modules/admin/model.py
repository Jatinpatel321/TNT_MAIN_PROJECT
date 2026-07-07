from sqlalchemy import Column, DateTime, Integer, String

from app.core.time_utils import utcnow_naive
from app.database.base import Base


class SystemConfig(Base):
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(500), nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)