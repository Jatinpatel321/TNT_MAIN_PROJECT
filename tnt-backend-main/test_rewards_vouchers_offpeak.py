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
from app.modules.ledger.model import Ledger, LedgerSource
from app.modules.orders.model import Order, OrderStatus
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
    admin = User(phone="9400000001", name="Admin", role=UserRole.ADMIN, is_active=True)
    student = User(phone="9400000002", name="Student", role=UserRole.STUDENT, is_active=True)
    vendor = User(
        phone="9400000010",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    test_db_session.add_all([admin, student, vendor])
    test_db_session.commit()
    test_db_session.refresh(admin)
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
    test_db_session.refresh(slot)

    voucher_order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=8000,
        created_at=utcnow_naive(),
    )
    completion_order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.CONFIRMED,
        total_amount=10000,
        created_at=utcnow_naive(),
    )
    test_db_session.add_all([voucher_order, completion_order])
    test_db_session.commit()
    test_db_session.refresh(voucher_order)
    test_db_session.refresh(completion_order)

    return {
        "admin": admin,
        "student": student,
        "vendor": vendor,
        "voucher_order": voucher_order,
        "completion_order": completion_order,
    }


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


def test_voucher_crud_redeem_and_expiry(client, seed_data, auth_context, test_db_session):
    admin = seed_data["admin"]
    student = seed_data["student"]
    voucher_order = seed_data["voucher_order"]

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})

    expiry = (utcnow_naive() + timedelta(days=2)).isoformat()
    create_resp = client.post(
        "/rewards/vouchers",
        json={
            "code": "SAVE10",
            "description": "Ten percent off",
            "discount_type": "percentage",
            "discount_value": 10,
            "min_order_amount_paise": 5000,
            "max_discount_amount_paise": 1000,
            "usage_limit": 1,
            "expires_at": expiry,
        },
    )
    assert create_resp.status_code == 200
    voucher_id = create_resp.json()["voucher_id"]

    update_resp = client.put(
        f"/rewards/vouchers/{voucher_id}",
        json={"description": "Updated desc"},
    )
    assert update_resp.status_code == 200

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})

    list_resp = client.get("/rewards/vouchers")
    assert list_resp.status_code == 200
    assert any(voucher["code"] == "SAVE10" for voucher in list_resp.json())

    redeem_resp = client.post(f"/rewards/vouchers/SAVE10/redeem", json={"order_id": voucher_order.id})
    assert redeem_resp.status_code == 200
    redeem_body = redeem_resp.json()
    assert redeem_body["discount_amount_paise"] == 800
    assert redeem_body["updated_order_total_paise"] == 7200

    duplicate_redeem = client.post(f"/rewards/vouchers/SAVE10/redeem", json={"order_id": voucher_order.id})
    assert duplicate_redeem.status_code == 400

    voucher_ledger = (
        test_db_session.query(Ledger)
        .filter(Ledger.order_id == voucher_order.id, Ledger.source == LedgerSource.VOUCHER)
        .first()
    )
    assert voucher_ledger is not None
    assert voucher_ledger.amount == 800

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})

    expired_create = client.post(
        "/rewards/vouchers",
        json={
            "code": "OLD",
            "description": "Expired",
            "discount_type": "fixed",
            "discount_value": 100,
            "min_order_amount_paise": 0,
            "expires_at": (utcnow_naive() - timedelta(days=1)).isoformat(),
        },
    )
    assert expired_create.status_code == 400

    delete_resp = client.delete(f"/rewards/vouchers/{voucher_id}")
    assert delete_resp.status_code == 200


def test_offpeak_bonus_policy_and_award_on_completion(client, seed_data, auth_context):
    admin = seed_data["admin"]
    vendor = seed_data["vendor"]
    student = seed_data["student"]
    completion_order = seed_data["completion_order"]

    auth_context.update({"id": admin.id, "phone": admin.phone, "role": admin.role.value})

    init_rules = client.post("/rewards/initialize-rules")
    assert init_rules.status_code == 200

    policy_resp = client.post(
        "/rewards/offpeak-policy",
        json={
            "enabled": True,
            "start_hour": 0,
            "end_hour": 24,
            "bonus_points_per_order": 15,
        },
    )
    assert policy_resp.status_code == 200
    assert policy_resp.json()["enabled"] is True

    audit_resp = client.get("/rewards/offpeak-policy/audit")
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()) >= 1

    auth_context.update({"id": vendor.id, "phone": vendor.phone, "role": vendor.role.value})
    complete_resp = client.post(f"/orders/{completion_order.id}/ready")
    assert complete_resp.status_code == 200

    auth_context.update({"id": student.id, "phone": student.phone, "role": student.role.value})
    points_resp = client.get("/rewards/points")
    assert points_resp.status_code == 200
    points = points_resp.json()

    assert points["current_points"] == 115.0
    reward_types = {row["reward_type"] for row in points["recent_transactions"]}
    assert "order_completion" in reward_types
    assert "off_peak_bonus" in reward_types
