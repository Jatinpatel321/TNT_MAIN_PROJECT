import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def _as_bool(value: str | None, default: bool = False) -> bool:
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None, default: list[str]) -> list[str]:
	if not value:
		return default
	items = [item.strip() for item in value.split(",") if item.strip()]
	return items or default


class Settings:
	APP_ENV: str = os.getenv("APP_ENV", "development")

	CORS_ORIGINS: list[str] = _as_list(
		os.getenv("CORS_ORIGINS"),
		["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
	)

	DB_REVISION_GUARD: bool = _as_bool(
		os.getenv("DB_REVISION_GUARD"),
		default=(APP_ENV == "production"),
	)

	ENABLE_METRICS: bool = _as_bool(os.getenv("ENABLE_METRICS"), default=True)
	ERROR_BUDGET_PERCENT: float = float(os.getenv("ERROR_BUDGET_PERCENT", "1.0"))
	ERROR_BUDGET_MIN_REQUESTS: int = int(os.getenv("ERROR_BUDGET_MIN_REQUESTS", "100"))
	ALERT_WEBHOOK_URL: str | None = os.getenv("ALERT_WEBHOOK_URL")
	LOG_JSON: bool = _as_bool(os.getenv("LOG_JSON"), default=(APP_ENV == "production"))

	ENABLE_ORDER_SIMULATOR: bool = _as_bool(
		os.getenv("ENABLE_ORDER_SIMULATOR"),
		default=(APP_ENV != "production"),
	)

	SMS_ENABLED: bool = _as_bool(os.getenv("SMS_ENABLED"), default=(APP_ENV == "production"))
	SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "twilio").strip().lower()
	SMS_FROM: str | None = os.getenv("SMS_FROM")

	TWILIO_ACCOUNT_SID: str | None = os.getenv("TWILIO_ACCOUNT_SID")
	TWILIO_AUTH_TOKEN: str | None = os.getenv("TWILIO_AUTH_TOKEN")

	MSG91_AUTH_KEY: str | None = os.getenv("MSG91_AUTH_KEY")
	MSG91_SENDER_ID: str | None = os.getenv("MSG91_SENDER_ID")
	MSG91_ROUTE: str = os.getenv("MSG91_ROUTE", "4")


settings = Settings()

