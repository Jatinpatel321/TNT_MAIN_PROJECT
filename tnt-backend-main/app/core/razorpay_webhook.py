import hashlib
import hmac
import os

from fastapi import HTTPException


def verify_webhook_signature(body: bytes, signature: str):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    expected_signature = hmac.new(
        bytes(secret, "utf-8"),
        body,
        hashlib.sha256
    ).hexdigest()

    if expected_signature != signature:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
