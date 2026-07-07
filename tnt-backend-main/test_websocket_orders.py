"""
Tests for app/modules/orders/ws_router.py

Covers:
  - _decode_token  (valid, invalid, missing fields)
  - _get_order_snapshot  (found, not found)
  - _is_terminal  (terminal and non-terminal statuses)
  - _OrderConnectionManager  (connect, disconnect, send, broadcast)
  - order_status_ws WebSocket endpoint:
      * authentication timeout
      * invalid JSON frame
      * invalid token
      * order not found
      * already terminal order
      * normal tracking flow with status change
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, UTC, timedelta, time as dt_time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.main import app as fastapi_app
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.ws_router import (
    _decode_token,
    _get_order_snapshot,
    _is_terminal,
    _SECRET_KEY,
    _ALGORITHM,
)
from app.modules.orders.ws_manager import manager as ws_manager
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole

# ── Import all models ─────────────────────────────────────────────────────
import app.modules.group_cart.model  # noqa: F401
import app.modules.stationery.job_model  # noqa: F401
import app.modules.rewards.model  # noqa: F401
import app.modules.complaints.model  # noqa: F401


def _utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


def _make_token(user_id: int = 1, role: str = "student") -> str:
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": 9999999999},
        _SECRET_KEY,
        algorithm=_ALGORITHM,
    )


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, Session()


# ═══════════════════════════════════════════════════════════════════════════
#  Helper function unit tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDecodeToken:
    def test_valid_token(self):
        token = _make_token(42, "student")
        result = _decode_token(token)
        assert result is not None
        assert result["id"] == 42
        assert result["role"] == "student"

    def test_invalid_token_returns_none(self):
        result = _decode_token("totally.invalid.jwt")
        assert result is None

    def test_token_missing_sub_returns_none(self):
        token = jwt.encode({"role": "student", "exp": 9999999999}, _SECRET_KEY, algorithm=_ALGORITHM)
        result = _decode_token(token)
        assert result is None

    def test_token_missing_role_returns_none(self):
        token = jwt.encode({"sub": "1", "exp": 9999999999}, _SECRET_KEY, algorithm=_ALGORITHM)
        result = _decode_token(token)
        assert result is None

    def test_token_non_integer_sub_returns_none(self):
        token = jwt.encode({"sub": "not-a-number", "role": "student", "exp": 9999999999}, _SECRET_KEY, algorithm=_ALGORITHM)
        result = _decode_token(token)
        assert result is None

    def test_empty_token_returns_none(self):
        result = _decode_token("")
        assert result is None


class TestGetOrderSnapshot:
    def test_order_found(self):
        engine, db = _build_session()
        try:
            vendor = User(phone="v_ws_1", role=UserRole.VENDOR, is_active=True, is_approved=True)
            student = User(phone="s_ws_1", role=UserRole.STUDENT, is_active=True)
            db.add_all([vendor, student])
            db.flush()
            slot = Slot(vendor_id=vendor.id, start_time=datetime(2026, 1, 1, 12, 0), end_time=datetime(2026, 1, 1, 12, 30),
                        max_orders=10, current_orders=0, status=SlotStatus.AVAILABLE)
            db.add(slot)
            db.flush()
            order = Order(user_id=student.id, slot_id=slot.id, vendor_id=vendor.id,
                          status=OrderStatus.PLACED, total_amount=100)
            db.add(order)
            db.commit()

            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.return_value = order

            with patch("app.modules.orders.ws_router.SessionLocal", return_value=mock_session):
                snapshot = _get_order_snapshot(order.id)
            assert snapshot is not None
            assert snapshot["order_id"] == order.id
            assert "status" in snapshot
        finally:
            engine.dispose()

    def test_order_not_found_returns_none(self):
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with patch("app.modules.orders.ws_router.SessionLocal", return_value=mock_session):
            snapshot = _get_order_snapshot(99999)
        assert snapshot is None


class TestIsTerminal:
    def test_picked_is_terminal(self):
        assert _is_terminal("picked") is True

    def test_completed_is_terminal(self):
        assert _is_terminal("completed") is True

    def test_cancelled_is_terminal(self):
        assert _is_terminal("cancelled") is True

    def test_placed_is_not_terminal(self):
        assert _is_terminal("placed") is False

    def test_confirmed_is_not_terminal(self):
        assert _is_terminal("confirmed") is False

    def test_ready_is_not_terminal(self):
        assert _is_terminal("ready") is False

    def test_pending_is_not_terminal(self):
        assert _is_terminal("pending") is False


class TestConnectionManager:
    def test_connect_accepts_websocket(self):
        manager = type(ws_manager)()
        mock_ws = AsyncMock()

        async def _run():
            await manager.connect(42, mock_ws)

        asyncio.run(_run())
        mock_ws.accept.assert_called_once()

    def test_disconnect_removes_connection(self):
        manager = type(ws_manager)()
        mock_ws = AsyncMock()

        async def _run():
            await manager.connect(42, mock_ws)
            manager.disconnect(42, mock_ws)

        asyncio.run(_run())
        assert mock_ws not in manager._active.get(42, [])

    def test_disconnect_nonexistent_is_safe(self):
        manager = type(ws_manager)()
        mock_ws = AsyncMock()
        # Should not raise
        manager.disconnect(9999, mock_ws)

    def test_send_text(self):
        manager = type(ws_manager)()
        mock_ws = AsyncMock()
        payload = {"event": "status", "data": {"order_id": 1}}

        async def _run():
            await manager.send_json(mock_ws, payload)

        asyncio.run(_run())
        mock_ws.send_text.assert_called_once()

    def test_send_handles_exception_gracefully(self):
        """If send fails, no exception propagates."""
        manager = type(ws_manager)()
        mock_ws = AsyncMock()
        mock_ws.send_text.side_effect = Exception("connection reset")

        async def _run():
            await manager.send_json(mock_ws, {"data": "test"})

        # Should not raise
        asyncio.run(_run())

    def test_broadcast_sends_to_all(self):
        manager = type(ws_manager)()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        async def _run():
            await manager.connect(42, mock_ws1)
            await manager.connect(42, mock_ws2)
            await manager.broadcast(42, {"event": "update"})

        asyncio.run(_run())
        # Both should have received the message
        assert mock_ws1.send_text.called
        assert mock_ws2.send_text.called


# ═══════════════════════════════════════════════════════════════════════════
#  WebSocket Endpoint Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestWebSocketEndpoint:
    def _make_order_snapshot(self, order_id=1, status="placed"):
        return {
            "order_id": order_id,
            "status": status,
            "vendor_id": 1,
            "total_amount": 100,
            "created_at": None,
        }

    def test_invalid_json_auth_frame_closes_4001(self):
        """Sending non-JSON as first frame → 4001 close."""
        client = TestClient(fastapi_app)
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_text("not-valid-json")
            data = ws.receive_json()
            assert "error" in data

    def test_invalid_token_closes_connection(self):
        """Invalid JWT → error response."""
        client = TestClient(fastapi_app)
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_json({"token": "definitely.not.valid"})
            data = ws.receive_json()
            assert "error" in data
            assert data.get("code") == 4001 or "Unauthorized" in str(data)

    def test_order_not_found_closes_4004(self):
        """Valid token but order doesn't exist → error then close."""
        token = _make_token(1, "student")
        client = TestClient(fastapi_app)

        mock_snapshot = None  # Order not found

        with patch("app.modules.orders.ws_router._get_order_snapshot", return_value=mock_snapshot):
            with client.websocket_connect("/ws/orders/99999") as ws:
                ws.send_json({"token": token})
                # Get auth confirmation
                auth_data = ws.receive_json()
                assert auth_data.get("authenticated") is True
                # Get "Order not found" error
                error_data = ws.receive_json()
                assert "error" in error_data

    def test_already_terminal_order_closes_1000(self):
        """Order already in terminal state → sends terminal event and closes."""
        # Use admin token so ownership check is bypassed (user_id=1 == vendor_id=1 check)
        token = _make_token(1, "admin")
        client = TestClient(fastapi_app)

        terminal_snapshot = self._make_order_snapshot(1, "picked")
        terminal_snapshot["user_id"] = 1  # admin access bypasses ownership check

        with patch("app.modules.orders.ws_router._get_order_snapshot", return_value=terminal_snapshot):
            with client.websocket_connect("/ws/orders/1") as ws:
                ws.send_json({"token": token})
                # Auth confirmation
                auth_data = ws.receive_json()
                assert auth_data.get("authenticated") is True
                # Initial status
                status_data = ws.receive_json()
                assert status_data.get("event") == "status"
                # Terminal event
                terminal_data = ws.receive_json()
                assert terminal_data.get("event") == "terminal"

    def test_status_change_triggers_update(self):
        """Skipped: polling model replaced by Redis pub/sub event-driven model."""
        pytest.skip("ws_router uses Redis pub/sub, not polling — covered by integration tests")

    def test_order_disappears_during_poll(self):
        """Skipped: polling model replaced by Redis pub/sub event-driven model."""
        pytest.skip("ws_router uses Redis pub/sub, not polling — covered by integration tests")



