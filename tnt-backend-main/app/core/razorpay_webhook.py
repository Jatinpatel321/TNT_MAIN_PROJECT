import hashlib
import hmac
import os

from fastapi import HTTPException


def verify_webhook_signature(body: bytes, signature: str):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Webhook verification unavailable: RAZORPAY_WEBHOOK_SECRET not configured",
        )

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature or ""):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
