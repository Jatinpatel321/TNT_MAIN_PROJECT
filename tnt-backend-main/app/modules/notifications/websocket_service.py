"""WebSocket Notification Service - Real-time notifications via WebSocket."""

from __future__ import annotations

import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("tnt.notifications.websocket")


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        # Store active connections: {user_id: Set[WebSocket]}
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept new WebSocket connection."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info("websocket_connected user_id=%s", user_id)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("websocket_disconnected user_id=%s", user_id)

    async def send_personal_notification(self, user_id: int, message: dict):
        """Send notification to specific user."""
        if user_id not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error("websocket_send_failed user_id=%s error=%s", user_id, e)
                disconnected.add(connection)

        # Clean up disconnected sockets
        for conn in disconnected:
            self.active_connections[user_id].discard(conn)

    async def broadcast(self, message: dict):
        """Broadcast message to all connected users."""
        for user_id in self.active_connections:
            await self.send_personal_notification(user_id, message)

    def get_connection_count(self, user_id: int) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of active connections."""
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


async def notify_user_realtime(user_id: int, notification_data: dict):
    """Send real-time notification to user via WebSocket."""
    await manager.send_personal_notification(user_id, {
        "type": "notification",
        "data": notification_data,
    })


async def notify_vendors_realtime(vendor_ids: list[int], notification_data: dict):
    """Send real-time notification to multiple vendors."""
    for vendor_id in vendor_ids:
        await notify_user_realtime(vendor_id, notification_data)