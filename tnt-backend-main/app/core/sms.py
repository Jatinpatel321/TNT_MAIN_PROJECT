import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("tnt.sms")


# ---------------------------------------------------------------------------
# Structured exception hierarchy
# ---------------------------------------------------------------------------

class SMSConfigError(RuntimeError):
    """Raised when required provider credentials are missing."""


class SMSNetworkError(RuntimeError):
    """Raised when the SMS provider is unreachable (timeout, DNS, etc.)."""


class SMSProviderDownError(RuntimeError):
    """Raised when the SMS provider returns a 5xx server error."""


class SMSRateLimitError(RuntimeError):
    """Raised when the SMS provider throttles the request (429)."""


class SMSDeliveryError(RuntimeError):
    """Generic delivery failure after all provider attempts are exhausted."""


# ---------------------------------------------------------------------------
# Provider helpers
# ---------------------------------------------------------------------------

def _send_twilio(phone: str, message: str) -> None:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN or not settings.SMS_FROM:
        raise SMSConfigError("Missing Twilio SMS configuration (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / SMS_FROM)")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    data = {
        "To": phone,
        "From": settings.SMS_FROM,
        "Body": message,
    }

    try:
        response = httpx.post(
            url,
            data=data,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=10.0,
        )
    except httpx.TimeoutException as exc:
        raise SMSNetworkError("Twilio request timed out") from exc
    except httpx.ConnectError as exc:
        raise SMSNetworkError("Twilio connection failed") from exc

    _raise_for_status("twilio", response)


def _send_msg91(phone: str, message: str) -> None:
    if not settings.MSG91_AUTH_KEY or not settings.MSG91_SENDER_ID:
        raise SMSConfigError("Missing MSG91 SMS configuration (MSG91_AUTH_KEY / MSG91_SENDER_ID)")

    url = "https://api.msg91.com/api/v5/flow/"
    headers = {
        "authkey": settings.MSG91_AUTH_KEY,
        "content-type": "application/json",
    }
    payload = {
        "route": settings.MSG91_ROUTE,
        "sender": settings.MSG91_SENDER_ID,
        "mobiles": phone,
        "message": message,
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
    except httpx.TimeoutException as exc:
        raise SMSNetworkError("MSG91 request timed out") from exc
    except httpx.ConnectError as exc:
        raise SMSNetworkError("MSG91 connection failed") from exc

    _raise_for_status("msg91", response)


def _raise_for_status(provider: str, response: httpx.Response) -> None:
    """Translate HTTP status codes into structured exceptions."""
    if response.status_code == 429:
        raise SMSRateLimitError(f"{provider} rate limit exceeded (HTTP 429)")
    if response.status_code >= 500:
        raise SMSProviderDownError(
            f"{provider} server error (HTTP {response.status_code})"
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise SMSDeliveryError(f"{provider} rejected the request: {exc}") from exc


# ---------------------------------------------------------------------------
# Dispatch table + fallback logic
# ---------------------------------------------------------------------------

_PROVIDER_FN = {
    "twilio": _send_twilio,
    "msg91": _send_msg91,
}

_FALLBACK = {
    "twilio": "msg91",
    "msg91": "twilio",
}


def _attempt_send(provider: str, phone: str, message: str) -> None:
    """Try one provider, raising a structured exception on failure."""
    fn = _PROVIDER_FN.get(provider)
    if fn is None:
        raise SMSConfigError(f"Unsupported SMS_PROVIDER: {provider}")
    fn(phone, message)


def send_sms(phone: str, message: str) -> None:
    """
    Send *message* to *phone*.

    Resolution order:
      1. Primary provider (``SMS_PROVIDER`` setting).
      2. Fallback provider if the primary fails with a transient error
         (network, provider downtime, rate limit).

    In development (``SMS_ENABLED=false``) the call is a no-op and the
    OTP is logged at DEBUG level so engineers can still test locally.
    """
    if not settings.SMS_ENABLED:
        logger.info(
            "sms_skipped event=sms_disabled provider=%s phone=%s",
            settings.SMS_PROVIDER,
            phone,
        )
        return

    primary = settings.SMS_PROVIDER
    fallback = _FALLBACK.get(primary)

    # --- Primary attempt ------------------------------------------------
    try:
        _attempt_send(primary, phone, message)
        logger.info(
            "sms_sent event=sms_delivered provider=%s phone=%s",
            primary,
            phone,
        )
        return
    except SMSConfigError:
        # Config errors are not transient — no point trying the fallback.
        logger.error(
            "sms_config_error event=sms_config_missing provider=%s phone=%s",
            primary,
            phone,
        )
        raise
    except SMSRateLimitError:
        logger.warning(
            "sms_rate_limit event=sms_rate_limited provider=%s phone=%s",
            primary,
            phone,
        )
    except SMSProviderDownError:
        logger.warning(
            "sms_provider_down event=sms_provider_down provider=%s phone=%s",
            primary,
            phone,
        )
    except SMSNetworkError:
        logger.warning(
            "sms_network_error event=sms_network_failure provider=%s phone=%s",
            primary,
            phone,
        )
    except SMSDeliveryError:
        logger.warning(
            "sms_delivery_error event=sms_delivery_fail provider=%s phone=%s",
            primary,
            phone,
        )

    # --- Fallback attempt -----------------------------------------------
    if not fallback:
        raise SMSDeliveryError(
            f"SMS delivery failed on primary provider '{primary}' and no fallback is configured"
        )

    logger.info(
        "sms_fallback event=sms_fallback_attempt primary=%s fallback=%s phone=%s",
        primary,
        fallback,
        phone,
    )

    try:
        _attempt_send(fallback, phone, message)
        logger.info(
            "sms_sent event=sms_delivered provider=%s phone=%s (via fallback)",
            fallback,
            phone,
        )
    except (SMSConfigError, SMSNetworkError, SMSProviderDownError, SMSRateLimitError, SMSDeliveryError) as exc:
        logger.error(
            "sms_fallback_failed event=sms_all_providers_failed primary=%s fallback=%s phone=%s error=%s",
            primary,
            fallback,
            phone,
            exc,
        )
        raise SMSDeliveryError(
            f"SMS delivery failed on both '{primary}' and fallback '{fallback}'"
        ) from exc
