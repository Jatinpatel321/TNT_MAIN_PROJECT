"""
Tests for core utility modules:
  - app/core/security.py  (require_role, invalid tokens, blocked users)
  - app/core/startup_checks.py  (validate_production_settings all branches)
  - app/core/file_upload.py    (save_menu_image)
  - app/core/file_upload_stationery.py  (save_stationery_file)
  - app/core/logging_setup.py  (JsonFormatter, configure_logging)
  - app/core/emergency.py  (set/get shutdown with live Redis values)
  - app/core/faculty_policy.py  (get/set with Redis hit)
  - app/core/university_policy.py  (get/set with Redis hit)
  - app/core/db_transaction.py  (rollback path, async path)
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.core.deps import get_db
from app.core.security import (
    create_access_token,
    get_current_user,
    require_role,
    SECRET_KEY,
    ALGORITHM,
)
from app.main import app as fastapi_app
from app.modules.users.model import User, UserRole

# ── Import all models so tables are created ───────────────────────────────
import app.modules.group_cart.model  # noqa: F401
import app.modules.orders.model  # noqa: F401


def _utcnow():
    from datetime import datetime, UTC
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


# ═══════════════════════════════════════════════════════════════════════════
#  security.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRequireRole:
    def test_role_matches(self):
        """require_role passes when user has the required role."""
        checker = require_role("admin")
        user = {"id": 1, "phone": "9990001111", "role": "admin", "is_active": True}
        result = checker(user=user)
        assert result == user

    def test_role_mismatch_raises_403(self):
        """require_role raises 403 when user has wrong role."""
        checker = require_role("admin")
        user = {"id": 1, "phone": "9990001111", "role": "student", "is_active": True}
        with pytest.raises(HTTPException) as exc_info:
            checker(user=user)
        assert exc_info.value.status_code == 403

    def test_vendor_role_mismatch(self):
        checker = require_role("vendor")
        user = {"id": 2, "role": "student", "is_active": True}
        with pytest.raises(HTTPException) as exc_info:
            checker(user=user)
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail


class TestGetCurrentUserEdgeCases:
    def test_invalid_token_raises_401(self):
        """Malformed JWT → 401."""
        engine, db = _build_session()
        try:
            fastapi_app.dependency_overrides[get_db] = lambda: db
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.get(
                "/users/me",
                headers={"Authorization": "Bearer totally.invalid.token"},
            )
            assert r.status_code == 401
        finally:
            fastapi_app.dependency_overrides.clear()
            engine.dispose()

    def test_token_missing_sub_raises_401(self):
        """JWT without 'sub' claim → 401 invalid payload."""
        engine, db = _build_session()
        try:
            fastapi_app.dependency_overrides[get_db] = lambda: db
            # Token with role but no sub
            token = jwt.encode({"role": "student", "exp": 9999999999}, SECRET_KEY, algorithm=ALGORITHM)
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 401
        finally:
            fastapi_app.dependency_overrides.clear()
            engine.dispose()

    def test_token_non_integer_sub_raises_401(self):
        """JWT with non-integer 'sub' → 401 invalid subject."""
        engine, db = _build_session()
        try:
            fastapi_app.dependency_overrides[get_db] = lambda: db
            token = jwt.encode(
                {"sub": "not-a-number", "role": "student", "exp": 9999999999},
                SECRET_KEY, algorithm=ALGORITHM,
            )
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 401
        finally:
            fastapi_app.dependency_overrides.clear()
            engine.dispose()

    def test_user_not_found_raises_401(self):
        """Valid token pointing to non-existent user → 401."""
        engine, db = _build_session()
        try:
            fastapi_app.dependency_overrides[get_db] = lambda: db
            token = jwt.encode(
                {"sub": "99999", "role": "student", "exp": 9999999999},
                SECRET_KEY, algorithm=ALGORITHM,
            )
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 401
        finally:
            fastapi_app.dependency_overrides.clear()
            engine.dispose()

    def test_blocked_user_raises_403(self):
        """Valid token for inactive user → 403."""
        engine, db = _build_session()
        try:
            fastapi_app.dependency_overrides[get_db] = lambda: db
            blocked = User(phone="9990002222", role=UserRole.STUDENT, is_active=False)
            db.add(blocked)
            db.commit()
            db.refresh(blocked)
            token = jwt.encode(
                {"sub": str(blocked.id), "role": "student", "phone": blocked.phone, "exp": 9999999999},
                SECRET_KEY, algorithm=ALGORITHM,
            )
            client = TestClient(fastapi_app, raise_server_exceptions=False)
            r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 403
        finally:
            fastapi_app.dependency_overrides.clear()
            engine.dispose()


# ═══════════════════════════════════════════════════════════════════════════
#  startup_checks.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestValidateProductionSettings:
    def test_non_production_is_noop(self):
        from app.core.startup_checks import validate_production_settings
        # Should not raise for non-production environments
        validate_production_settings("development", [])
        validate_production_settings("staging", ["*"])
        validate_production_settings("test", [])

    def test_production_empty_cors_raises(self):
        from app.core.startup_checks import validate_production_settings
        with pytest.raises(RuntimeError, match="CORS_ORIGINS cannot be empty"):
            validate_production_settings("production", [])

    def test_production_wildcard_cors_raises(self):
        from app.core.startup_checks import validate_production_settings
        with pytest.raises(RuntimeError, match="Wildcard CORS"):
            validate_production_settings("production", ["*"])

    def test_production_localhost_cors_raises(self):
        from app.core.startup_checks import validate_production_settings
        with pytest.raises(RuntimeError, match="Localhost origins"):
            validate_production_settings("production", ["http://localhost:3000"])

    def test_production_localhost_ip_cors_raises(self):
        from app.core.startup_checks import validate_production_settings
        with pytest.raises(RuntimeError, match="Localhost origins"):
            validate_production_settings("production", ["http://127.0.0.1:8000"])

    def test_production_valid_cors_sms_disabled(self):
        """Valid CORS + SMS disabled → no error."""
        from app.core.startup_checks import validate_production_settings
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.SMS_ENABLED = False
            # Should not raise
            validate_production_settings("production", ["https://app.example.com"])

    def test_production_twilio_missing_credentials(self):
        """SMS_ENABLED + twilio provider with missing credentials → RuntimeError."""
        from app.core.startup_checks import validate_production_settings
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.SMS_ENABLED = True
            mock_settings.SMS_PROVIDER = "twilio"
            mock_settings.TWILIO_ACCOUNT_SID = ""
            mock_settings.TWILIO_AUTH_TOKEN = ""
            mock_settings.SMS_FROM = ""
            with pytest.raises(RuntimeError, match="Missing Twilio SMS settings"):
                validate_production_settings("production", ["https://app.example.com"])

    def test_production_twilio_complete_credentials(self):
        """SMS_ENABLED + twilio with all credentials → no error."""
        from app.core.startup_checks import validate_production_settings
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.SMS_ENABLED = True
            mock_settings.SMS_PROVIDER = "twilio"
            mock_settings.TWILIO_ACCOUNT_SID = "ACxxx"
            mock_settings.TWILIO_AUTH_TOKEN = "token123"
            mock_settings.SMS_FROM = "+10001112222"
            # Should not raise
            validate_production_settings("production", ["https://app.example.com"])

    def test_production_msg91_missing_credentials(self):
        """SMS_ENABLED + msg91 with missing credentials → RuntimeError."""
        from app.core.startup_checks import validate_production_settings
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.SMS_ENABLED = True
            mock_settings.SMS_PROVIDER = "msg91"
            mock_settings.MSG91_AUTH_KEY = ""
            mock_settings.MSG91_SENDER_ID = ""
            with pytest.raises(RuntimeError, match="Missing MSG91 SMS settings"):
                validate_production_settings("production", ["https://app.example.com"])

    def test_production_msg91_complete_credentials(self):
        """MSG91 with all credentials → no error."""
        from app.core.startup_checks import validate_production_settings
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.SMS_ENABLED = True
            mock_settings.SMS_PROVIDER = "msg91"
            mock_settings.MSG91_AUTH_KEY = "key123"
            mock_settings.MSG91_SENDER_ID = "TNTAPP"
            validate_production_settings("production", ["https://app.example.com"])

    def test_production_unsupported_provider_raises(self):
        """Unknown SMS provider → RuntimeError."""
        from app.core.startup_checks import validate_production_settings
        from unittest.mock import patch

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.SMS_ENABLED = True
            mock_settings.SMS_PROVIDER = "unknown_provider"
            with pytest.raises(RuntimeError, match="Unsupported SMS_PROVIDER"):
                validate_production_settings("production", ["https://app.example.com"])


class TestVerifyDatabaseRevision:
    def test_verify_database_revision_table_missing(self):
        """Missing alembic_version table → RuntimeError."""
        from app.core.startup_checks import verify_database_revision
        from unittest.mock import patch, MagicMock

        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = False

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("app.core.startup_checks.engine") as mock_engine, \
             patch("app.core.startup_checks.inspect", return_value=mock_inspector):
            mock_engine.connect.return_value = mock_conn
            with pytest.raises(RuntimeError, match="Database revision table missing"):
                verify_database_revision()

    def test_verify_database_revision_wrong_version(self):
        """Wrong revision → RuntimeError with upgrade hint."""
        from app.core.startup_checks import verify_database_revision
        from unittest.mock import patch, MagicMock

        mock_inspector = MagicMock()
        mock_inspector.has_table.return_value = True

        mock_result = MagicMock()
        mock_result.scalar.return_value = "old_revision_abc"

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value = mock_result

        mock_script = MagicMock()
        mock_script.get_current_head.return_value = "new_revision_xyz"

        with patch("app.core.startup_checks.engine") as mock_engine, \
             patch("app.core.startup_checks.inspect", return_value=mock_inspector), \
             patch("app.core.startup_checks.ScriptDirectory") as mock_sd:
            mock_engine.connect.return_value = mock_conn
            mock_sd.from_config.return_value = mock_script
            with pytest.raises(RuntimeError, match="not at head"):
                verify_database_revision()


# ═══════════════════════════════════════════════════════════════════════════
#  file_upload.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestMenuFileUpload:
    def test_invalid_content_type_raises_400(self):
        from app.core.file_upload import save_menu_image
        mock_file = MagicMock()
        mock_file.content_type = "text/plain"
        mock_file.filename = "test.txt"
        with pytest.raises(HTTPException) as exc_info:
            save_menu_image(mock_file)
        assert exc_info.value.status_code == 400
        assert "Invalid image format" in exc_info.value.detail

    def test_valid_jpeg_saves_and_returns_path(self, tmp_path):
        from app.core.file_upload import save_menu_image
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        mock_file.filename = "photo.jpg"
        mock_file.file.read.return_value = b"fake-image-data"

        with patch("app.core.file_upload.UPLOAD_DIR", str(tmp_path / "menu")):
            result = save_menu_image(mock_file)

        assert result.startswith("/uploads/menu/")
        assert result.endswith(".jpg")

    def test_valid_png_saves_and_returns_path(self, tmp_path):
        from app.core.file_upload import save_menu_image
        mock_file = MagicMock()
        mock_file.content_type = "image/png"
        mock_file.filename = "image.png"
        mock_file.file.read.return_value = b"fake-png-data"

        with patch("app.core.file_upload.UPLOAD_DIR", str(tmp_path / "menu")):
            result = save_menu_image(mock_file)

        assert result.startswith("/uploads/menu/")

    def test_valid_webp_saves_and_returns_path(self, tmp_path):
        from app.core.file_upload import save_menu_image
        mock_file = MagicMock()
        mock_file.content_type = "image/webp"
        mock_file.filename = "image.webp"
        mock_file.file.read.return_value = b"fake-webp-data"

        with patch("app.core.file_upload.UPLOAD_DIR", str(tmp_path / "menu")):
            result = save_menu_image(mock_file)

        assert result.startswith("/uploads/menu/")


# ═══════════════════════════════════════════════════════════════════════════
#  file_upload_stationery.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestStationeryFileUpload:
    def test_invalid_content_type_raises_400(self):
        from app.core.file_upload_stationery import save_stationery_file
        mock_file = MagicMock()
        mock_file.content_type = "image/jpeg"
        with pytest.raises(HTTPException) as exc_info:
            save_stationery_file(mock_file)
        assert exc_info.value.status_code == 400
        assert "Only PDF files allowed" in exc_info.value.detail

    def test_valid_pdf_saves_and_returns_path(self, tmp_path):
        from app.core.file_upload_stationery import save_stationery_file
        mock_file = MagicMock()
        mock_file.content_type = "application/pdf"
        mock_file.file.read.return_value = b"%PDF-1.4 fake"

        with patch("app.core.file_upload_stationery.UPLOAD_DIR", str(tmp_path / "stationery")):
            result = save_stationery_file(mock_file)

        assert result.startswith("/uploads/stationery/")
        assert result.endswith(".pdf")


# ═══════════════════════════════════════════════════════════════════════════
#  logging_setup.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestLoggingSetup:
    def test_json_formatter_basic(self):
        from app.core.logging_setup import JsonFormatter
        import json
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Hello World",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        payload = json.loads(output)
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test.logger"
        assert payload["message"] == "Hello World"
        assert "timestamp" in payload

    def test_json_formatter_with_request_id(self):
        from app.core.logging_setup import JsonFormatter
        import json
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Request warning",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-abc-123"
        output = formatter.format(record)
        payload = json.loads(output)
        assert payload["request_id"] == "req-abc-123"

    def test_configure_logging_json_mode(self):
        from app.core.logging_setup import configure_logging, JsonFormatter
        configure_logging(use_json=True)
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_configure_logging_plain_mode(self):
        from app.core.logging_setup import configure_logging, JsonFormatter
        configure_logging(use_json=False)
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert not isinstance(handler.formatter, JsonFormatter)


# ═══════════════════════════════════════════════════════════════════════════
#  emergency.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestEmergency:
    def test_set_and_get_shutdown_enabled(self):
        """set_emergency_shutdown(True) → is_emergency_shutdown_enabled() True."""
        fake = fakeredis.FakeRedis(decode_responses=True)
        with patch("app.core.emergency.redis_client", fake):
            from app.core.emergency import set_emergency_shutdown, is_emergency_shutdown_enabled
            set_emergency_shutdown(True)
            assert is_emergency_shutdown_enabled() is True

    def test_set_and_get_shutdown_disabled(self):
        fake = fakeredis.FakeRedis(decode_responses=True)
        with patch("app.core.emergency.redis_client", fake):
            from app.core.emergency import set_emergency_shutdown, is_emergency_shutdown_enabled
            set_emergency_shutdown(True)
            set_emergency_shutdown(False)
            assert is_emergency_shutdown_enabled() is False

    def test_is_enabled_value_truthy_strings(self):
        """Redis values like '1', 'true', 'yes', 'on' → True."""
        fake = fakeredis.FakeRedis(decode_responses=True)
        from app.core.emergency import EMERGENCY_SHUTDOWN_KEY
        for truthy in ["1", "true", "True", "yes", "on"]:
            fake.set(EMERGENCY_SHUTDOWN_KEY, truthy)
            with patch("app.core.emergency.redis_client", fake):
                from app.core.emergency import is_emergency_shutdown_enabled
                assert is_emergency_shutdown_enabled() is True

    def test_is_enabled_default_when_no_redis(self):
        """When Redis fails, fallback returns False (default state)."""
        import app.core.emergency as em_module
        em_module._fallback_shutdown_enabled = False
        bad_redis = MagicMock()
        bad_redis.get.side_effect = Exception("Redis unavailable")
        with patch("app.core.emergency.redis_client", bad_redis):
            from app.core.emergency import is_emergency_shutdown_enabled
            result = is_emergency_shutdown_enabled()
            assert result is False


# ═══════════════════════════════════════════════════════════════════════════
#  faculty_policy.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestFacultyPolicy:
    def test_set_and_get_policy(self):
        fake = fakeredis.FakeRedis(decode_responses=True)
        with patch("app.core.faculty_policy.redis_client", fake):
            from app.core.faculty_policy import set_faculty_priority_policy, get_faculty_priority_policy
            set_faculty_priority_policy(True, 11, 15)
            result = get_faculty_priority_policy()
            assert result["enabled"] is True
            assert result["start_hour"] == 11
            assert result["end_hour"] == 15

    def test_get_policy_fallback_when_no_redis(self):
        """Redis error → returns fallback policy."""
        bad_redis = MagicMock()
        bad_redis.get.side_effect = Exception("connection error")
        with patch("app.core.faculty_policy.redis_client", bad_redis):
            from app.core.faculty_policy import get_faculty_priority_policy
            result = get_faculty_priority_policy()
            assert "enabled" in result

    def test_is_slot_in_faculty_window_enabled(self):
        fake = fakeredis.FakeRedis(decode_responses=True)
        with patch("app.core.faculty_policy.redis_client", fake):
            from app.core.faculty_policy import set_faculty_priority_policy, is_slot_in_faculty_priority_window
            set_faculty_priority_policy(True, 12, 14)
            assert is_slot_in_faculty_priority_window(12) is True
            assert is_slot_in_faculty_priority_window(10) is False

    def test_is_slot_in_faculty_window_disabled(self):
        fake = fakeredis.FakeRedis(decode_responses=True)
        with patch("app.core.faculty_policy.redis_client", fake):
            from app.core.faculty_policy import set_faculty_priority_policy, is_slot_in_faculty_priority_window
            set_faculty_priority_policy(False, 12, 14)
            assert is_slot_in_faculty_priority_window(13) is False


# ═══════════════════════════════════════════════════════════════════════════
#  university_policy.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestUniversityPolicy:
    def test_set_and_get_policy(self):
        fake = fakeredis.FakeRedis(decode_responses=True)
        with patch("app.core.university_policy.redis_client", fake):
            from app.core.university_policy import set_university_policy, get_university_policy
            set_university_policy(
                enabled=True, break_start_hour=11, break_end_hour=13,
                max_orders_per_user=5, min_slot_duration_minutes=20,
            )
            result = get_university_policy()
            assert result["enabled"] is True
            assert result["break_start_hour"] == 11

    def test_get_policy_fallback_when_no_redis(self):
        bad_redis = MagicMock()
        bad_redis.get.side_effect = Exception("connection error")
        with patch("app.core.university_policy.redis_client", bad_redis):
            from app.core.university_policy import get_university_policy
            result = get_university_policy()
            assert "enabled" in result

    def test_is_hour_in_break_window(self):
        from app.core.university_policy import is_hour_in_break_window
        assert is_hour_in_break_window(12, 12, 14) is True
        assert is_hour_in_break_window(14, 12, 14) is False
        assert is_hour_in_break_window(10, 12, 14) is False


# ═══════════════════════════════════════════════════════════════════════════
#  db_transaction.py Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDbTransaction:
    def test_sync_function_commits_on_success(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        def my_func(db):
            return "done"

        result = my_func(db=mock_db)
        assert result == "done"
        mock_db.commit.assert_called_once()

    def test_sync_function_commits_and_reraises_on_http_exception(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        def my_func(db):
            raise HTTPException(status_code=400, detail="Bad request")

        with pytest.raises(HTTPException):
            my_func(db=mock_db)
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()

    def test_sync_function_rolls_back_on_unexpected_error(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        def my_func(db):
            raise ValueError("unexpected")

        with pytest.raises(ValueError):
            my_func(db=mock_db)
        mock_db.rollback.assert_called_once()

    def test_sync_function_no_db_doesnt_crash(self):
        from app.core.db_transaction import transactional

        @transactional
        def my_func(x: int):
            return x * 2

        # No db param → db is None, should still work
        result = my_func(5)
        assert result == 10

    def test_sync_wrapper_db_as_positional_arg(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        def my_func(db):
            return "positional"

        result = my_func(mock_db)  # passed positionally
        assert result == "positional"
        mock_db.commit.assert_called_once()

    def test_async_function_commits_on_success(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        async def my_async_func(db):
            return "async_done"

        result = asyncio.run(my_async_func(db=mock_db))
        assert result == "async_done"
        mock_db.commit.assert_called_once()

    def test_async_function_rolls_back_on_unexpected_error(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        async def my_async_func(db):
            raise RuntimeError("async crash")

        with pytest.raises(RuntimeError):
            asyncio.run(my_async_func(db=mock_db))
        mock_db.rollback.assert_called_once()

    def test_async_function_commits_on_http_exception(self):
        from app.core.db_transaction import transactional
        mock_db = MagicMock()

        @transactional
        async def my_async_func(db):
            raise HTTPException(status_code=422, detail="Validation failed")

        with pytest.raises(HTTPException):
            asyncio.run(my_async_func(db=mock_db))
        mock_db.commit.assert_called_once()

    def test_safe_rollback_logs_error_on_failure(self):
        from app.core.db_transaction import _safe_rollback
        mock_db = MagicMock()
        mock_db.rollback.side_effect = Exception("rollback failed")
        # Should not raise, just log
        _safe_rollback(mock_db)



