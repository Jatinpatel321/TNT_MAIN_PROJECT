import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.database.base import Base
from app.main import app
from app.modules.users.model import User, UserRole
from app.core.security import create_access_token


class _FakeRedis:
    def __init__(self):
        self.data = {}

    def ping(self):
        return True

    def llen(self, key):
        return 0

    def lpush(self, key, val):
        return 1

    def rpush(self, key, val):
        return 1

    def ltrim(self, key, start, end):
        return True

    def lrange(self, key, start, end):
        return []


@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def admin_token(test_db_session):
    admin_user = User(
        phone="9999999999",
        name="Admin User",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    test_db_session.add(admin_user)
    test_db_session.commit()
    test_db_session.refresh(admin_user)
    return create_access_token({"sub": str(admin_user.id), "phone": admin_user.phone, "role": "admin"}, expires_delta=60)


def test_admin_health_endpoints(test_db_session, admin_token, monkeypatch):
    # Mock database dependency
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock Redis client in health service
    fake_redis = _FakeRedis()
    monkeypatch.setattr("app.modules.health.service.redis_client", fake_redis)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Test GET /v1/admin/health/metrics
    response = client.get("/v1/admin/health/metrics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    
    # Assert top-level keys
    assert "status" in data
    assert "timestamp" in data
    assert "subsystems" in data
    assert "history" in data

    # Assert subsystems presence
    subsystems = data["subsystems"]
    for sys_name in [
        "backend", "database", "redis", "notifications",
        "ai_engine", "storage", "api_health", "queue_health"
    ]:
        assert sys_name in subsystems
        assert "status" in subsystems[sys_name]

    # Assert overall status
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

    # Test GET /v1/admin/health/status
    status_response = client.get("/v1/admin/health/status", headers=headers)
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert "status" in status_data
    assert status_data["status"] == data["status"]

    app.dependency_overrides.clear()
