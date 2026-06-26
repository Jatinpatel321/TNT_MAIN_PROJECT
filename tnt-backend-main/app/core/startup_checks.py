from alembic.script import ScriptDirectory
from alembic.config import Config
from sqlalchemy import inspect, text

from app.database.session import engine


def validate_production_settings(app_env: str, cors_origins: list[str]) -> None:
    if app_env != "production":
        return

    if not cors_origins:
        raise RuntimeError("CORS_ORIGINS cannot be empty in production")

    if "*" in cors_origins:
        raise RuntimeError("Wildcard CORS is not allowed in production")

    invalid_local = [origin for origin in cors_origins if "localhost" in origin or "127.0.0.1" in origin]
    if invalid_local:
        raise RuntimeError(
            f"Localhost origins are not allowed in production CORS: {invalid_local}"
        )

    from app.core.config import settings

    if not settings.SMS_ENABLED:
        return

    provider = settings.SMS_PROVIDER
    if provider == "twilio":
        missing = []
        if not settings.TWILIO_ACCOUNT_SID:
            missing.append("TWILIO_ACCOUNT_SID")
        if not settings.TWILIO_AUTH_TOKEN:
            missing.append("TWILIO_AUTH_TOKEN")
        if not settings.SMS_FROM:
            missing.append("SMS_FROM")
        if missing:
            raise RuntimeError(f"Missing Twilio SMS settings in production: {missing}")
    elif provider == "msg91":
        missing = []
        if not settings.MSG91_AUTH_KEY:
            missing.append("MSG91_AUTH_KEY")
        if not settings.MSG91_SENDER_ID:
            missing.append("MSG91_SENDER_ID")
        if missing:
            raise RuntimeError(f"Missing MSG91 SMS settings in production: {missing}")
    else:
        raise RuntimeError(f"Unsupported SMS_PROVIDER in production: {provider}")


def verify_database_revision() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    expected_head = script.get_current_head()

    with engine.connect() as connection:
        inspector = inspect(connection)
        table_name = inspector.has_table("alembic_version")

        if not table_name:
            raise RuntimeError(
                "Database revision table missing. Run: alembic stamp 20260214_0001 ; alembic upgrade head"
            )

        current_revision = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()

    if current_revision != expected_head:
        raise RuntimeError(
            f"Database schema is not at head. Current={current_revision}, Expected={expected_head}. "
            "Run: alembic upgrade head"
        )
