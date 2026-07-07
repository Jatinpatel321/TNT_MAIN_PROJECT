"""
Coverage gap tests targeting modules with <90% coverage:

  - app/modules/admin/router.py       — toggle_user, shutdown, policy routes, announce
  - app/modules/auth/router.py        — send_otp, verify_otp (full flow)
  - app/modules/users/router.py       — register, me, update_profile, preferences, delete
  - app/modules/complaints/router.py  — list_complaints, assign, update_status
  - app/modules/rewards/router.py     — points, redeem, vouchers
  - app/modules/rewards/service.py    — redeem_points edge cases
  - app/modules/notifications/service.py — SMS failure fallback path
  - app/modules/orders/order_service.py  — _require_user/vendor/order 404 paths
"""
from __future__ import annotations

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
from app.modules.complaints.model import Complaint, ComplaintCategory, ComplaintStatus
from app.modules.rewards.model import (
    RedemptionRule, RedemptionType, RewardPoints, RewardTransaction, RewardType
)

# ── All models must be imported for Base.metadata.create_all ──────────────
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
#  Admin Router Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAdminToggleUser:
    def test_toggle_user_block(self):
        """POST /admin/users/{id}/toggle → toggles is_active."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_tgl_1", role=UserRole.ADMIN, is_active=True)
            target = User(phone="stud_tgl_1", role=UserRole.STUDENT, is_active=True)
            db.add_all([admin, target])
            db.commit()
            client = _make_client(db, admin)
            r = client.post(f"/admin/users/{target.id}/toggle")
            assert r.status_code == 200
            data = r.json()
            assert data["user_id"] == target.id
            assert data["is_active"] is False
        finally:
            _clear()
            engine.dispose()

    def test_toggle_user_unblock(self):
        """Second toggle re-enables the user."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_tgl_2", role=UserRole.ADMIN, is_active=True)
            target = User(phone="stud_tgl_2", role=UserRole.STUDENT, is_active=False)
            db.add_all([admin, target])
            db.commit()
            client = _make_client(db, admin)
            r = client.post(f"/admin/users/{target.id}/toggle")
            assert r.status_code == 200
            assert r.json()["is_active"] is True
        finally:
            _clear()
            engine.dispose()

    def test_toggle_user_not_found(self):
        """Toggle non-existent user → 404."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_tgl_3", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            client = _make_client(db, admin)
            r = client.post("/admin/users/99999/toggle")
            assert r.status_code == 404
        finally:
            _clear()
            engine.dispose()

    def test_toggle_requires_admin(self):
        """Non-admin → 403."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_tgl_4", role=UserRole.STUDENT, is_active=True)
            target = User(phone="stud_tgl_5", role=UserRole.STUDENT, is_active=True)
            db.add_all([student, target])
            db.commit()
            client = _make_client(db, student)
            r = client.post(f"/admin/users/{target.id}/toggle")
            assert r.status_code == 403
        finally:
            _clear()
            engine.dispose()


class TestAdminEmergencyShutdown:
    def test_enable_shutdown(self):
        """POST /admin/shutdown?enabled=true → emergency enabled."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_sd_1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.emergency.redis_client", fake):
                client = _make_client(db, admin)
                r = client.post("/admin/shutdown?enabled=true")
                assert r.status_code == 200
                assert r.json()["enabled"] is True
        finally:
            _clear()
            engine.dispose()

    def test_disable_shutdown(self):
        """POST /admin/shutdown?enabled=false → emergency disabled."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_sd_2", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.emergency.redis_client", fake):
                client = _make_client(db, admin)
                r = client.post("/admin/shutdown?enabled=false")
                assert r.status_code == 200
                assert r.json()["enabled"] is False
        finally:
            _clear()
            engine.dispose()


