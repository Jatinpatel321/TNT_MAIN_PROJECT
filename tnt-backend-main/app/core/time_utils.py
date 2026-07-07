from datetime import UTC, datetime
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def ist_now() -> datetime:
    """Return current IST time as a timezone-naive datetime (for DB storage)."""
    return datetime.now(IST).replace(tzinfo=None)
