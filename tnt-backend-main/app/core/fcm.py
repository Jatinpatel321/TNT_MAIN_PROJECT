"""Firebase Cloud Messaging push notification sender.

This is the ACTIVE push notification sender.
app/modules/notifications/push_service.py was a simulated placeholder
and has been removed. This file is wired into notify_user() in
app/modules/notifications/service.py.

Set FCM_SERVER_KEY in environment for V1 HTTP Legacy API,
or set GOOGLE_APPLICATION_CREDENTIALS for the Admin SDK.
"""
import logging
import os

import httpx

logger = logging.getLogger("tnt.fcm")

FCM_SERVER_KEY = os.getenv("FCM_SERVER_KEY")
FCM_URL = "https://fcm.googleapis.com/fcm/send"


def send_push(device_token: str, title: str, body: str, data: dict | None = None) -> bool:
    """Send a push notification to a single device. Returns True on success."""
    if not FCM_SERVER_KEY:
        logger.warning("fcm_skipped reason=FCM_SERVER_KEY_not_set")
        return False

    if not device_token:
        return False

    payload = {
        "to": device_token,
        "notification": {"title": title, "body": body, "sound": "default"},
        "data": data or {},
        "priority": "high",
    }

    try:
        response = httpx.post(
            FCM_URL,
            json=payload,
            headers={
                "Authorization": f"key={FCM_SERVER_KEY}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success", 0) == 1:
                logger.info("fcm_sent device_token=%s...", device_token[:10])
                return True
            else:
                logger.warning("fcm_failed result=%s", result)
                return False
        else:
            logger.warning("fcm_http_error status=%s", response.status_code)
            return False
    except Exception as exc:
        logger.error("fcm_exception error=%s", exc)
        return False
