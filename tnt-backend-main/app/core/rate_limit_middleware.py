"""Starlette HTTP middleware: IP-based rate limiting for payment endpoints.

Covers every route whose path starts with ``/payments/`` or
``/stationery/payments/`` so that all current *and future* payment endpoints
are protected automatically without modifying individual route handlers.

The thresholds are delegated to ``app.core.rate_limit`` which reads them from
environment variables — DevOps can tune them without code changes.

Fail-open policy
----------------
If Redis is unavailable the middleware lets the request through.  The core
``check_rate_limit`` helper already implements this; the middleware simply
converts the resulting ``HTTPException(429)`` into a proper ``JSONResponse``.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.rate_limit import PAYMENT_LIMIT, PAYMENT_WINDOW, _client_ip, check_rate_limit
from app.core.redis import redis_client

logger = logging.getLogger(__name__)

# Path prefixes protected by this middleware — covers both legacy and v1 paths.
_GUARDED_PREFIXES: tuple[str, ...] = (
    # legacy (un-prefixed)
    "/payments/",
    "/stationery/payments/",
    # v1
    "/v1/payments/",
    "/v1/stationery/payments/",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply IP-based rate limiting to all payment-related routes.

    The middleware is intentionally narrow — only the prefixes listed in
    ``_GUARDED_PREFIXES`` are checked.  Everything else passes through
    untouched.

    An optional *redis* parameter is accepted so that tests can inject a
    fake Redis client without monkey-patching the module-level import.
    """

    def __init__(self, app, redis=None) -> None:
        super().__init__(app)
        self._redis = redis  # None → falls back to the app-level client

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path.startswith(prefix) for prefix in _GUARDED_PREFIXES):
            ip = _client_ip(request)
            key = f"ratelimit:payments:{ip}"
            r = self._redis if self._redis is not None else redis_client
            try:
                check_rate_limit(key, PAYMENT_LIMIT, PAYMENT_WINDOW, redis=r)
            except HTTPException as exc:
                if exc.status_code == 429:
                    retry_after = (exc.headers or {}).get("Retry-After", str(PAYMENT_WINDOW))
                    return JSONResponse(
                        status_code=429,
                        content=exc.detail,
                        headers={"Retry-After": retry_after},
                    )
                raise

        return await call_next(request)
