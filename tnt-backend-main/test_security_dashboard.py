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
from app.core import security_monitor

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

def test_security_metrics_endpoint(test_db_session, admin_token):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get("/v1/admin/security/metrics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "active_sessions" in data
    assert "jwt_failures" in data
    assert "rate_limit_violations" in data
    assert "api_abuse" in data
    
    app.dependency_overrides.clear()

def test_security_events_endpoint(admin_token):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Log a dummy security event
    security_monitor.log_security_event("test_event", "low", {"info": "test"})
    
    response = client.get("/v1/admin/security/events", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["event_type"] == "test_event"

def test_ip_blocking_endpoints(admin_token):
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Block a target
    payload = {"target": "1.2.3.4", "reason": "abusive requests", "duration_seconds": 10}
    res = client.post("/v1/admin/security/ip-blocks", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True
    
    # Retrieve blocked targets
    res = client.get("/v1/admin/security/ip-blocks", headers=headers)
    assert res.status_code == 200
    assert "1.2.3.4" in res.json()
    assert res.json()["1.2.3.4"] == "abusive requests"
    
    # Unblock
    res = client.delete("/v1/admin/security/ip-blocks/1.2.3.4", headers=headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

def test_update_user_role_endpoint(test_db_session, admin_token):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Create target student user
    student = User(
        phone="9888888888",
        name="Student User",
        full_name="Student User",
        role=UserRole.STUDENT,
        is_active=True,
    )
    test_db_session.add(student)
    test_db_session.commit()
    test_db_session.refresh(student)
    
    # Change role to faculty
    payload = {"role": "faculty"}
    res = client.patch(f"/v1/admin/users/{student.id}/role", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["role"] == "faculty"
    
    # Verify in DB
    updated = test_db_session.query(User).filter(User.id == student.id).first()
    assert updated.role == UserRole.FACULTY
    
    app.dependency_overrides.clear()
