import json
import asyncio
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.deps import get_db
from app.core.security import require_role
from app.core.redis import redis_client
from app.core import security_monitor
from app.modules.auditlog.model import AuditLog
from app.modules.fraud.model import FraudAlert

router = APIRouter(prefix="/admin/security", tags=["Admin Security Dashboard"])

# ── Pydantic models ──────────────────────────────────────────────────────────

class BlockRequest(BaseModel):
    target: str  # IP address or Phone number
    reason: str
    duration_seconds: int = 86400

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/metrics", response_model=Dict[str, Any])
def get_security_metrics(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """Retrieve aggregate security metrics for dashboard visualization."""
    # 1. Active sessions (Redis scan)
    pattern = "tnt:refresh_token:*"
    cursor = 0
    session_keys = []
    while True:
        cursor, chunk = redis_client.scan(cursor, match=pattern, count=100)
        session_keys.extend(chunk)
        if cursor == 0:
            break
    active_sessions_count = len(session_keys)

    # 2. Failed logins count (DB AuditLogs)
    failed_logins_count = db.query(AuditLog).filter(AuditLog.action == "auth.login_failed").count()

    # 3. Pending fraud alerts (DB FraudAlerts)
    fraud_alerts_count = db.query(FraudAlert).filter(FraudAlert.status == "pending").count()

    # 4. Critical events count (DB AuditLogs with specific actions + high severity fraud alerts)
    critical_audit_actions = [
        "auth.login_failed",
        "user.role_changed",
        "user.blocked",
        "vendor.suspended",
        "policy.updated",
        "settings.changed",
        "vendor.staff_permissions_updated"
    ]
    critical_events_count = db.query(AuditLog).filter(
        AuditLog.action.in_(critical_audit_actions)
    ).count()

    # 5. Role changes count
    role_changes_count = db.query(AuditLog).filter(AuditLog.action == "user.role_changed").count()

    # 6. Permission changes count
    permission_changes_count = db.query(AuditLog).filter(
        AuditLog.action == "vendor.staff_permissions_updated"
    ).count()

    # 7. High throughput counters from Redis
    api_abuse_count = int(redis_client.get("security:metric:api_abuse:total") or 0)
    rate_limit_violations_count = int(redis_client.get("security:metric:rate_limit_violations:total") or 0)
    jwt_failures_count = int(redis_client.get("security:metric:jwt_failures:total") or 0)

    return {
        "active_sessions": active_sessions_count,
        "failed_logins": failed_logins_count,
        "fraud_alerts": fraud_alerts_count,
        "critical_events": critical_events_count,
        "role_changes": role_changes_count,
        "permission_changes": permission_changes_count,
        "api_abuse": api_abuse_count,
        "rate_limit_violations": rate_limit_violations_count,
        "jwt_failures": jwt_failures_count,
    }


@router.get("/events", response_model=List[Dict[str, Any]])
def get_security_events(
    limit: int = Query(50, ge=1, le=100),
    admin=Depends(require_role("admin")),
):
    """Retrieve recent security events stored in Redis list."""
    events_raw = redis_client.lrange("security:recent_events", 0, limit - 1)
    events = []
    for item in events_raw:
        try:
            events.append(json.loads(item))
        except Exception:
            pass
    return events


@router.get("/sessions", response_model=List[Dict[str, Any]])
def get_active_sessions(
    db: Session = Depends(get_db),
    admin=Depends(require_role("admin")),
):
    """List active user sessions from Redis refresh tokens."""
    pattern = "tnt:refresh_token:*"
    cursor = 0
    sessions = []
    keys = []
    
    while True:
        cursor, chunk = redis_client.scan(cursor, match=pattern, count=100)
        keys.extend(chunk)
        if cursor == 0:
            break
            
    for key in keys:
        raw = redis_client.get(key)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
            user_id = payload.get("user_id")
            role = payload.get("role")
            phone = payload.get("phone")
            
            # Load user full name from database
            from app.modules.users.model import User
            user = db.query(User).filter(User.id == user_id).first()
            name = user.name or user.full_name if user else "Unknown User"
            
            ttl = redis_client.ttl(key)
            
            sessions.append({
                "token_key": key.replace("tnt:refresh_token:", ""),
                "user_id": user_id,
                "role": role,
                "phone": phone,
                "name": name,
                "ttl": ttl,
            })
        except Exception:
            pass
            
    return sessions


@router.delete("/sessions/{token_key}")
def revoke_session(
    token_key: str,
    admin=Depends(require_role("admin")),
):
    """Revoke a specific active login session."""
    key = f"tnt:refresh_token:{token_key}"
    if not redis_client.exists(key):
        raise HTTPException(status_code=404, detail="Session not found")
        
    redis_client.delete(key)
    security_monitor.log_security_event(
        event_type="session_revoked",
        severity="medium",
        details={"token_key": token_key}
    )
    return {"success": True, "message": "Session successfully revoked"}


@router.get("/ip-blocks", response_model=Dict[str, str])
def get_blocked_ips(
    admin=Depends(require_role("admin")),
):
    """List all blocked IPs or phone numbers."""
    return security_monitor.get_blocked_targets()


@router.post("/ip-blocks")
def block_ip_or_phone(
    payload: BlockRequest,
    admin=Depends(require_role("admin")),
):
    """Block an IP or Phone target."""
    security_monitor.block_target(
        target=payload.target,
        reason=payload.reason,
        duration_seconds=payload.duration_seconds
    )
    return {"success": True, "message": f"Target {payload.target} blocked successfully"}


@router.delete("/ip-blocks/{target}")
def unblock_ip_or_phone(
    target: str,
    admin=Depends(require_role("admin")),
):
    """Unblock an IP or Phone target."""
    security_monitor.unblock_target(target)
    return {"success": True, "message": f"Target {target} unblocked successfully"}


@router.websocket("/ws")
async def security_ws(websocket: WebSocket):
    """Real-time security event pub/sub over websocket."""
    await websocket.accept()
    pubsub = None
    try:
        # Step 1: Authenticate client using auth frame token
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_frame = json.loads(raw)
        token = auth_frame.get("token", "")
        
        from app.modules.orders.ws_router import _decode_token
        user_ctx = _decode_token(token)
        if not user_ctx or user_ctx.get("role", "").lower() not in {"admin", "super_admin"}:
            await websocket.send_text(json.dumps({"error": "Unauthorized"}))
            await websocket.close(code=4001)
            return
            
        await websocket.send_text(json.dumps({"authenticated": True}))

        # Step 2: Subscribe to pub/sub and stream events
        pubsub = redis_client.pubsub()
        pubsub.subscribe("tnt:security:events")
        
        while True:
            # Check for pubsub message
            message = pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                data_str = message.get("data")
                if data_str:
                    await websocket.send_text(data_str)
            await asyncio.sleep(0.5)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"error": f"Internal error: {str(e)}"}))
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        if pubsub:
            try:
                pubsub.unsubscribe("tnt:security:events")
                pubsub.close()
            except Exception:
                pass
