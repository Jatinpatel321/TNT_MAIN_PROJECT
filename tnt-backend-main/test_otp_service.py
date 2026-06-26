"""
Comprehensive unit tests for app/modules/auth/otp_service.py

Tests cover:
  generate_otp  — normal flow, test phone, rate limiting, SMS errors
  verify_otp    — success, expired, wrong OTP, max attempts exceeded
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import fakeredis
import pytest
from fastapi import HTTPException


# ─────────────────────────────────────────────────────────────── helpers ──

def _fake_redis():
    """Return a fresh fakeredis instance."""
    return fakeredis.FakeRedis(decode_responses=True)


# ═══════════════════════════════════════════════════════════════════════════
#  generate_otp tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGenerateOTP:
    def test_test_phone_returns_fixed_otp(self):
        """Phone ending 1111 always returns '123456' without SMS."""
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms") as mock_sms:
            from app.modules.auth.otp_service import generate_otp
            otp = generate_otp("9991111111")
            assert otp == "123456"
            mock_sms.assert_not_called()

    def test_test_phone_stores_in_redis(self):
        """OTP is stored in Redis for test phones."""
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms"):
            from app.modules.auth.otp_service import generate_otp
            generate_otp("9991111")
            assert fake.get("otp:9991111") == "123456"

    def test_normal_phone_generates_random_otp(self):
        """Normal phone gets a 6-digit OTP via SMS."""
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms") as mock_sms:
            from app.modules.auth.otp_service import generate_otp
            otp = generate_otp("9998887777")
            assert len(otp) == 6
            assert otp.isdigit()
            mock_sms.assert_called_once()

    def test_rate_limit_blocks_after_three(self):
        """Calling generate_otp more than SEND_LIMIT=3 times raises HTTP 429."""
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms"):
            from app.modules.auth.otp_service import generate_otp
            phone = "9990001234"
            for _ in range(3):
                generate_otp(phone)
            with pytest.raises(HTTPException) as exc_info:
                generate_otp(phone)
            assert exc_info.value.status_code == 429

    def test_rate_limit_increments_counter(self):
        """Each generate_otp increments the send counter in Redis."""
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms"):
            from app.modules.auth.otp_service import generate_otp
            phone = "9995556666"
            generate_otp(phone)
            generate_otp(phone)
            count = int(fake.get(f"otp:send_count:{phone}"))
            assert count == 2

    def test_sms_config_error_raises_503(self):
        """SMSConfigError → HTTP 503."""
        from app.core.sms import SMSConfigError
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms", side_effect=SMSConfigError("no config")):
            from app.modules.auth.otp_service import generate_otp
            with pytest.raises(HTTPException) as exc_info:
                generate_otp("9998880001")
            assert exc_info.value.status_code == 503
            assert "misconfigured" in exc_info.value.detail

    def test_sms_delivery_error_raises_503(self):
        """SMSDeliveryError → HTTP 503."""
        from app.core.sms import SMSDeliveryError
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms", side_effect=SMSDeliveryError("delivery failed")):
            from app.modules.auth.otp_service import generate_otp
            with pytest.raises(HTTPException) as exc_info:
                generate_otp("9998880002")
            assert exc_info.value.status_code == 503
            assert "could not be delivered" in exc_info.value.detail

    def test_otp_has_ttl(self):
        """OTP key should have a TTL set in Redis."""
        fake = _fake_redis()
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms"):
            from app.modules.auth.otp_service import generate_otp
            generate_otp("9991111111")  # test phone
            ttl = fake.ttl("otp:9991111111")
            assert ttl > 0


# ═══════════════════════════════════════════════════════════════════════════
#  verify_otp tests
# ═══════════════════════════════════════════════════════════════════════════

class TestVerifyOTP:
    def test_verify_correct_otp(self):
        """Correct OTP → returns True, clears Redis keys."""
        fake = _fake_redis()
        phone = "9990009999"
        fake.setex(f"otp:{phone}", 300, "654321")
        with patch("app.modules.auth.otp_service.redis_client", fake):
            from app.modules.auth.otp_service import verify_otp
            result = verify_otp(phone, "654321")
        assert result is True
        assert fake.get(f"otp:{phone}") is None
        assert fake.get(f"otp:attempts:{phone}") is None

    def test_verify_expired_otp_raises_400(self):
        """No OTP in Redis → HTTP 400 OTP expired."""
        fake = _fake_redis()
        phone = "9990008888"
        # Do NOT set any OTP key → simulates expiry
        with patch("app.modules.auth.otp_service.redis_client", fake):
            from app.modules.auth.otp_service import verify_otp
            with pytest.raises(HTTPException) as exc_info:
                verify_otp(phone, "123456")
        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail

    def test_verify_wrong_otp_increments_attempts(self):
        """Wrong OTP raises 400 and increments attempts counter."""
        fake = _fake_redis()
        phone = "9990007777"
        fake.setex(f"otp:{phone}", 300, "111111")
        with patch("app.modules.auth.otp_service.redis_client", fake):
            from app.modules.auth.otp_service import verify_otp
            with pytest.raises(HTTPException) as exc_info:
                verify_otp(phone, "999999")
        assert exc_info.value.status_code == 400
        assert "Invalid OTP" in exc_info.value.detail
        attempts = int(fake.get(f"otp:attempts:{phone}"))
        assert attempts == 1

    def test_verify_max_attempts_exceeded_raises_429(self):
        """After MAX_ATTEMPTS=5 wrong tries → HTTP 429."""
        fake = _fake_redis()
        phone = "9990006666"
        fake.setex(f"otp:{phone}", 300, "111111")
        fake.set(f"otp:attempts:{phone}", "5")  # Already at limit
        with patch("app.modules.auth.otp_service.redis_client", fake):
            from app.modules.auth.otp_service import verify_otp
            with pytest.raises(HTTPException) as exc_info:
                verify_otp(phone, "999999")
        assert exc_info.value.status_code == 429
        assert "Too many" in exc_info.value.detail

    def test_verify_max_attempts_deletes_otp(self):
        """After too many attempts, the OTP key is deleted."""
        fake = _fake_redis()
        phone = "9990005555"
        fake.setex(f"otp:{phone}", 300, "111111")
        fake.set(f"otp:attempts:{phone}", "5")
        with patch("app.modules.auth.otp_service.redis_client", fake):
            from app.modules.auth.otp_service import verify_otp
            with pytest.raises(HTTPException):
                verify_otp(phone, "999999")
        assert fake.get(f"otp:{phone}") is None

    def test_full_flow_generate_then_verify(self):
        """Full round-trip: generate OTP, then verify it successfully."""
        fake = _fake_redis()
        phone = "9991111111"  # test phone
        with patch("app.modules.auth.otp_service.redis_client", fake), \
             patch("app.modules.auth.otp_service.send_sms"):
            from app.modules.auth.otp_service import generate_otp, verify_otp
            otp = generate_otp(phone)
            assert otp == "123456"
            result = verify_otp(phone, otp)
            assert result is True
