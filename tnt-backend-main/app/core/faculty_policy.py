import json

from app.core.redis import redis_client

FACULTY_PRIORITY_POLICY_KEY = "tnt:policy:faculty_priority"
_fallback_policy = {
    "enabled": False,
    "start_hour": 12,
    "end_hour": 14,
}


def set_faculty_priority_policy(enabled: bool, start_hour: int, end_hour: int) -> dict:
    global _fallback_policy

    policy = {
        "enabled": bool(enabled),
        "start_hour": int(start_hour),
        "end_hour": int(end_hour),
    }
    _fallback_policy = policy

    try:
        redis_client.set(FACULTY_PRIORITY_POLICY_KEY, json.dumps(policy))
    except Exception:
        pass

    return policy


def get_faculty_priority_policy() -> dict:
    try:
        raw = redis_client.get(FACULTY_PRIORITY_POLICY_KEY)
        if raw:
            data = json.loads(raw)
            return {
                "enabled": bool(data.get("enabled", False)),
                "start_hour": int(data.get("start_hour", 12)),
                "end_hour": int(data.get("end_hour", 14)),
            }
    except Exception:
        pass

    return dict(_fallback_policy)


def is_slot_in_faculty_priority_window(slot_hour: int) -> bool:
    policy = get_faculty_priority_policy()
    if not policy.get("enabled", False):
        return False

    start_hour = int(policy.get("start_hour", 12))
    end_hour = int(policy.get("end_hour", 14))
    return start_hour <= slot_hour < end_hour
