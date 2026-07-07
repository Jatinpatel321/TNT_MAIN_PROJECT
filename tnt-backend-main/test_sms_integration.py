import pytest

from app.core.config import settings
from app.core.sms import SMSConfigError, SMSDeliveryError, SMSNetworkError, SMSProviderDownError, SMSRateLimitError, send_sms
from app.core.startup_checks import validate_production_settings


class _FakeResponse:
    """Minimal httpx.Response mock simulating a successful 200 OK."""
    status_code = 200

    def raise_for_status(self):
        return None


def test_send_sms_disabled_skips_provider_call(monkeypatch):
    monkeypatch.setattr(settings, "SMS_ENABLED", False)

    def _should_not_call(*args, **kwargs):
        raise AssertionError("Provider should not be called when SMS is disabled")

    monkeypatch.setattr("app.core.sms.httpx.post", _should_not_call)

    send_sms("+911234567890", "hello")


def test_send_sms_twilio_calls_provider(monkeypatch):
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setattr(settings, "SMS_FROM", "+911111111111")

    captured = {}

    def _fake_post(url, data=None, auth=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        captured["auth"] = auth
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr("app.core.sms.httpx.post", _fake_post)

    send_sms("+919999999999", "TNT test message")

    assert "api.twilio.com" in captured["url"]
    assert captured["data"]["To"] == "+919999999999"
    assert captured["data"]["Body"] == "TNT test message"


def test_send_sms_twilio_missing_config_raises(monkeypatch):
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", None)
    monkeypatch.setattr(settings, "SMS_FROM", None)

    with pytest.raises(SMSConfigError):
        send_sms("+919999999999", "TNT test message")


def test_validate_production_settings_rejects_missing_sms_config(monkeypatch):
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", None)
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setattr(settings, "SMS_FROM", "+911111111111")

    with pytest.raises(RuntimeError):
        validate_production_settings("production", ["https://app.example.com"])


# ---------------------------------------------------------------------------
# Fallback + structured exception tests
# ---------------------------------------------------------------------------

class _ErrorResponse:
    """Simulates an HTTP error response with a given status code."""
    def __init__(self, status_code: int):
        self.status_code = status_code

    def raise_for_status(self):
        import httpx
        raise httpx.HTTPStatusError(
            f"HTTP {self.status_code}",
            request=None,  # type: ignore[arg-type]
            response=None,  # type: ignore[arg-type]
        )


def test_send_sms_rate_limit_raises_SMSRateLimitError(monkeypatch):
    """A 429 from twilio surfaces as SMSRateLimitError (before fallback kicks in)."""
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setattr(settings, "SMS_FROM", "+911111111111")
    # Also block the fallback (msg91) so we get the final error
    monkeypatch.setattr(settings, "MSG91_AUTH_KEY", None)
    monkeypatch.setattr(settings, "MSG91_SENDER_ID", None)

    monkeypatch.setattr("app.core.sms.httpx.post", lambda *a, **kw: _ErrorResponse(429))

    with pytest.raises(SMSDeliveryError):
        send_sms("+919999999999", "test")


def test_send_sms_provider_down_triggers_fallback_then_fails(monkeypatch):
    """5xx on primary + missing fallback config → SMSDeliveryError."""
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setattr(settings, "SMS_FROM", "+911111111111")
    monkeypatch.setattr(settings, "MSG91_AUTH_KEY", None)
    monkeypatch.setattr(settings, "MSG91_SENDER_ID", None)

    monkeypatch.setattr("app.core.sms.httpx.post", lambda *a, **kw: _ErrorResponse(503))

    with pytest.raises(SMSDeliveryError):
        send_sms("+919999999999", "test")


def test_send_sms_fallback_succeeds_when_primary_fails(monkeypatch):
    """Primary (twilio) returns 503 → fallback (msg91) succeeds."""
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "twilio")
    monkeypatch.setattr(settings, "TWILIO_ACCOUNT_SID", "AC_test")
    monkeypatch.setattr(settings, "TWILIO_AUTH_TOKEN", "auth_test")
    monkeypatch.setattr(settings, "SMS_FROM", "+911111111111")
    monkeypatch.setattr(settings, "MSG91_AUTH_KEY", "key91")
    monkeypatch.setattr(settings, "MSG91_SENDER_ID", "TNTAPP")

    call_count = {"n": 0}

    def _fake_post(url, *args, **kwargs):
        call_count["n"] += 1
        if "twilio.com" in url:
            return _ErrorResponse(503)  # primary fails
        return _FakeResponse()  # fallback succeeds

    monkeypatch.setattr("app.core.sms.httpx.post", _fake_post)

    # Should succeed without raising
    send_sms("+919999999999", "test")
    assert call_count["n"] == 2, "Expected two HTTP calls: primary + fallback"


def test_send_sms_msg91_provider_direct(monkeypatch):
    """Primary provider set to msg91 calls the correct endpoint."""
    monkeypatch.setattr(settings, "SMS_ENABLED", True)
    monkeypatch.setattr(settings, "SMS_PROVIDER", "msg91")
    monkeypatch.setattr(settings, "MSG91_AUTH_KEY", "key91")
    monkeypatch.setattr(settings, "MSG91_SENDER_ID", "TNTAPP")

    captured = {}

    def _fake_post(url, *args, **kwargs):
        captured["url"] = url
        return _FakeResponse()

    monkeypatch.setattr("app.core.sms.httpx.post", _fake_post)

    send_sms("+919999999999", "test message")

    assert "msg91.com" in captured["url"]
