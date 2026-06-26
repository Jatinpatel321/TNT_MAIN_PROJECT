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
        self.cache = {}

    async def get_or_set(self, category, identifier, fetch_func, ttl=300):
        # Bypass cache for test simplicity, executing fetch directly
        return fetch_func()


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


def test_extended_analytics_endpoint(test_db_session, admin_token, monkeypatch):
    # Override get_db dependency
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock cache_service to run without actual Redis
    fake_cache = _FakeRedis()
    monkeypatch.setattr("app.core.redis_cache.cache_service", fake_cache)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch the extended KPIs
    response = client.get("/v1/admin/analytics/kpis", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Verify extended properties existence
    assert "department_analytics" in data
    assert "food_trends" in data
    assert "stationery_trends" in data
    assert "revenue_trends" in data
    assert "peak_hour_analysis" in data
    assert "slot_usage_analysis" in data
    assert "cancellation_trends" in data
    assert "ai_insights" in data

    # Verify AI insights structure and types
    ai_insights = data["ai_insights"]
    assert isinstance(ai_insights, list)
    for insight in ai_insights:
        assert "type" in insight
        assert "title" in insight
        assert "detail" in insight
        assert "recommendation" in insight
        assert insight["type"] in ["info", "warning", "success", "danger"]

    # Verify peak hour analysis structure
    peak_hour = data["peak_hour_analysis"]
    assert len(peak_hour) == 24
    assert peak_hour[0]["hour"] == 0
    assert "food_orders" in peak_hour[0]
    assert "stationery_orders" in peak_hour[0]

    app.dependency_overrides.clear()