class TestAdminPolicies:
    def test_get_faculty_priority_policy(self):
        """GET /admin/policies/faculty-priority → 200."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_pol_1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.faculty_policy.redis_client", fake):
                client = _make_client(db, admin)
                r = client.get("/admin/policies/faculty-priority")
                assert r.status_code == 200
                data = r.json()
                assert "enabled" in data
        finally:
            _clear()
            engine.dispose()

    def test_set_faculty_priority_policy(self):
        """POST /admin/policies/faculty-priority → 200."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_pol_2", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.faculty_policy.redis_client", fake):
                client = _make_client(db, admin)
                r = client.post("/admin/policies/faculty-priority?enabled=true&start_hour=12&end_hour=14")
                assert r.status_code == 200
                data = r.json()
                assert data["enabled"] is True
        finally:
            _clear()
            engine.dispose()

    def test_set_faculty_priority_invalid_hours(self):
        """end_hour <= start_hour → 400."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_pol_3", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.faculty_policy.redis_client", fake):
                client = _make_client(db, admin)
                r = client.post("/admin/policies/faculty-priority?enabled=true&start_hour=14&end_hour=12")
                assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()

    def test_get_university_policy(self):
        """GET /admin/policies/university → 200."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_pol_4", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.university_policy.redis_client", fake):
                client = _make_client(db, admin)
                r = client.get("/admin/policies/university")
                assert r.status_code == 200
                data = r.json()
                assert "enabled" in data
        finally:
            _clear()
            engine.dispose()

    def test_set_university_policy(self):
        """POST /admin/policies/university → 200."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_pol_5", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.university_policy.redis_client", fake):
                client = _make_client(db, admin)
                r = client.post(
                    "/admin/policies/university?enabled=true&break_start_hour=12"
                    "&break_end_hour=14&max_orders_per_user=3&min_slot_duration_minutes=15"
                )
                assert r.status_code == 200
                data = r.json()
                assert "enabled" in data
        finally:
            _clear()
            engine.dispose()

    def test_set_university_policy_invalid_hours(self):
        """break_end <= break_start → 400."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_pol_6", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.core.university_policy.redis_client", fake):
                client = _make_client(db, admin)
                r = client.post(
                    "/admin/policies/university?enabled=true&break_start_hour=14"
                    "&break_end_hour=12&max_orders_per_user=3&min_slot_duration_minutes=15"
                )
                assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()


