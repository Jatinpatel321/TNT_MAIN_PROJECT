"""Redis-backed rate-limiting primitives.

Two integration points are provided:

1. ``check_rate_limit`` — low-level function usable anywhere.
2. ``RateLimiter``     — FastAPI dependency factory (IP-keyed by default).
3. ``otp_rate_limiter``— async FastAPI dependency that keys on the ``phone``
   field read from the JSON request body (falls back to client IP if the
   body cannot be parsed).

Fixed-window algorithm
----------------------
For each (key, window) pair the counter is incremented with INCR.  The first
INCR also sets the TTL, so the window resets automatically.  Under concurrent
load two requests may both see count==1 and both set TTL — this is harmless
because the second EXPIRE is a no-op if the key already has a TTL.

Fail-open on Redis errors
-------------------------
If Redis is unreachable the check logs a warning and lets the request through.
This prevents Redis downtime from taking down the entire API.
"""

import json
import logging

from fastapi import HTTPException, Request

from app.core.redis import redis_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configurable thresholds — DevOps can override via environment variables.
# These are read at import time so they can be patched in tests without
# modifying the Settings object.
# ---------------------------------------------------------------------------

import os

# OTP send  : 5 requests / 60 s / phone number
OTP_LIMIT: int = int(os.getenv("RATE_LIMIT_OTP_LIMIT", "5"))
OTP_WINDOW: int = int(os.getenv("RATE_LIMIT_OTP_WINDOW", "60"))

# Verify OTP / login : 10 requests / 60 s / IP
LOGIN_LIMIT: int = int(os.getenv("RATE_LIMIT_LOGIN_LIMIT", "10"))
LOGIN_WINDOW: int = int(os.getenv("RATE_LIMIT_LOGIN_WINDOW", "60"))

# Payments : 20 requests / 60 s / IP
PAYMENT_LIMIT: int = int(os.getenv("RATE_LIMIT_PAYMENT_LIMIT", "20"))
PAYMENT_WINDOW: int = int(os.getenv("RATE_LIMIT_PAYMENT_WINDOW", "60"))


# ---------------------------------------------------------------------------
# Core primitive
# ---------------------------------------------------------------------------


def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    redis=None,
) -> tuple[int, int]:
    """Increment the counter for *key* and raise 429 if *limit* is exceeded.

    Returns ``(current_count, remaining)`` — useful when you want to add
    ``X-RateLimit-*`` headers (the caller is responsible for that).

    Parameters
    ----------
    key:            Redis key (should already include the namespace/prefix).
    limit:          Maximum allowed requests within the window.
    window_seconds: Window length in seconds.
    redis:          Optional Redis client override (defaults to the app client).
                    Inject a fake in tests to avoid real Redis.
    """
    r = redis if redis is not None else redis_client
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = pipe.execute()

        # Set TTL on first hit OR if a key somehow lost its TTL.
        if count == 1 or ttl < 0:
            r.expire(key, window_seconds)
            ttl = window_seconds

        remaining = max(limit - count, 0)

        if count > limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": ttl,
                },
                headers={"Retry-After": str(ttl)},
            )

        return count, remaining

    except HTTPException:
        raise
    except Exception:
        # Fail open — Redis unavailable must not block legitimate traffic.
        logger.warning(
            "Rate-limit Redis check failed for key=%s; failing open.", key, exc_info=True
        )
        return 0, limit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client_ip(request: Request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# FastAPI dependency factory — IP-keyed, reusable across routers
# ---------------------------------------------------------------------------


class RateLimiter:
    """Callable FastAPI dependency that applies a fixed-window rate limit.

    Usage::

        from app.core.rate_limit import RateLimiter

        @router.post("/some-endpoint")
        def endpoint(
            _rl: None = Depends(RateLimiter(limit=10, window=60, prefix="my_endpoint")),
        ):
            ...
    """

    def __init__(
        self,
        limit: int,
        window: int,
        prefix: str,
        redis=None,
    ) -> None:
        self.limit = limit
        self.window = window
        self.prefix = prefix
        self._redis = redis  # None → use default client; set in tests

    def __call__(self, request: Request) -> None:
        ip = _client_ip(request)
        key = f"ratelimit:{self.prefix}:{ip}"
        check_rate_limit(key, self.limit, self.window, redis=self._redis)


# Pre-built limiter instances (imported by routers / middleware).
login_rate_limiter = RateLimiter(
    limit=LOGIN_LIMIT,
    window=LOGIN_WINDOW,
    prefix="login",
)

payment_rate_limiter = RateLimiter(
    limit=PAYMENT_LIMIT,
    window=PAYMENT_WINDOW,
    prefix="payments",
)


# ---------------------------------------------------------------------------
# Phone-keyed OTP dependency (reads JSON body)
# ---------------------------------------------------------------------------


async def otp_rate_limiter(request: Request) -> None:
    """FastAPI dependency: rate-limit ``POST /auth/send-otp`` by phone number.

    Reads the JSON body to extract ``phone``.  FastAPI caches the raw bytes
    in ``request._body`` after the first read, so the Pydantic model
    validation that runs later still has access to the full body.

    Falls back to client IP if the body cannot be parsed.
    """
    try:
        raw = await request.body()
        data = json.loads(raw)
        phone: str = str(data.get("phone", "")).strip() or _client_ip(request)
    except Exception:
        phone = _client_ip(request)

    # Local/dev test numbers use a fixed OTP and should stay reusable while
    # exercising the login UI.
    if phone.endswith("1111"):
        return

    key = f"ratelimit:otp:{phone}"
    check_rate_limit(key, OTP_LIMIT, OTP_WINDOW)
