"""
Tests for the ledger endpoint:
  GET /ledger/  – admin-only listing of all ledger entries
"""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.ledger.model import Ledger, LedgerSource, LedgerType
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    admin = User(phone="8800000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="8800000002", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="8800000003",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
        vendor_type="food",
    )
    test_db_session.add_all([admin, student, vendor])
    test_db_session.commit()
    for u in (admin, student, vendor):
        test_db_session.refresh(u)

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
    test_db_session.refresh(slot)

    order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.CONFIRMED,
        total_amount=10000,
    )
    test_db_session.add(order)
    test_db_session.commit()
    test_db_session.refresh(order)

    payment = Payment(
        order_id=order.id,
        amount=10000,
        status=PaymentStatus.SUCCESS,
    )
    test_db_session.add(payment)
    test_db_session.commit()
    test_db_session.refresh(payment)

    entry1 = Ledger(
        order_id=order.id,
        payment_id=payment.id,
        amount=10000,
        entry_type=LedgerType.CREDIT,
        source=LedgerSource.PAYMENT,
        description="Payment received",
    )
    entry2 = Ledger(
        order_id=order.id,
        payment_id=None,
        amount=2000,
        entry_type=LedgerType.DEBIT,
        source=LedgerSource.REFUND,
        description="Partial refund",
    )
    test_db_session.add_all([entry1, entry2])
    test_db_session.commit()
    for e in (entry1, entry2):
        test_db_session.refresh(e)

    return {
        "admin": admin,
        "student": student,
        "vendor": vendor,
        "order": order,
        "payment": payment,
        "entry1": entry1,
        "entry2": entry2,
    }


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /ledger/
# ---------------------------------------------------------------------------


def test_admin_can_list_ledger_entries(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_ledger_returns_all_entries(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    ids = {e["id"] for e in resp.json()}
    assert seed_data["entry1"].id in ids
    assert seed_data["entry2"].id in ids


def test_ledger_entry_has_required_fields(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    entry = resp.json()[0]
    for field in ("id", "amount", "entry_type", "source", "order_id"):
        assert field in entry, f"Missing field: {field}"


def test_ledger_credit_entry_has_correct_type(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    entries = {e["id"]: e for e in resp.json()}
    assert entries[seed_data["entry1"].id]["entry_type"] == "credit"


def test_ledger_debit_entry_has_correct_type(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["admin"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    entries = {e["id"]: e for e in resp.json()}
    assert entries[seed_data["entry2"].id]["entry_type"] == "debit"


def test_student_cannot_access_ledger(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["student"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_vendor_cannot_access_ledger(test_db_session, seed_data):
    client = _make_client(test_db_session, seed_data["vendor"])
    resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    assert resp.status_code == 403


def test_unauthenticated_cannot_access_ledger(test_db_session):
    app.dependency_overrides[get_db] = lambda: test_db_session
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/ledger/")
    app.dependency_overrides.clear()

    assert resp.status_code in (401, 403)