class TestAdminAnnouncement:
    def test_send_announcement(self):
        """POST /admin/announce sends to all users."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_ann_1", role=UserRole.ADMIN, is_active=True)
            student = User(phone="stud_ann_1", role=UserRole.STUDENT, is_active=True)
            db.add_all([admin, student])
            db.commit()
            with patch("app.modules.notifications.service.send_sms"):
                client = _make_client(db, admin)
                r = client.post("/admin/announce?message=Hello+everyone")
                assert r.status_code == 200
                assert "sent" in r.json().get("message", "").lower()
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Users Router Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUsersRouter:
    def test_register_new_user(self):
        """POST /users/register with valid phone → 200."""
        engine, db = _build_session()
        try:
            _clear()
            fastapi_app.dependency_overrides[get_db] = lambda: db
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.post("/users/register", json={
                "phone": "9990001234",
                "name": "Test User",
                "role": "student",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["phone"] == "9990001234"
        finally:
            _clear()
            engine.dispose()

    def test_register_duplicate_phone_400(self):
        """POST /users/register with existing phone → 400."""
        engine, db = _build_session()
        try:
            existing = User(phone="9990001235", role=UserRole.STUDENT, is_active=True)
            db.add(existing)
            db.commit()
            _clear()
            fastapi_app.dependency_overrides[get_db] = lambda: db
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.post("/users/register", json={
                "phone": "9990001235",
                "name": "Another",
                "role": "student",
            })
            assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()

    def test_get_me(self):
        """GET /users/me → 200 with user data."""
        engine, db = _build_session()
        try:
            student = User(phone="9990001236", role=UserRole.STUDENT, is_active=True, name="Me")
            db.add(student)
            db.commit()
            client = _make_client(db, student)
            r = client.get("/users/me")
            assert r.status_code == 200
            assert r.json()["phone"] == "9990001236"
        finally:
            _clear()
            engine.dispose()

    def test_update_profile(self):
        """PUT /users/me → updates name (vendor role, no university_id required)."""
        engine, db = _build_session()
        try:
            vendor = User(phone="9990001237", role=UserRole.VENDOR, is_active=True)
            db.add(vendor)
            db.commit()
            client = _make_client(db, vendor)
            r = client.put("/users/me?name=NewName")
            assert r.status_code == 200
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Auth Router Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAuthRouter:
    def test_send_otp_test_number(self):
        """POST /auth/send-otp with test number → 200."""
        engine, db = _build_session()
        try:
            _clear()
            fastapi_app.dependency_overrides[get_db] = lambda: db
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.modules.auth.otp_service.redis_client", fake), \
                 patch("app.core.rate_limit.redis_client", fake):
                client = TestClient(fastapi_app, raise_server_exceptions=False)
                r = client.post("/auth/send-otp", json={"phone": "9999999999"})
                assert r.status_code == 200
                assert r.json() == {"message": "OTP sent"}
        finally:
            _clear()
            engine.dispose()

    def test_verify_otp_invalid(self):
        """POST /auth/verify-otp with wrong OTP → 400."""
        engine, db = _build_session()
        try:
            _clear()
            fastapi_app.dependency_overrides[get_db] = lambda: db
            fake = fakeredis.FakeRedis(decode_responses=True)
            with patch("app.modules.auth.otp_service.redis_client", fake), \
                 patch("app.core.rate_limit.redis_client", fake), \
                 patch("app.core.observability.observability") as mock_obs:
                client = TestClient(fastapi_app, raise_server_exceptions=False)
                r = client.post("/auth/verify-otp", json={"phone": "9990009999", "otp": "000000"})
                assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()

    def test_verify_otp_creates_new_user(self):
        """POST /auth/verify-otp with valid OTP for new phone → auto-registers user."""
        engine, db = _build_session()
        try:
            _clear()
            fastapi_app.dependency_overrides[get_db] = lambda: db
            fake = fakeredis.FakeRedis(decode_responses=True)
            from app.modules.auth.otp_service import generate_otp
            with patch("app.modules.auth.otp_service.redis_client", fake), \
                 patch("app.core.sms.send_sms"), \
                 patch("app.core.rate_limit.redis_client", fake):
                # Generate OTP for phone
                otp = generate_otp("9990008888")
                client = TestClient(fastapi_app, raise_server_exceptions=False)
                r = client.post("/auth/verify-otp", json={"phone": "9990008888", "otp": otp})
                assert r.status_code == 200
                data = r.json()
                assert data["success"] is True
                assert "access_token" in data["data"]
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Complaints Router Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestComplaintsRouter:
    def _seed(self, db):
        admin = User(phone="adm_cmp_1", role=UserRole.ADMIN, is_active=True)
        student = User(phone="stud_cmp_1", role=UserRole.STUDENT, is_active=True)
        vendor = User(phone="vnd_cmp_1", role=UserRole.VENDOR, is_active=True, is_approved=True)
        db.add_all([admin, student, vendor])
        db.commit()
        slot = Slot(
            vendor_id=vendor.id,
            start_time=_utcnow(),
            end_time=_utcnow() + timedelta(hours=1),
            max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.flush()
        order = Order(
            user_id=student.id, vendor_id=vendor.id, slot_id=slot.id,
            status=OrderStatus.COMPLETED, total_amount=100,
        )
        db.add(order)
        db.commit()
        complaint = Complaint(
            user_id=student.id, vendor_id=vendor.id, order_id=order.id,
            category=ComplaintCategory.QUALITY_ISSUE, title="Cold food",
            status=ComplaintStatus.OPEN,
        )
        db.add(complaint)
        db.commit()
        return admin, student, vendor, order, complaint

    def test_list_complaints_as_admin(self):
        """GET /complaints/ (admin) → 200 with list."""
        engine, db = _build_session()
        try:
            admin, student, vendor, order, complaint = self._seed(db)
            client = _make_client(db, admin)
            r = client.get("/complaints/")
            assert r.status_code == 200
            assert isinstance(r.json(), list)
        finally:
            _clear()
            engine.dispose()

    def test_list_complaints_denied_for_student(self):
        """GET /complaints/ (student) → 403."""
        engine, db = _build_session()
        try:
            admin, student, vendor, order, complaint = self._seed(db)
            client = _make_client(db, student)
            r = client.get("/complaints/")
            assert r.status_code == 403
        finally:
            _clear()
            engine.dispose()

    def test_assign_complaint(self):
        """POST /complaints/{id}/assign → 200."""
        engine, db = _build_session()
        try:
            admin, student, vendor, order, complaint = self._seed(db)
            client = _make_client(db, admin)
            r = client.post(f"/complaints/{complaint.id}/assign?vendor_id={vendor.id}")
            assert r.status_code == 200
            assert r.json()["assigned_to_vendor_id"] == vendor.id
        finally:
            _clear()
            engine.dispose()

    def test_assign_complaint_not_found(self):
        """POST /complaints/9999/assign → 404."""
        engine, db = _build_session()
        try:
            admin, student, vendor, order, complaint = self._seed(db)
            client = _make_client(db, admin)
            r = client.post(f"/complaints/9999/assign?vendor_id={vendor.id}")
            assert r.status_code == 404
        finally:
            _clear()
            engine.dispose()

    def test_assign_complaint_invalid_vendor(self):
        """Assign to student (not vendor) → 404."""
        engine, db = _build_session()
        try:
            admin, student, vendor, order, complaint = self._seed(db)
            client = _make_client(db, admin)
            r = client.post(f"/complaints/{complaint.id}/assign?vendor_id={student.id}")
            assert r.status_code == 404
        finally:
            _clear()
            engine.dispose()

    def test_update_complaint_status(self):
        """POST /complaints/{id}/status → 200."""
        engine, db = _build_session()
        try:
            admin, student, vendor, order, complaint = self._seed(db)
            client = _make_client(db, admin)
            r = client.post(
                f"/complaints/{complaint.id}/status",
                json={"status": "resolved"}
            )
            assert r.status_code == 200
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Rewards Service Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestRewardsService:
    def test_get_user_points_creates_record(self):
        """get_user_points creates RewardPoints if not exists."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwp_1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            from app.modules.rewards.service import get_user_points
            result = get_user_points(student.id, db)
            assert result["current_points"] == 0
            assert "recent_transactions" in result
        finally:
            engine.dispose()

    def test_redeem_points_insufficient_points(self):
        """redeem_points with 0 points → ValueError."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwp_2", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            from app.modules.rewards.service import redeem_points
            with pytest.raises(ValueError, match="Insufficient points"):
                redeem_points(student.id, RedemptionType.DISCOUNT_FIXED, 100.0, 50.0, db=db)
        finally:
            engine.dispose()

    def test_redeem_points_no_active_rule(self):
        """redeem_points without active rule → ValueError."""
        engine, db = _build_session()
        try:
            # Give user points but no active redemption rule exists
            student = User(phone="stud_rwp_3", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.flush()
            rp = RewardPoints(user_id=student.id, points=500, total_earned=500)
            db.add(rp)
            db.commit()
            from app.modules.rewards.service import redeem_points
            with pytest.raises(ValueError, match="Redemption type not available"):
                redeem_points(student.id, RedemptionType.DISCOUNT_FIXED, 100.0, 50.0, db=db)
        finally:
            engine.dispose()

    def test_redeem_points_below_minimum(self):
        """Points below rule minimum → ValueError."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwp_4", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.flush()
            rp = RewardPoints(user_id=student.id, points=500, total_earned=500)
            db.add(rp)
            db.flush()
            rule = RedemptionRule(
                redemption_type=RedemptionType.DISCOUNT_FIXED,
                min_points=200,
                max_discount_amount=100,
                is_active=True,
            )
            db.add(rule)
            db.commit()
            from app.modules.rewards.service import redeem_points
            with pytest.raises(ValueError, match="Minimum"):
                redeem_points(student.id, RedemptionType.DISCOUNT_FIXED, 50.0, 25.0, db=db)
        finally:
            engine.dispose()

    def test_award_points(self):
        """award_points creates transaction + increases balance."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwp_5", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            from app.modules.rewards.service import award_points, get_user_points
            award_points(student.id, RewardType.ORDER_COMPLETION, 50.0, "Test award", db=db)
            result = get_user_points(student.id, db)
            assert result["current_points"] == 50.0
        finally:
            engine.dispose()


class TestRewardsRouter:
    def test_get_points_endpoint(self):
        """GET /rewards/points → 200."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwr_1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            client = _make_client(db, student)
            r = client.get("/rewards/points")
            assert r.status_code == 200
            data = r.json()
            assert "current_points" in data
        finally:
            _clear()
            engine.dispose()

    def test_get_redemptions_endpoint(self):
        """GET /rewards/redemptions → 200 with list."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwr_2", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            client = _make_client(db, student)
            r = client.get("/rewards/redemptions")
            assert r.status_code == 200
            assert isinstance(r.json(), list)
        finally:
            _clear()
            engine.dispose()

    def test_redeem_points_insufficient_returns_400(self):
        """POST /rewards/redeem with insufficient points → 400."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_rwr_3", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            client = _make_client(db, student)
            r = client.post("/rewards/redeem", json={
                "redemption_type": "discount_fixed",
                "points_used": 100.0,
                "value": 50.0,
            })
            assert r.status_code == 400
        finally:
            _clear()
            engine.dispose()

    def test_initialize_rules_admin(self):
        """POST /rewards/initialize-rules (admin) → 200."""
        engine, db = _build_session()
        try:
            admin = User(phone="adm_rwr_1", role=UserRole.ADMIN, is_active=True)
            db.add(admin)
            db.commit()
            client = _make_client(db, admin)
            r = client.post("/rewards/initialize-rules")
            assert r.status_code == 200
        finally:
            _clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Notification Service — SMS failure fallback
