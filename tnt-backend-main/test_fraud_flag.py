"""
Fraud Flag Schema Enforcement QA — test_fraud_flag.py

Acceptance criteria (PROMPT 10):
  • fraud_flag is a first-class column on Order (no hasattr needed).
  • fraud_flag defaults to False for every new order.
  • POST /admin/orders/{id}/fraud persists fraud_flag=True and sets flagged_at.
  • Flagging an already-flagged order returns 400.
  • Non-admin requests are rejected with 403.
  • Non-existent order returns 404.
  • The codebase contains no hasattr(order, 'fraud_flag') guard (regression).
"""

from __future__ import annotations

import ast
import pathlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import get_current_user
from app.database.base import Base
from app.main import app
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
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
def seed(db_session):
    admin = User(
        phone="9300000001", name="Admin", role=UserRole.ADMIN, is_active=True
    )
    student = User(
        phone="9300000002", name="Student", role=UserRole.STUDENT, is_active=True
    )
    vendor = User(
        phone="9300000003",
        name="Vendor",
        role=UserRole.VENDOR,
        is_active=True,
        is_approved=True,
    )
    db_session.add_all([admin, student, vendor])
    db_session.commit()
    for u in (admin, student, vendor):
        db_session.refresh(u)

    slot = Slot(
        vendor_id=vendor.id,
        start_time=utcnow_naive() + timedelta(hours=1),
        end_time=utcnow_naive() + timedelta(hours=2),
        max_orders=10,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)

    order = Order(
        user_id=student.id,
        slot_id=slot.id,
        vendor_id=vendor.id,
        status=OrderStatus.PENDING,
        total_amount=5000,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)

    return {"admin": admin, "student": student, "vendor": vendor, "order": order}


def _make_client(db_session, user: User) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id,
        "phone": user.phone,
        "role": user.role.value,
    }
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Model-level: fraud_flag is a proper ORM column
# ---------------------------------------------------------------------------


class TestOrderModelFraudColumn:
    def test_fraud_flag_column_in_model(self):
        """Order must have fraud_flag as a mapped column attribute."""
        cols = {c.key for c in Order.__mapper__.columns}
        assert "fraud_flag" in cols, "fraud_flag column missing from Order model"

    def test_flagged_at_column_in_model(self):
        cols = {c.key for c in Order.__mapper__.columns}
        assert "flagged_at" in cols, "flagged_at column missing from Order model"

    def test_fraud_flag_column_in_db_schema(self, db_session):
        """After create_all the column must exist in the SQLite schema."""
        inspector = inspect(db_session.bind)
        col_names = {c["name"] for c in inspector.get_columns("orders")}
        assert "fraud_flag" in col_names
        assert "flagged_at" in col_names

    def test_fraud_flag_defaults_to_false(self, db_session, seed):
        """New orders must default to fraud_flag=False without explicit assignment."""
        order = seed["order"]
        assert order.fraud_flag is False

    def test_no_hasattr_needed(self, seed):
        """Verify fraud_flag is accessible directly without hasattr guard."""
        order = seed["order"]
        # This must not raise AttributeError — hasattr guard no longer needed.
        _ = order.fraud_flag
        _ = order.flagged_at

    def test_fraud_flag_type_is_bool(self, db_session, seed):
        order = seed["order"]
        assert isinstance(order.fraud_flag, bool)


# ---------------------------------------------------------------------------
# 2. Route: POST /admin/orders/{id}/fraud
# ---------------------------------------------------------------------------


class TestFraudFlagRoute:
    def test_admin_can_flag_order(self, db_session, seed):
        client = _make_client(db_session, seed["admin"])
        resp = client.post(f"/admin/orders/{seed['order'].id}/fraud")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["message"] == "Order marked as fraud"
        assert body["order_id"] == seed["order"].id
        assert "flagged_at" in body

    def test_fraud_flag_persisted_in_db(self, db_session, seed):
        client = _make_client(db_session, seed["admin"])
        client.post(f"/admin/orders/{seed['order'].id}/fraud")

        db_session.expire_all()
        order = db_session.query(Order).filter(Order.id == seed["order"].id).first()
        assert order.fraud_flag is True

    def test_flagged_at_set_on_flag(self, db_session, seed):
        client = _make_client(db_session, seed["admin"])
        client.post(f"/admin/orders/{seed['order'].id}/fraud")

        db_session.expire_all()
        order = db_session.query(Order).filter(Order.id == seed["order"].id).first()
        assert order.flagged_at is not None

    def test_double_flag_returns_400(self, db_session, seed):
        client = _make_client(db_session, seed["admin"])
        client.post(f"/admin/orders/{seed['order'].id}/fraud")   # first — OK
        resp = client.post(f"/admin/orders/{seed['order'].id}/fraud")  # second

        assert resp.status_code == 400
        assert "already flagged" in resp.json()["detail"]

    def test_non_existent_order_returns_404(self, db_session, seed):
        client = _make_client(db_session, seed["admin"])
        resp = client.post("/admin/orders/99999/fraud")
        assert resp.status_code == 404

    def test_student_cannot_flag_order(self, db_session, seed):
        client = _make_client(db_session, seed["student"])
        resp = client.post(f"/admin/orders/{seed['order'].id}/fraud")
        assert resp.status_code == 403

    def test_vendor_cannot_flag_order(self, db_session, seed):
        client = _make_client(db_session, seed["vendor"])
        resp = client.post(f"/admin/orders/{seed['order'].id}/fraud")
        assert resp.status_code == 403

    def test_unflagged_order_remains_unflagged_after_failed_attempt(
        self, db_session, seed
    ):
        """A 403 or 404 must not mutate the order's fraud state."""
        client = _make_client(db_session, seed["student"])
        client.post(f"/admin/orders/{seed['order'].id}/fraud")  # 403

        db_session.expire_all()
        order = db_session.query(Order).filter(Order.id == seed["order"].id).first()
        assert order.fraud_flag is False
        assert order.flagged_at is None

    def test_v1_route_also_flags_correctly(self, db_session, seed):
        """The /v1/admin/... route must also work after API versioning."""
        client = _make_client(db_session, seed["admin"])
        resp = client.post(f"/v1/admin/orders/{seed['order'].id}/fraud")
        assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# 3. Regression: no hasattr(order, 'fraud_flag') anywhere in the codebase
# ---------------------------------------------------------------------------


class TestNoHasattrGuard:
    """Parse every Python file under app/ and assert the fragile guard is gone."""

    _APP_ROOT = pathlib.Path(__file__).parent / "app"

    def _collect_hasattr_fraud_usages(self) -> list[str]:
        offenders: list[str] = []
        for py_file in self._APP_ROOT.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (isinstance(func, ast.Name) and func.id == "hasattr"):
                    continue
                # hasattr(<something>, 'fraud_flag')
                if len(node.args) >= 2:
                    arg = node.args[1]
                    if isinstance(arg, ast.Constant) and "fraud" in str(arg.value):
                        rel = py_file.relative_to(self._APP_ROOT.parent)
                        offenders.append(f"{rel}:{node.col_offset}")
        return offenders

    def test_no_hasattr_fraud_flag_in_codebase(self):
        offenders = self._collect_hasattr_fraud_usages()
        assert not offenders, (
            f"hasattr(order, 'fraud_flag') guard still present in:\n"
            + "\n".join(offenders)
        )
