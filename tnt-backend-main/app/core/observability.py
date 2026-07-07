import logging
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import httpx
from fastapi import Request

logger = logging.getLogger("tnt.observability")


@dataclass
class RouteMetric:
    requests: int = 0
    server_errors: int = 0
    total_latency_ms: float = 0.0


@dataclass
class MetricsState:
    total_requests: int = 0
    server_errors: int = 0
    started_at: float = field(default_factory=time.time)
    per_route: dict[str, RouteMetric] = field(default_factory=lambda: defaultdict(RouteMetric))
    last_alert_at: float = 0.0

    # ── Business metrics ──────────────────────────────────────────────────
    # OTP success rate
    otp_attempts_total: int = 0
    otp_success_total: int = 0

    # Payment failures (signature mismatch + webhook payment.failed)
    payment_failures_total: int = 0

    # Vendor confirmation latency (PLACED → CONFIRMED), last 1 000 samples
    vendor_confirm_latency_samples: deque = field(
        default_factory=lambda: deque(maxlen=1000)
    )


class Observability:
    def __init__(self):
        self.state = MetricsState()

    async def track_request(self, request: Request, call_next):
        route_key = f"{request.method} {request.url.path}"
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self.state.total_requests += 1

            route_metric = self.state.per_route[route_key]
            route_metric.requests += 1
            route_metric.total_latency_ms += elapsed_ms

            if status_code >= 500:
                self.state.server_errors += 1
                route_metric.server_errors += 1

    def error_rate_percent(self) -> float:
        if self.state.total_requests == 0:
            return 0.0
        return (self.state.server_errors / self.state.total_requests) * 100.0

    # ── Business metric recorders ─────────────────────────────────────────

    def record_otp_attempt(self, *, success: bool) -> None:
        """Call once per /auth/verify-otp invocation; pass success=True on valid OTP."""
        self.state.otp_attempts_total += 1
        if success:
            self.state.otp_success_total += 1

    def record_payment_failure(self) -> None:
        """Call when a payment is rejected (bad signature) or webhook payment.failed fires."""
        self.state.payment_failures_total += 1

    def record_vendor_confirmation(self, latency_ms: float) -> None:
        """Record how many ms elapsed from order placement to vendor confirmation."""
        self.state.vendor_confirm_latency_samples.append(latency_ms)

    def otp_success_rate_percent(self) -> float:
        if self.state.otp_attempts_total == 0:
            return 0.0
        return (self.state.otp_success_total / self.state.otp_attempts_total) * 100.0

    def _vendor_latency_stats(self) -> dict:
        samples = list(self.state.vendor_confirm_latency_samples)
        n = len(samples)
        if n == 0:
            return {"count": 0, "avg_ms": None, "p50_ms": None, "p95_ms": None}
        avg = sum(samples) / n
        if n < 2:
            return {"count": n, "avg_ms": round(avg, 2), "p50_ms": round(avg, 2), "p95_ms": None}
        qs = statistics.quantiles(samples, n=100)
        return {
            "count": n,
            "avg_ms": round(avg, 2),
            "p50_ms": round(qs[49], 2),
            "p95_ms": round(qs[94], 2),
        }

    def maybe_alert_error_budget(
        self,
        threshold_percent: float,
        min_requests: int,
        alert_webhook_url: str | None = None,
    ) -> None:
        if self.state.total_requests < min_requests:
            return

        current_rate = self.error_rate_percent()
        now = time.time()
        if current_rate > threshold_percent and now - self.state.last_alert_at >= 60:
            message = (
                "Error budget breached: "
                f"error_rate={current_rate:.2f}% threshold={threshold_percent:.2f}% "
                f"requests={self.state.total_requests} server_errors={self.state.server_errors}"
            )
            logger.error(message)

            if alert_webhook_url:
                try:
                    httpx.post(
                        alert_webhook_url,
                        json={
                            "event": "error_budget_breach",
                            "error_rate_percent": current_rate,
                            "threshold_percent": threshold_percent,
                            "total_requests": self.state.total_requests,
                            "server_errors": self.state.server_errors,
                        },
                        timeout=2.0,
                    )
                except Exception:
                    logger.exception("Failed to deliver error budget alert webhook")

            self.state.last_alert_at = now

    def snapshot(self) -> dict:
        routes = {}
        for route, metric in self.state.per_route.items():
            avg_latency = metric.total_latency_ms / metric.requests if metric.requests else 0.0
            routes[route] = {
                "requests": metric.requests,
                "server_errors": metric.server_errors,
                "avg_latency_ms": round(avg_latency, 2),
            }

        uptime_seconds = int(time.time() - self.state.started_at)
        return {
            "uptime_seconds": uptime_seconds,
            "total_requests": self.state.total_requests,
            "server_errors": self.state.server_errors,
            "error_rate_percent": round(self.error_rate_percent(), 4),
            # ── Business metrics ─────────────────────────────────────────
            "otp": {
                "attempts_total": self.state.otp_attempts_total,
                "success_total": self.state.otp_success_total,
                "success_rate_percent": round(self.otp_success_rate_percent(), 4),
            },
            "payment_failures_total": self.state.payment_failures_total,
            "vendor_confirmation_latency": self._vendor_latency_stats(),
            # ─────────────────────────────────────────────────────────────
            "routes": routes,
        }


observability = Observability()
