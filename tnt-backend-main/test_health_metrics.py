import pytest
from fastapi.testclient import TestClient

from app.core.observability import MetricsState, observability
from app.main import app


class _FakeConnection:
    def exec_driver_sql(self, _query: str):
        return 1

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def connect(self):
        return _FakeConnection()


class _FakeRedis:
    def ping(self):
        return True


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setattr("app.main.engine", _FakeEngine())
    monkeypatch.setattr("app.main.redis_client", _FakeRedis())
    observability.state = MetricsState()

    with TestClient(app) as test_client:
        yield test_client


def test_health_and_metrics_endpoints(client):
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json() == {"status": "ok"}

    ready_resp = client.get("/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

    deep_resp = client.get("/health/deep")
    assert deep_resp.status_code == 200
    deep_body = deep_resp.json()
    assert deep_body["status"] == "ready"
    assert deep_body["checks"]["database"] == "ok"
    assert deep_body["checks"]["redis"] == "ok"

    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    body = metrics_resp.json()

    assert "total_requests" in body
    assert "server_errors" in body
    assert "error_rate_percent" in body
    assert "routes" in body
    assert body["total_requests"] >= 3

    route_keys = body["routes"].keys()
    assert "GET /health/live" in route_keys
    assert "GET /health/ready" in route_keys
    assert len(route_keys) >= 3
