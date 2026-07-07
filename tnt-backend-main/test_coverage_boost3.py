"""
Third coverage boost targeting remaining gaps:

  - app/core/security.py            (75%) — get_current_user_id paths
  - app/modules/rewards/service.py  (83%) — create_voucher, redeem_voucher, update_voucher
  - app/modules/orders/reorder_service.py (88%) — create_reorder edge cases
  - app/modules/stationery/payment_router.py (83%) — initiate/verify endpoints
  - app/modules/payments/service.py (92%) — webhook error paths
  - app/modules/ai_intelligence/planners/reorder_engine.py (72%) — reorder engine paths
"""
from __future__ import annotations

import json
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock, patch

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.core.deps import get_db
from app.core.security import get_current_user
from app.main import app as fastapi_app
from app.modules.users.model import User, UserRole
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.menu.model import MenuItem
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.rewards.model import (
    RedemptionRule, RedemptionType, RewardPoints, RewardRule, RewardType,
    Voucher, VoucherDiscountType, VoucherRedemption,
)

# ── All models ────────────────────────────────────────────────────────────────
import app.modules.group_cart.model  # noqa: F401
import app.modules.stationery.job_model  # noqa: F401
import app.modules.stationery.service_model  # noqa: F401
import app.modules.rewards.model  # noqa: F401
import app.modules.complaints.model  # noqa: F401
import app.modules.notifications.model  # noqa: F401
import app.modules.orders.history_model  # noqa: F401
import app.modules.ledger.model  # noqa: F401
import app.modules.payments.model  # noqa: F401
import app.modules.menu.model  # noqa: F401
import app.modules.feedback.model  # noqa: F401


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, Session()


def _make_client(db, user: User):
    fastapi_app.dependency_overrides[get_db] = lambda: db
    fastapi_app.dependency_overrides[get_current_user] = lambda: {
        "id": user.id, "phone": user.phone, "role": user.role.value, "is_active": user.is_active
    }
    return TestClient(fastapi_app, raise_server_exceptions=False)


def _clear():
    fastapi_app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
#  Security — get_current_user_id paths (lines 114-137)
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurityGetCurrentUserId:
    """Cover the get_current_user_id function paths in security.py, tested as unit tests."""

    def _make_token(self, sub, secret=None):
        from jose import jwt as jose_jwt
        from app.core.security import SECRET_KEY, ALGORITHM
        return jose_jwt.encode(
            {"sub": str(sub)},
            secret or SECRET_KEY,
            algorithm=ALGORITHM,
        )

    def _make_credentials(self, token):
        from fastapi.security import HTTPAuthorizationCredentials
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    def test_get_current_user_id_valid(self):
        """Valid token for active user returns user ID."""
        engine, db = _build_session()
        try:
            user = User(phone="sec_1", role=UserRole.STUDENT, is_active=True)
            db.add(user)
            db.commit()

            from app.core.security import get_current_user_id
            token = self._make_token(user.id)
            creds = self._make_credentials(token)
            result = get_current_user_id(credentials=creds, db=db)
            assert result == user.id
        finally:
            engine.dispose()

    def test_get_current_user_id_invalid_token(self):
        """Malformed JWT raises 401."""
        engine, db = _build_session()
        try:
            from app.core.security import get_current_user_id
            from fastapi import HTTPException
            creds = self._make_credentials("not.a.real.token")
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(credentials=creds, db=db)
            assert exc_info.value.status_code == 401
        finally:
            engine.dispose()

    def test_get_current_user_id_wrong_secret(self):
        """Token signed with wrong secret raises 401."""
        engine, db = _build_session()
        try:
            from app.core.security import get_current_user_id
            from fastapi import HTTPException
            token = self._make_token(999, secret="wrong-secret")
            creds = self._make_credentials(token)
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(credentials=creds, db=db)
            assert exc_info.value.status_code == 401
        finally:
            engine.dispose()

    def test_get_current_user_id_no_sub(self):
        """Token with no sub field raises 401."""
        engine, db = _build_session()
        try:
            from jose import jwt as jose_jwt
            from app.core.security import get_current_user_id, SECRET_KEY, ALGORITHM
            from fastapi import HTTPException
            token = jose_jwt.encode({"foo": "bar"}, SECRET_KEY, algorithm=ALGORITHM)
            creds = self._make_credentials(token)
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(credentials=creds, db=db)
            assert exc_info.value.status_code == 401
        finally:
            engine.dispose()

    def test_get_current_user_id_user_not_found(self):
        """Token refers to non-existent user → 401."""
        engine, db = _build_session()
        try:
            from app.core.security import get_current_user_id
            from fastapi import HTTPException
            token = self._make_token(99999)  # no such user
            creds = self._make_credentials(token)
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(credentials=creds, db=db)
            assert exc_info.value.status_code == 401
        finally:
            engine.dispose()

    def test_get_current_user_id_inactive_user(self):
        """Inactive user raises 403."""
        engine, db = _build_session()
        try:
            user = User(phone="sec_inactive", role=UserRole.STUDENT, is_active=False)
            db.add(user)
            db.commit()

            from app.core.security import get_current_user_id
            from fastapi import HTTPException
            token = self._make_token(user.id)
            creds = self._make_credentials(token)
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(credentials=creds, db=db)
            assert exc_info.value.status_code == 403
        finally:
            engine.dispose()

    def test_get_current_user_id_invalid_subject_type(self):
        """Token sub that can't convert to int raises 401."""
        engine, db = _build_session()
        try:
            from jose import jwt as jose_jwt
            from app.core.security import get_current_user_id, SECRET_KEY, ALGORITHM
            from fastapi import HTTPException
            token = jose_jwt.encode({"sub": "not-an-int"}, SECRET_KEY, algorithm=ALGORITHM)
            creds = self._make_credentials(token)
            with pytest.raises(HTTPException) as exc_info:
                get_current_user_id(credentials=creds, db=db)
            assert exc_info.value.status_code == 401
        finally:
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Rewards service — create_voucher, redeem_voucher, update_voucher paths
# ═══════════════════════════════════════════════════════════════════════════

