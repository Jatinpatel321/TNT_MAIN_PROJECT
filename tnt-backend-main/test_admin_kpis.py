from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
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
def seed_data(test_db_session):
    admin = User(phone="8900000001", name="Admin", role=UserRole.ADMIN, is_active=True, department="Administration")
    student1 = User(phone="8900000002", name="Student CS", role=UserRole.STUDENT, is_active=True, department="Computer Science")
    student2 = User(phone="8900000003", name="Student EE", role=UserRole.STUDENT, is_active=True, department="Electrical Engineering")
    vendor = User(
        phone="8900000004",
        name="MainVendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
        vendor_type="food",
    )
    test_db_session.add_all([admin, student1, student2, vendor])
    test_db_session.commit()

    # Seed slots
    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() - timedelta(hours=2),
        end_time=utcnow_naive() - timedelta(hours=1),
        max_orders=10,
        current_orders=2,
        status=SlotStatus.AVAILABLE,
    )
    test_db_session.add(slot)
    test_db_session.commit()

    # Seed orders
    order1 = Order(
        user_id=student1.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PICKED,
        total_amount=15000,
        booking_type="food",
        actual_completion_minutes=12,
        pickup_confirmed_at=utcnow_naive(),
    )
    order2 = Order(
        user_id=student2.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.CANCELLED,
        total_amount=5000,
        booking_type="stationery",
    )
    test_db_session.add_all([order1, order2])
    test_db_session.commit()

    # Seed payment for order1 (success) and order2 (refunded)
    p1 = Payment(
        order_id=order1.id,
        amount=15000,
        status=PaymentStatus.SUCCESS,
    )
    p2 = Payment(
        order_id=order2.id,
        amount=5000,
        status=PaymentStatus.REFUNDED,
    )
    test_db_session.add_all([p1, p2])
    test_db_session.commit()

    return {
        "admin": admin,
        "student1": student1,
        "student2": student2,
        "vendor": vendor,
    }


def test_admin_kpis_endpoint(test_db_session, seed_data):
    # Mock current admin user
    def mock_require_admin():
        return {"id": seed_data["admin"].id, "role": "admin"}

    app.dependency_overrides[get_db] = lambda: test_db_session
    app.dependency_overrides[get_current_user] = mock_require_admin
    # If app core checks require_role("admin"), overrides may need to bypass it:
    from app.core.security import require_role
    app.dependency_overrides[require_role("admin")] = mock_require_admin

    client = TestClient(app)

    # 1. Fetch KPIs
    response = client.get("/v1/admin/analytics/kpis")
    assert response.status_code == 200
    data = response.json()

    assert "university_kpis" in data
    assert "operational_kpis" in data
    assert "business_kpis" in data
    assert "engagement_kpis" in data

    # Verify aggregates
    assert data["university_kpis"]["total_orders"] == 2
    assert data["university_kpis"]["food_orders"] == 1
    assert data["university_kpis"]["stationery_orders"] == 1

    # Verify filters (e.g. Computer Science)
    response_cs = client.get("/v1/admin/analytics/kpis?department=Computer Science")
    assert response_cs.status_code == 200
    data_cs = response_cs.json()
    assert data_cs["university_kpis"]["total_orders"] == 1
    assert data_cs["university_kpis"]["food_orders"] == 1
    assert data_cs["university_kpis"]["stationery_orders"] == 0

    # 2. Export Excel
    response_excel = client.get("/v1/admin/export/kpis?format=excel")
    assert response_excel.status_code == 200
    assert response_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # 3. Export PDF
    response_pdf = client.get("/v1/admin/export/kpis?format=pdf")
    assert response_pdf.status_code == 200
    assert response_pdf.headers["content-type"] == "application/pdf"

    # Clean up overrides
    app.dependency_overrides.clear()
