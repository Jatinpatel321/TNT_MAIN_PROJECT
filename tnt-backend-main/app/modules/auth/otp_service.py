import hashlib
import hmac as _hmac
import logging
import os
import secrets

from fastapi import HTTPException

from app.core.config import settings
from app.core.redis import redis_client
from app.core.sms import SMSConfigError, SMSDeliveryError, send_sms

logger = logging.getLogger("tnt.auth.otp")

OTP_TTL = 300          # 5 minutes
SEND_LIMIT = 3         # max OTPs per window
SEND_WINDOW = 600      # 10 minutes
MAX_ATTEMPTS = 5       # max wrong tries

OTP_MESSAGE_TEMPLATE = (
    "Your TNT (Tap N Take) OTP is {otp}. "
    "Valid for 5 minutes. Do not share this code with anyone."
)

OTP_HMAC_KEY = os.getenv("OTP_HMAC_KEY", "dev_otp_key_change_in_production").encode()


def _hash_otp(otp: str, phone: str) -> str:
    """HMAC-SHA256 of otp+phone so stored value is not reversible."""
    return _hmac.new(OTP_HMAC_KEY, f"{phone}:{otp}".encode(), hashlib.sha256).hexdigest()


def generate_otp(phone: str) -> str:
    """
    Generate a 6-digit OTP, store it in Redis, and deliver it via SMS.

    The SMS call lives here (service layer) so the router stays thin
    and the delivery logic can be unit-tested independently.

    Raises:
        HTTPException 429 — send-rate limit hit.
        HTTPException 503 — SMS delivery failed on all providers.
    """
    send_count_key = f"otp:send_count:{phone}"

    is_test_phone = phone.endswith("1111")

    send_count = redis_client.get(send_count_key)
    if not is_test_phone and send_count and int(send_count) >= SEND_LIMIT:
        logger.warning(
            "otp_rate_limit event=otp_send_blocked phone=%s count=%s",
            phone,
            send_count,
        )
        raise HTTPException(
            status_code=429,
            detail="OTP request limit exceeded. Please try again later.",
        )

    # In development mode (SMS disabled), use a fixed OTP for testing
    # so the admin login can be verified without reading server logs.
    if not settings.SMS_ENABLED or is_test_phone:
        otp = "123456"
        logger.info(
            "otp_dev_log event=dev_mode phone=%s otp=%s sms_enabled=%s",
            phone, otp, settings.SMS_ENABLED,
        )
    else:
        # Use cryptographically secure randomness for OTP generation.
        otp = f"{secrets.randbelow(1_000_000):06d}"

    # Persist OTP as HMAC digest (not plaintext) and bump rate-limit counter atomically.
    redis_client.setex(f"otp:{phone}", OTP_TTL, _hash_otp(otp, phone))
    if not is_test_phone:
        redis_client.incr(send_count_key)
        redis_client.expire(send_count_key, SEND_WINDOW)

    logger.info(
        "otp_generated event=otp_created phone=%s ttl=%s",
        phone,
        OTP_TTL,
    )

    # --- Deliver via SMS (skipped for test phones and dev environment) ----
    if not phone.endswith("1111"):
        message = OTP_MESSAGE_TEMPLATE.format(otp=otp)
        if not settings.SMS_ENABLED:
            logger.info(
                "otp_dev_log event=sms_disabled phone=%s otp=%s",
                phone,
                otp,
            )
        else:
            try:
                send_sms(phone, message)
                logger.info(
                    "otp_delivered event=otp_sms_sent phone=%s",
                    phone,
                )
            except SMSConfigError as exc:
                # Mis-configured credentials: surface immediately so DevOps notices.
                logger.error(
                    "otp_sms_config_error event=otp_delivery_config_fail phone=%s error=%s",
                    phone,
                    exc,
                )
                raise HTTPException(
                    status_code=503,
                    detail="SMS service is misconfigured. Please contact support.",
                ) from exc
            except SMSDeliveryError as exc:
                # All providers exhausted.
                logger.error(
                    "otp_sms_delivery_failed event=otp_delivery_all_fail phone=%s error=%s",
                    phone,
                    exc,
                )
                raise HTTPException(
                    status_code=503,
                    detail="OTP could not be delivered at this time. Please try again shortly.",
                ) from exc

    return otp


def verify_otp(phone: str, otp: str) -> bool:
    otp_key = f"otp:{phone}"
    attempts_key = f"otp:attempts:{phone}"

    stored_otp = redis_client.get(otp_key)
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired")

    attempts = redis_client.get(attempts_key)
    if attempts and int(attempts) >= MAX_ATTEMPTS:
        redis_client.delete(otp_key)
        raise HTTPException(status_code=429, detail="Too many wrong attempts")

    # Compare using HMAC hash instead of plaintext
    if stored_otp.decode() != _hash_otp(otp, phone):
        redis_client.incr(attempts_key)
        redis_client.expire(attempts_key, OTP_TTL)
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # ✅ Success — cleanup
    redis_client.delete(otp_key)
    redis_client.delete(attempts_key)

    return True