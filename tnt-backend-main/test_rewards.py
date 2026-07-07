import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.rewards.model import RewardType
from app.modules.rewards.service import award_points
from app.modules.users.model import User, UserRole


@pytest.fixture()
def test_db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def seed_data(test_db_session):
    admin = User(phone="7200000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="7200000002", name="Student", role=UserRole.STUDENT, is_active=True)
    test_db_session.add_all([admin, student])
    test_db_session.commit()
    test_db_session.refresh(admin)
    test_db_session.refresh(student)
    return {"admin": admin, "student": student}


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

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_rewards_flow(client, test_db_session, seed_data, auth_context):
    admin = seed_data["admin"]
    student = seed_data["student"]

    init_as_student = client.post("/rewards/initialize-rules")
    assert init_as_student.status_code == 403

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})
    init_as_admin = client.post("/rewards/initialize-rules")
    assert init_as_admin.status_code == 200

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})

    before_points = client.get("/rewards/points")
    assert before_points.status_code == 200
    assert before_points.json()["current_points"] == 0.0

    award_points(
        user_id=student.id,
        reward_type=RewardType.ORDER_COMPLETION,
        points=120.0,
        description="Test award",
        db=test_db_session,
    )

    after_points = client.get("/rewards/points")
    assert after_points.status_code == 200
    assert after_points.json()["current_points"] == 120.0

    redemptions = client.get("/rewards/redemptions")
    assert redemptions.status_code == 200
    assert len(redemptions.json()) >= 1

    redeem_resp = client.post(
        "/rewards/redeem",
        json={
            "redemption_type": "discount_percentage",
            "points_used": 50,
            "value": 10,
        },
    )
    assert redeem_resp.status_code == 200

    final_points = client.get("/rewards/points")
    assert final_points.status_code == 200
    assert final_points.json()["current_points"] == 70.0
