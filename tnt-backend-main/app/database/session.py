import json
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.money import json_default

# 🔥 EXPLICITLY LOAD .env FROM PROJECT ROOT
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found. Check your .env file location.")

# Use pg8000 (pure Python) driver — no C compiler needed
if DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)


def _json_serializer(obj) -> str:
    """SQLAlchemy JSON-column serializer that also handles Decimal (money).

    Without this, any JSON column (e.g. audit_logs.before_state/after_state)
    storing a dict with a Decimal amount raises
    ``TypeError: Object of type Decimal is not JSON serializable``.
    """
    return json.dumps(obj, default=json_default)


engine = create_engine(DATABASE_URL, json_serializer=_json_serializer)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency to get DB session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
