import json
import time
from typing import Dict, Any, Optional
from app.core.redis import redis_client

EVENT_KEY = "security:recent_events"
MAX_EVENTS = 100
PUB_CHANNEL = "tnt:security:events"

def log_security_event(
    event_type: str,
    severity: str,
    details: Dict[str, Any],
    ip: Optional[str] = None,
    user_id: Optional[int] = None,
):
    """
    Log a security event:
    1. Increment the specific event metric counter.
    2. Add to bounded list of recent events in Redis.
    3. Publish to Redis pub/sub channel for real-time dashboard updates.
    """
    # 1. Increment specific counters
    redis_client.incr(f"security:metric:{event_type}:total")
    redis_client.incr("security:metric:total_events")
    
    # 2. Structure the event payload
    event = {
        "id": f"evt_{int(time.time() * 1000)}",
        "timestamp": time.time(),
        "event_type": event_type,
        "severity": severity,
        "details": details,
        "ip_address": ip,
        "user_id": user_id,
    }
    
    # Push to Redis list
    payload = json.dumps(event)
    redis_client.lpush(EVENT_KEY, payload)
    redis_client.ltrim(EVENT_KEY, 0, MAX_EVENTS - 1)
    
    # 3. Publish to Pub/Sub
    try:
        redis_client.publish(PUB_CHANNEL, payload)
    except Exception:
        pass

def record_jwt_failure(ip: Optional[str], token_preview: str, reason: str):
    log_security_event(
        event_type="jwt_failure",
        severity="high",
        details={"token_preview": token_preview, "reason": reason},
        ip=ip
    )

def record_rate_limit_violation(ip: Optional[str], path: str, limit_key: str):
    log_security_event(
        event_type="rate_limit_violation",
        severity="medium",
        details={"path": path, "limit_key": limit_key},
        ip=ip
    )

def record_api_abuse(ip: Optional[str], path: str, user_id: Optional[int], reason: str):
    log_security_event(
        event_type="api_abuse",
        severity="critical",
        details={"path": path, "reason": reason},
        ip=ip,
        user_id=user_id
    )

# IP and phone blocking utilities
def block_target(target: str, reason: str, duration_seconds: int = 86400):
    """Block an IP or Phone number in Redis."""
    redis_client.setex(f"security:blocked:{target}", duration_seconds, reason)
    log_security_event(
        event_type="target_blocked",
        severity="high",
        details={"target": target, "reason": reason, "duration": duration_seconds}
    )

def unblock_target(target: str):
    """Unblock an IP or Phone number in Redis."""
    redis_client.delete(f"security:blocked:{target}")
    log_security_event(
        event_type="target_unblocked",
        severity="medium",
        details={"target": target}
    )

def is_target_blocked(target: str) -> bool:
    """Check if target (IP or Phone) is currently blocked."""
    return redis_client.exists(f"security:blocked:{target}") > 0

def get_blocked_targets() -> Dict[str, str]:
    """Retrieve all blocked targets and reasons."""
    pattern = "security:blocked:*"
    blocked = {}
    cursor = 0
    while True:
        cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
        for key in keys:
            target = key.replace("security:blocked:", "")
            reason = redis_client.get(key) or "No reason provided"
            blocked[target] = reason
        if cursor == 0:
            break
    return blocked
