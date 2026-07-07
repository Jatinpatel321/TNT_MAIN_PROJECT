"""WebSocket Router - Real-time notification endpoints."""

from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.notifications.websocket_service import manager, notify_user_realtime
from app.modules.users.model import User

logger = logging.getLogger("tnt.notifications.websocket_router")

router = APIRouter(prefix="/ws", tags=["WebSocket Notifications"])


@router.websocket("/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time notifications.
    
    Client must provide JWT token as query parameter:
    ws://localhost:8000/ws/notifications?token=<jwt_token>
    """
    # Validate token and get user
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
        
        # Verify user exists
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            await websocket.close(code=4001, reason="User not found")
            return
        
    except Exception as e:
        logger.error("websocket_auth_failed error=%s", e)
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Connect to manager
    await manager.connect(websocket, user_id)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "data": {
            "user_id": user_id,
            "message": "Connected to real-time notifications"
        }
    })

    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message from client (ping/pong)
            data = await websocket.receive_text()
            
            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")
            
            # Handle other client messages if needed
            logger.debug("websocket_message user_id=%s message=%s", user_id, data)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info("websocket_disconnected user_id=%s", user_id)
    except Exception as e:
        logger.error("websocket_error user_id=%s error=%s", user_id, e)
        manager.disconnect(websocket, user_id)


@router.get("/notifications/status")
async def get_websocket_status(
    user_id: int = Query(...),
):
    """Get WebSocket connection status for a user."""
    connection_count = manager.get_connection_count(user_id)
    return {
        "user_id": user_id,
        "connected": connection_count > 0,
        "connection_count": connection_count,
    }


@router.get("/notifications/status/all")
async def get_all_websocket_status():
    """Get WebSocket connection status for all users."""
    return {
        "total_connections": manager.get_total_connections(),
        "active_users": len(manager.active_connections),
    }