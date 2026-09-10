import logging
import os

import razorpay

_logger = logging.getLogger("tnt.razorpay")

_key_id = os.getenv("RAZORPAY_KEY_ID")
_key_secret = os.getenv("RAZORPAY_KEY_SECRET")

if not _key_id or not _key_secret:
    _logger.warning(
        "RAZORPAY_KEY_ID and/or RAZORPAY_KEY_SECRET not set — "
        "payment operations will fail until configured"
    )

client = razorpay.Client(auth=(_key_id or "", _key_secret or ""))