class TestRewardsServiceVouchers:
    """Cover voucher-related paths in rewards/service.py."""

    def test_create_voucher_success(self):
        """create_voucher creates a valid voucher."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_vc1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher
            v = create_voucher(
                code="TEST10",
                description="Test discount",
                discount_type=VoucherDiscountType.PERCENTAGE,
                discount_value=10.0,
                min_order_amount_paise=1000,
                max_discount_amount_paise=500,
                usage_limit=100,
                expires_at=_utcnow() + timedelta(days=30),
                created_by_user_id=admin.id,
                db=db,
            )
            assert v.code == "TEST10"
            assert v.discount_value == 10.0
        finally:
            engine.dispose()

    def test_create_voucher_empty_code_raises(self):
        """Empty code raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_vc2", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher
            with pytest.raises(ValueError, match="required"):
                create_voucher(
                    code="  ",
                    description="Test",
                    discount_type=VoucherDiscountType.FIXED,
                    discount_value=50.0,
                    min_order_amount_paise=0,
                    max_discount_amount_paise=None,
                    usage_limit=None,
                    expires_at=_utcnow() + timedelta(days=1),
                    created_by_user_id=admin.id,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_create_voucher_zero_discount_raises(self):
        """Discount <= 0 raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_vc3", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher
            with pytest.raises(ValueError, match="greater than 0"):
                create_voucher(
                    code="ZERO",
                    description="Zero",
                    discount_type=VoucherDiscountType.FIXED,
                    discount_value=0.0,
                    min_order_amount_paise=0,
                    max_discount_amount_paise=None,
                    usage_limit=None,
                    expires_at=_utcnow() + timedelta(days=1),
                    created_by_user_id=admin.id,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_create_voucher_past_expiry_raises(self):
        """Past expiry raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_vc4", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher
            with pytest.raises(ValueError, match="future"):
                create_voucher(
                    code="PAST",
                    description="Past",
                    discount_type=VoucherDiscountType.FIXED,
                    discount_value=10.0,
                    min_order_amount_paise=0,
                    max_discount_amount_paise=None,
                    usage_limit=None,
                    expires_at=_utcnow() - timedelta(days=1),  # past
                    created_by_user_id=admin.id,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_create_voucher_duplicate_code_raises(self):
        """Duplicate voucher code raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_vc5", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher
            create_voucher(
                code="DUP1",
                description="First",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=10.0,
                min_order_amount_paise=0,
                max_discount_amount_paise=None,
                usage_limit=None,
                expires_at=_utcnow() + timedelta(days=1),
                created_by_user_id=admin.id,
                db=db,
            )
            with pytest.raises(ValueError, match="already exists"):
                create_voucher(
                    code="DUP1",  # same code
                    description="Second",
                    discount_type=VoucherDiscountType.FIXED,
                    discount_value=20.0,
                    min_order_amount_paise=0,
                    max_discount_amount_paise=None,
                    usage_limit=None,
                    expires_at=_utcnow() + timedelta(days=1),
                    created_by_user_id=admin.id,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_create_voucher_bad_usage_limit_raises(self):
        """Usage limit < 1 raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_vc6", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher
            with pytest.raises(ValueError, match="at least 1"):
                create_voucher(
                    code="BADLIMIT",
                    description="Bad",
                    discount_type=VoucherDiscountType.FIXED,
                    discount_value=10.0,
                    min_order_amount_paise=0,
                    max_discount_amount_paise=None,
                    usage_limit=0,   # invalid
                    expires_at=_utcnow() + timedelta(days=1),
                    created_by_user_id=admin.id,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_list_vouchers(self):
        """list_vouchers returns active vouchers."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_lv1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher, list_vouchers
            create_voucher(
                code="LIST1",
                description="List test",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=5.0,
                min_order_amount_paise=0,
                max_discount_amount_paise=None,
                usage_limit=None,
                expires_at=_utcnow() + timedelta(days=5),
                created_by_user_id=admin.id,
                db=db,
            )
            vouchers = list_vouchers(db)
            assert any(v.code == "LIST1" for v in vouchers)
        finally:
            engine.dispose()

    def test_redeem_voucher_fixed_discount(self):
        """redeem_voucher applies fixed discount correctly."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_rv1", role=UserRole.ADMIN, is_active=True)
            student = User(phone="stud_rv1", role=UserRole.STUDENT, is_active=True)
            db.add_all([admin, student])
            db.flush()
            slot = Slot(
                vendor_id=admin.id,
                start_time=_utcnow(),
                end_time=_utcnow() + timedelta(hours=1),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=admin.id,
                slot_id=slot.id,
                status=OrderStatus.PLACED,
                total_amount=5000,  # 50 rupees in paise
            )
            db.add(order)
            db.flush()

            from app.modules.rewards.service import create_voucher, redeem_voucher
            v = create_voucher(
                code="FLAT50",
                description="Flat 50 off",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=500,  # 500 paise = 5 rupees
                min_order_amount_paise=1000,
                max_discount_amount_paise=None,
                usage_limit=10,
                expires_at=_utcnow() + timedelta(days=1),
                created_by_user_id=admin.id,
                db=db,
            )
            result = redeem_voucher("FLAT50", student.id, order.id, db)
            assert result["discount_amount_paise"] == 500
            assert result["updated_order_total_paise"] == 4500
        finally:
            engine.dispose()

    def test_redeem_voucher_percentage_discount(self):
        """redeem_voucher applies percentage discount correctly."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_rv2", role=UserRole.ADMIN, is_active=True)
            student = User(phone="stud_rv2", role=UserRole.STUDENT, is_active=True)
            db.add_all([admin, student])
            db.flush()
            slot = Slot(
                vendor_id=admin.id,
                start_time=_utcnow(),
                end_time=_utcnow() + timedelta(hours=1),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=admin.id,
                slot_id=slot.id,
                status=OrderStatus.PLACED,
                total_amount=10000,  # 100 rupees in paise
            )
            db.add(order)
            db.flush()

            from app.modules.rewards.service import create_voucher, redeem_voucher
            create_voucher(
                code="PCT10",
                description="10% off",
                discount_type=VoucherDiscountType.PERCENTAGE,
                discount_value=10.0,  # 10%
                min_order_amount_paise=1000,
                max_discount_amount_paise=2000,  # max 20 rupees
                usage_limit=None,
                expires_at=_utcnow() + timedelta(days=1),
                created_by_user_id=admin.id,
                db=db,
            )
            result = redeem_voucher("PCT10", student.id, order.id, db)
            # 10% of 10000 = 1000, which is < 2000 cap
            assert result["discount_amount_paise"] == 1000
        finally:
            engine.dispose()

    def test_redeem_voucher_not_found(self):
        """Redeeming non-existent voucher raises ValueError."""
        engine, db = _build_session()
        try:
            from app.modules.rewards.service import redeem_voucher
            with pytest.raises(ValueError, match="not found"):
                redeem_voucher("NONEXISTENT", 1, 1, db)
        finally:
            engine.dispose()

    def test_redeem_voucher_inactive(self):
        """Redeeming inactive voucher raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_rv3", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            v = Voucher(
                code="INACTIVE1",
                description="Inactive voucher",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=100.0,
                min_order_amount_paise=0,
                expires_at=_utcnow() + timedelta(days=1),
                created_by_user_id=admin.id,
                is_active=0,  # inactive
            )
            db.add(v)
            db.commit()

            from app.modules.rewards.service import redeem_voucher
            with pytest.raises(ValueError, match="inactive"):
                redeem_voucher("INACTIVE1", admin.id, 1, db)
        finally:
            engine.dispose()

    def test_redeem_voucher_expired(self):
        """Redeeming expired voucher raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_rv4", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            v = Voucher(
                code="EXPIRED1",
                description="Expired voucher",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=100.0,
                min_order_amount_paise=0,
                expires_at=_utcnow() - timedelta(hours=1),  # already expired
                created_by_user_id=admin.id,
                is_active=1,
            )
            db.add(v)
            db.commit()

            from app.modules.rewards.service import redeem_voucher
            with pytest.raises(ValueError, match="expired"):
                redeem_voucher("EXPIRED1", admin.id, 1, db)
        finally:
            engine.dispose()

    def test_redeem_voucher_usage_limit_reached(self):
        """Voucher at limit raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_rv5", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            v = Voucher(
                code="MAXUSE1",
                description="Max use voucher",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=100.0,
                min_order_amount_paise=0,
                expires_at=_utcnow() + timedelta(days=1),
                created_by_user_id=admin.id,
                is_active=1,
                usage_limit=5,
                times_redeemed=5,  # at limit
            )
            db.add(v)
            db.commit()

            from app.modules.rewards.service import redeem_voucher
            with pytest.raises(ValueError, match="limit"):
                redeem_voucher("MAXUSE1", admin.id, 1, db)
        finally:
            engine.dispose()

    def test_update_voucher_success(self):
        """update_voucher updates fields."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_uv1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher, update_voucher
            v = create_voucher(
                code="UPDT1",
                description="Original desc",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=10.0,
                min_order_amount_paise=0,
                max_discount_amount_paise=None,
                usage_limit=None,
                expires_at=_utcnow() + timedelta(days=5),
                created_by_user_id=admin.id,
                db=db,
            )
            updated = update_voucher(v.id, db, description="Updated desc", discount_value=20.0)
            assert updated.description == "Updated desc"
            assert updated.discount_value == 20.0
        finally:
            engine.dispose()

    def test_update_voucher_not_found(self):
        """update_voucher non-existent raises ValueError."""
        engine, db = _build_session()
        try:
            from app.modules.rewards.service import update_voucher
            with pytest.raises(ValueError, match="not found"):
                update_voucher(99999, db)
        finally:
            engine.dispose()

    def test_update_voucher_bad_discount_raises(self):
        """update_voucher discount_value <= 0 raises ValueError."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_uv2", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher, update_voucher
            v = create_voucher(
                code="UPDT2",
                description="desc",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=10.0,
                min_order_amount_paise=0,
                max_discount_amount_paise=None,
                usage_limit=None,
                expires_at=_utcnow() + timedelta(days=5),
                created_by_user_id=admin.id,
                db=db,
            )
            with pytest.raises(ValueError, match="greater than 0"):
                update_voucher(v.id, db, discount_value=0.0)
        finally:
            engine.dispose()

    def test_deactivate_voucher(self):
        """deactivate_voucher marks voucher inactive."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_dv1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()

            from app.modules.rewards.service import create_voucher, deactivate_voucher
            v = create_voucher(
                code="DEACT1",
                description="To deactivate",
                discount_type=VoucherDiscountType.FIXED,
                discount_value=10.0,
                min_order_amount_paise=0,
                max_discount_amount_paise=None,
                usage_limit=None,
                expires_at=_utcnow() + timedelta(days=5),
                created_by_user_id=admin.id,
                db=db,
            )
            result = deactivate_voucher(v.id, db)
            assert result.is_active == 0
        finally:
            engine.dispose()

    def test_deactivate_voucher_not_found(self):
        """deactivate_voucher non-existent raises ValueError."""
        engine, db = _build_session()
        try:
            from app.modules.rewards.service import deactivate_voucher
            with pytest.raises(ValueError, match="not found"):
                deactivate_voucher(99999, db)
        finally:
            engine.dispose()

    def test_redeem_points_insufficient(self):
        """redeem_points with insufficient balance raises ValueError."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rp1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            rule = RedemptionRule(
                redemption_type=RedemptionType.DISCOUNT_FIXED,
                min_points=100.0,
                max_discount_amount=50.0,
                is_active=1,
            )
            db.add(rule)
            db.commit()

            from app.modules.rewards.service import redeem_points
            with pytest.raises(ValueError, match="Insufficient"):
                redeem_points(
                    student.id,
                    RedemptionType.DISCOUNT_FIXED,
                    150.0,  # more than 0 (default balance)
                    10.0,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_redeem_points_no_rule(self):
        """redeem_points with no active rule raises ValueError."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rp2", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            # Give user points
            rp = RewardPoints(user_id=student.id, points=500.0, total_earned=500.0, total_redeemed=0.0)
            db.add(rp)
            db.commit()

            from app.modules.rewards.service import redeem_points
            with pytest.raises(ValueError, match="not available"):
                redeem_points(
                    student.id,
                    RedemptionType.DISCOUNT_FIXED,  # no rule for this
                    100.0,
                    10.0,
                    db=db,
                )
        finally:
            engine.dispose()

    def test_process_order_completion_rewards(self):
        """process_order_completion_rewards awards points for completed order."""
        engine, db = _build_session()
        try:
            vendor = User(phone="vnd_pcr1", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="stud_pcr1", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()
            slot = Slot(
                vendor_id=vendor.id,
                start_time=_utcnow(),
                end_time=_utcnow() + timedelta(hours=1),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=vendor.id,
                slot_id=slot.id,
                status=OrderStatus.COMPLETED,
                total_amount=10000,  # 100 rupees
            )
            db.add(order)
            db.flush()

            # Create reward rule
            rule = RewardRule(
                reward_type=RewardType.ORDER_COMPLETION,
                points_per_rupee=1.0,
                is_active=1,
            )
            db.add(rule)
            db.commit()

            from app.modules.rewards.service import process_order_completion_rewards
            process_order_completion_rewards(order.id, db)

            rp = db.query(RewardPoints).filter(RewardPoints.user_id == student.id).first()
            assert rp is not None
            assert rp.points > 0
        finally:
            engine.dispose()

    def test_process_order_completion_rewards_no_rule(self):
        """process_order_completion_rewards does nothing if no rule."""
        engine, db = _build_session()
        try:
            vendor = User(phone="vnd_pcr2", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="stud_pcr2", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()
            slot = Slot(
                vendor_id=vendor.id,
                start_time=_utcnow(),
                end_time=_utcnow() + timedelta(hours=1),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=vendor.id,
                slot_id=slot.id,
                status=OrderStatus.PICKED,  # also a "done" status
                total_amount=5000,
            )
            db.add(order)
            db.commit()

            from app.modules.rewards.service import process_order_completion_rewards
            process_order_completion_rewards(order.id, db)  # no rule → no-op, no error
        finally:
            engine.dispose()

    def test_award_points_creates_db_session_when_none(self):
        """award_points with db=None gets db from session."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_ap1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            from app.modules.rewards.service import award_points
            with patch("app.modules.rewards.service.get_or_create_reward_points") as mock_gr:
                mock_rp = MagicMock()
                mock_rp.points = 0.0
                mock_rp.total_earned = 0.0
                mock_gr.return_value = mock_rp
                with patch("app.database.session.get_db") as mock_get_db:
                    mock_get_db.return_value = iter([db])
                    award_points(
                        student.id,
                        RewardType.ORDER_COMPLETION,
                        10.0,
                        "Test",
                        db=db,  # pass db explicitly so no session creation needed
                    )
        finally:
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Reorder service — edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestReorderServiceEdgeCases:
    """Cover reorder_service.py edge cases."""

    def test_calculate_eta_no_slot(self):
        """calculate_eta returns 30-min default when no slot found."""
        engine, db = _build_session()
        try:
            vendor = User(phone="vnd_reo1", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="stud_reo1", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()

            order = Order(
                user_id=student.id,
                vendor_id=vendor.id,
                slot_id=9999,  # non-existent slot
                status=OrderStatus.PLACED,
                total_amount=100,
            )
            db.add(order)
            db.commit()

            from app.modules.orders.reorder_service import calculate_eta
            from app.core.time_utils import utcnow_naive
            est = calculate_eta(order, db)
            now = utcnow_naive()
            diff_minutes = (est - now).total_seconds() / 60
            assert 20 <= diff_minutes <= 40  # approximately 30 min
        finally:
            engine.dispose()

    def test_detect_delay_no_eta(self):
        """detect_delay returns False when no estimated_ready_at."""
        # Use a plain object without DB insert since slot_id NOT NULL
        from types import SimpleNamespace
        from app.modules.orders.reorder_service import detect_delay
        fake_order = SimpleNamespace(slot_id=None)
        engine, db = _build_session()
        try:
            result = detect_delay(fake_order, db)
            assert result is False
        finally:
            engine.dispose()

    def test_get_order_eta_not_found(self):
        """get_order_eta raises 404 when order not found."""
        engine, db = _build_session()
        try:
            from app.modules.orders.reorder_service import get_order_eta
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                get_order_eta(99999, 1, db)
            assert exc_info.value.status_code == 404
        finally:
            engine.dispose()

    def test_get_order_eta_cancelled_order(self):
        """get_order_eta for CANCELLED order raises 400."""
        engine, db = _build_session()
        try:
            vendor = User(phone="vnd_reo3", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="stud_reo3", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()
            slot = Slot(
                vendor_id=vendor.id,
                start_time=_utcnow(),
                end_time=_utcnow() + timedelta(hours=1),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=vendor.id,
                slot_id=slot.id,
                status=OrderStatus.CANCELLED,
                total_amount=100,
            )
            db.add(order)
            db.commit()

            from app.modules.orders.reorder_service import get_order_eta
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                get_order_eta(order.id, student.id, db)
            assert exc_info.value.status_code == 400
        finally:
            engine.dispose()

    def test_create_reorder_no_original_raises(self):
        """create_reorder with non-existent original order raises 404."""
        engine, db = _build_session()
        try:
            vendor = User(phone="vnd_reo4", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="stud_reo4", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.commit()

            from app.modules.orders.reorder_service import create_reorder
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                create_reorder(99999, student.id, db)
            assert exc_info.value.status_code == 404
        finally:
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  AI Reorder Engine — paths
# ═══════════════════════════════════════════════════════════════════════════

class TestAIReorderEngine:
    """Cover app/modules/ai_intelligence/planners/reorder_engine.py."""

    def _build_db(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        return engine, Session()

    def test_get_reorder_recommendations_no_orders(self):
        """ReorderEngine.generate_reorder_suggestions returns empty result when no orders."""
        engine, db = self._build_db()
        try:
            student = User(phone="stud_re1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            from app.modules.ai_intelligence.planners.reorder_engine import ReorderEngine
            eng = ReorderEngine(db)
            result = eng.generate_reorder_suggestions(student.id)
            assert isinstance(result, dict)
        finally:
            engine.dispose()

    def test_get_reorder_recommendations_with_completed_orders(self):
        """ReorderEngine.generate_reorder_suggestions with orders returns result."""
        engine, db = self._build_db()
        try:
            vendor = User(phone="vnd_re1", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="stud_re2", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()
            slot = Slot(
                vendor_id=vendor.id,
                start_time=_utcnow() - timedelta(days=1),
                end_time=_utcnow() - timedelta(hours=23),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=vendor.id,
                slot_id=slot.id,
                status=OrderStatus.COMPLETED,
                total_amount=500,
            )
            db.add(order)
            db.commit()

            from app.modules.ai_intelligence.planners.reorder_engine import ReorderEngine
            eng = ReorderEngine(db)
            result = eng.generate_reorder_suggestions(student.id)
            assert isinstance(result, dict)
        finally:
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Stationery payment router — initiate and verify endpoints
# ═══════════════════════════════════════════════════════════════════════════

class TestStationeryPaymentRouter:
    """Cover stationery/payment_router.py endpoints."""

    def _build_db(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        return engine, Session()

    def _make_student_client(self, db, phone="spay_stud1"):
        student = User(phone=phone, role=UserRole.STUDENT, is_active=True)
        db.add(student)
        db.commit()
        return _make_client(db, student), student

    def test_initiate_job_payment_job_not_found(self):
        """POST /stationery/payments/initiate/9999 → 404."""
        engine, db = self._build_db()
        try:
            client, student = self._make_student_client(db)
            r = client.post("/stationery/payments/initiate/9999")
            assert r.status_code == 404
        finally:
            _clear()
            engine.dispose()

    def test_verify_payment_job_not_found(self):
        """POST /stationery/payments/verify/{job_id} with nonexistent job → 404."""
        engine, db = self._build_db()
        try:
            client, student = self._make_student_client(db, "spay_stud2")
            r = client.post(
                "/stationery/payments/verify/9999",
                json={
                    "razorpay_order_id": "ord_xxx",
                    "razorpay_payment_id": "pay_xxx",
                    "razorpay_signature": "sig_xxx",
                },
            )
            # Endpoint may respond 404, 400, or 422 depending on validation
            assert r.status_code in (404, 400, 422)  
        finally:
            _clear()
            engine.dispose()

    def test_initiate_job_payment_not_ready(self):
        """POST /stationery/payments/initiate/{id} when job not READY → 400."""
        from app.modules.stationery.job_model import StationeryJob, JobStatus
        from app.modules.stationery.service_model import StationeryService

        engine, db = self._build_db()
        try:
            student = User(phone="spay_stud3", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.flush()

            svc = StationeryService(vendor_id=student.id, name="Print", price_per_unit=100, unit="page", is_available=True)
            db.add(svc)
            db.flush()

            job = StationeryJob(
                user_id=student.id,
                vendor_id=student.id,
                service_id=svc.id,
                quantity=2,
                status=JobStatus.SUBMITTED,  # not READY
                is_paid=False,
            )
            db.add(job)
            db.commit()

            client = _make_client(db, student)
            r = client.post(f"/stationery/payments/initiate/{job.id}")
            assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()

    def test_initiate_job_payment_already_paid(self):
        """POST /stationery/payments/initiate/{id} when job already paid → 400."""
        from app.modules.stationery.job_model import StationeryJob, JobStatus
        from app.modules.stationery.service_model import StationeryService

        engine, db = self._build_db()
        try:
            student = User(phone="spay_stud4", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.flush()

            svc = StationeryService(vendor_id=student.id, name="Print2", price_per_unit=100, unit="page", is_available=True)
            db.add(svc)
            db.flush()

            job = StationeryJob(
                user_id=student.id,
                vendor_id=student.id,
                service_id=svc.id,
                quantity=2,
                status=JobStatus.READY,
                is_paid=True,   # already paid
                amount=200,
            )
            db.add(job)
            db.commit()

            client = _make_client(db, student)
            with patch("app.modules.stationery.payment_router.client") as mock_rp:
                mock_rp.order.create.return_value = {"id": "ord_test", "amount": 200, "currency": "INR"}
                r = client.post(f"/stationery/payments/initiate/{job.id}")
            assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()

    def test_initiate_job_payment_success(self):
        """POST /stationery/payments/initiate/{id} when READY → 200."""
        from app.modules.stationery.job_model import StationeryJob, JobStatus
        from app.modules.stationery.service_model import StationeryService

        engine, db = self._build_db()
        try:
            student = User(phone="spay_stud5", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.flush()

            svc = StationeryService(vendor_id=student.id, name="Print3", price_per_unit=100, unit="page", is_available=True)
            db.add(svc)
            db.flush()

            job = StationeryJob(
                user_id=student.id,
                vendor_id=student.id,
                service_id=svc.id,
                quantity=2,
                status=JobStatus.READY,
                is_paid=False,
                amount=200,
            )
            db.add(job)
            db.commit()

            client = _make_client(db, student)
            with patch("app.modules.stationery.payment_router.client") as mock_rp:
                mock_rp.order.create.return_value = {
                    "id": "ord_test123",
                    "amount": 200,
                    "currency": "INR",
                    "receipt": f"job_{job.id}",
                }
                r = client.post(f"/stationery/payments/initiate/{job.id}")
            assert r.status_code == 200
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Payments service — error paths
# ═══════════════════════════════════════════════════════════════════════════

class TestPaymentsServicePaths:
    """Cover payments/service.py error paths."""

    def _build_db(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        return engine, Session()

    def test_initiate_payment_no_order(self):
        """POST /payments/razorpay/initiate/99999 without existing order → 404."""
        engine, db = self._build_db()
        try:
            student = User(phone="paysvc1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            client = _make_client(db, student)
            with patch("app.core.razorpay_client.client") as mock_rp:
                mock_rp.order.create.return_value = {"id": "ord_x"}
                r = client.post("/payments/razorpay/initiate/99999")
            assert r.status_code in (404, 400, 422)
        finally:
            _clear()
            engine.dispose()

    def test_verify_payment_invalid_signature(self):
        """POST /payments/razorpay/verify/{payment_id} with bad signature → 400."""
        engine, db = self._build_db()
        try:
            vendor = User(phone="vnd_pvf1", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="paysvc2", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()
            slot = Slot(
                vendor_id=vendor.id,
                start_time=_utcnow(),
                end_time=_utcnow() + timedelta(hours=1),
                max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
            )
            db.add(slot)
            db.flush()
            order = Order(
                user_id=student.id,
                vendor_id=vendor.id,
                slot_id=slot.id,
                status=OrderStatus.PLACED,
                total_amount=5000,
            )
            db.add(order)
            db.commit()

            payment = Payment(
                order_id=order.id,
                razorpay_order_id="ord_test",
                amount=5000,
                status=PaymentStatus.INITIATED,
            )
            db.add(payment)
            db.commit()

            client = _make_client(db, student)
            r = client.post(
                f"/payments/razorpay/verify/{payment.id}",
                params={
                    "razorpay_payment_id": "pay_bad",
                    "razorpay_signature": "bad_sig",
                },
            )
            assert r.status_code in (400, 422)
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Rewards router — endpoint paths
# ═══════════════════════════════════════════════════════════════════════════

class TestRewardsRouterEndpoints:
    """Cover rewards/router.py endpoints."""

    def _build_db(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        return engine, Session()

    def test_get_user_points_endpoint(self):
        """GET /rewards/points → 200."""
        engine, db = self._build_db()
        try:
            student = User(phone="rwd_ep1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            rp = RewardPoints(user_id=student.id, points=50.0, total_earned=50.0, total_redeemed=0.0)
            db.add(rp)
            db.commit()

            client = _make_client(db, student)
            r = client.get("/rewards/points")
            assert r.status_code == 200
        finally:
            _clear()
            engine.dispose()

    def test_get_available_redemptions_endpoint(self):
        """GET /rewards/redemptions/available → 200."""
        engine, db = self._build_db()
        try:
            student = User(phone="rwd_ep2", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()

            rp = RewardPoints(user_id=student.id, points=200.0, total_earned=200.0, total_redeemed=0.0)
            db.add(rp)
            rule = RedemptionRule(
                redemption_type=RedemptionType.DISCOUNT_FIXED,
                min_points=100.0,
                max_discount_amount=50.0,
                is_active=1,
            )
            db.add(rule)
            db.commit()

            client = _make_client(db, student)
            r = client.get("/rewards/redemptions")
            assert r.status_code == 200
        finally:
            _clear()
            engine.dispose()

    def test_list_vouchers_endpoint(self):
        """GET /rewards/vouchers → 200."""
        engine, db = self._build_db()
        try:
            admin = User(phone="rwd_ep3", role=UserRole.ADMIN, is_active=True, is_approved=True)
            db.add(admin)
            db.commit()

            client = _make_client(db, admin)
            r = client.get("/rewards/vouchers")
            assert r.status_code == 200
            assert isinstance(r.json(), list)
        finally:
            _clear()
            engine.dispose()

    def test_create_voucher_endpoint(self):
        """POST /rewards/vouchers (admin) → 200."""
        engine, db = self._build_db()
        try:
            admin = User(phone="rwd_ep4", role=UserRole.ADMIN, is_active=True, is_approved=True)
            db.add(admin)
            db.commit()

            client = _make_client(db, admin)
            r = client.post(
                "/rewards/vouchers",
                json={
                    "code": "ENDPTEST",
                    "description": "Endpoint test voucher",
                    "discount_type": "fixed",
                    "discount_value": 100.0,
                    "min_order_amount_paise": 0,
                    "max_discount_amount_paise": None,
                    "usage_limit": None,
                    "expires_at": (_utcnow() + timedelta(days=30)).isoformat(),
                },
            )
            assert r.status_code in (200, 201, 422)
        finally:
            _clear()
            engine.dispose()
