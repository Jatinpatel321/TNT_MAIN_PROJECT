from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user, get_current_user_id
from app.database.base import Base
from app.main import app
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    student = User(phone="9700000001", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9700000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([student, vendor])
    test_db_session.commit()
    test_db_session.refresh(student)
    test_db_session.refresh(vendor)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()

    return {"student": student}


@pytest.fixture()
def auth_context(seed_data):
    student = seed_data["student"]
    return {"id": student.id, "phone": student.phone, "role": student.role.value}


@pytest.fixture()
def client(test_db_session, auth_context):
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    def override_get_current_user():
        return auth_context

    def override_get_current_user_id():
        return auth_context["id"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_user_id] = override_get_current_user_id

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_ai_signal_routes_available_and_legacy_routes_removed(client):
    ai_endpoints = {
        "/ai/signals": "signals",
        "/ai/signals/rush-hour": "signals",
        "/ai/signals/slot-suggestions": "signals",
        "/ai/signals/reorder-prompts": "signals",
    }

    for endpoint, expected_key in ai_endpoints.items():
        ai_response = client.get(endpoint)
        assert ai_response.status_code == 200
        payload = ai_response.json()
        assert expected_key in payload
        assert isinstance(payload[expected_key], list)

    legacy_endpoints = [
        "/signals/",
        "/signals/rush-hour",
        "/signals/slot-suggestions",
        "/signals/reorder-prompts",
    ]

    for endpoint in legacy_endpoints:
        legacy_response = client.get(endpoint)
        assert legacy_response.status_code == 404


def test_legacy_signals_prefix_is_not_registered(client):
    for endpoint in ["/signals", "/signals/"]:
        response = client.get(endpoint)
        assert response.status_code == 404