# ═══════════════════════════════════════════════════════════════════════════

class TestNotificationService:
    def test_notify_user_sms_failure_is_logged_not_raised(self):
        """SMS failure is logged but not raised to caller."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_ntf_1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            from app.modules.notifications.service import notify_user
            with patch("app.modules.notifications.service.send_sms", side_effect=Exception("SMS down")):
                # Should not raise
                result = notify_user(
                    user_id=student.id,
                    phone=student.phone,
                    title="Test",
                    message="Hello",
                    db=db,
                    send_sms_flag=True,
                )
            assert result is not None
        finally:
            engine.dispose()

    def test_notify_user_sms_disabled_skips_send(self):
        """notify_user with send_sms_flag=False skips SMS."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_ntf_2", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            from app.modules.notifications.service import notify_user
            with patch("app.modules.notifications.service.send_sms") as mock_sms:
                notify_user(
                    user_id=student.id,
                    phone=student.phone,
                    title="Test",
                    message="Hello",
                    db=db,
                    send_sms_flag=False,
                )
                mock_sms.assert_not_called()
        finally:
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  Order Service Helper 404 Paths
# ═══════════════════════════════════════════════════════════════════════════

class TestOrderServiceHelpers:
    def test_require_user_not_found(self):
        """_require_user raises 404 when phone not in DB."""
        engine, db = _build_session()
        try:
            from app.modules.orders.order_service import _require_user
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                _require_user({"phone": "nonexistent_phone", "id": 99}, db)
            assert exc_info.value.status_code == 404
        finally:
            engine.dispose()

    def test_require_vendor_not_found(self):
        """_require_vendor raises 404 when phone not in DB."""
        engine, db = _build_session()
        try:
            from app.modules.orders.order_service import _require_vendor
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                _require_vendor({"phone": "nonexistent_vendor", "id": 99}, db)
            assert exc_info.value.status_code == 404
        finally:
            engine.dispose()

    def test_require_own_order_not_found(self):
        """_require_own_order raises 404 when order doesn't exist."""
        engine, db = _build_session()
        try:
            student = User(phone="stud_oh_1", role=UserRole.STUDENT, is_active=True)
            db.add(student)
            db.commit()
            from app.modules.orders.order_service import _require_own_order
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                _require_own_order(99999, student, db)
            assert exc_info.value.status_code == 404
        finally:
            engine.dispose()

    def test_require_own_order_wrong_user(self):
        """_require_own_order raises 404 if order belongs to different user."""
        engine, db = _build_session()
        try:
            vendor = User(phone="vnd_oh_1", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student1 = User(phone="stud_oh_2", role=UserRole.STUDENT, is_active=True)
            student2 = User(phone="stud_oh_3", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student1, student2])
            db.flush()
            slot = Slot(vendor_id=vendor.id, start_time=_utcnow(), end_time=_utcnow() + timedelta(hours=1),
                        max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE)
            db.add(slot)
            db.flush()
            order = Order(user_id=student1.id, vendor_id=vendor.id, slot_id=slot.id,
                          status=OrderStatus.PLACED, total_amount=100)
            db.add(order)
            db.commit()
            from app.modules.orders.order_service import _require_own_order
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                _require_own_order(order.id, student2, db)
            assert exc_info.value.status_code == 404
        finally:
            engine.dispose()
