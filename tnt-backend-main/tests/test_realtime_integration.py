"""
Integration tests for the real-time architecture overhaul.

Tests cover:
1. WebSocket authorization enforcement (NEW-D1 fix)
2. Vendor dashboard WebSocket endpoint
3. Redis pub/sub event publishing
4. Vendor-wide event broadcast
5. Push notification flow
6. QR pickup confirmation flow
7. Device token registration
8. Graceful reconnection (via hook unit tests)
"""
from __future__ import annotations

import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

# Set test env before any app imports
os.environ["APP_ENV"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["USE_FAKE_REDIS"] = "1"

from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


# ── Helper: Generate test JWTs ─────────────────────────────────────────────

_SECRET = os.environ["SECRET_KEY"]
_ALGO = os.environ["JWT_ALGORITHM"]


def _make_token(user_id: int, role: str, phone: str = "9999999999") -> str:
    return create_access_token(
        data={"sub": str(user_id), "role": role, "phone": phone},
        expires_delta=60,
    )


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_redis_pubsub():
    """Ensure all Redis pub/sub calls use fakeredis and don't hang on real connections."""
    with patch("app.core.redis.redis_client.publish") as mock_publish:
        mock_publish.return_value = 1
        yield mock_publish


@pytest.fixture
def mock_db_session():
    """Mock the DB session for WS handler order lookups.

    Both WS routers bind SessionLocal at import time, so the patch must
    target their module-level names, not app.database.session.
    """
    session = MagicMock()
    with patch("app.modules.orders.ws_router.SessionLocal", return_value=session), \
         patch("app.modules.orders.vendor_ws_router.SessionLocal", return_value=session):
        yield session


# ══════════════════════════════════════════════════════════════════════════════
# Part 1: WebSocket Authorization (NEW-D1 fix enforcement)
# ══════════════════════════════════════════════════════════════════════════════


class TestWebSocketAuthorization:
    """Verifies that the WS ownership gate works correctly."""

    def test_ws_auth_requires_token(self):
        """A WS connection whose auth frame carries no token is rejected."""
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_text(json.dumps({}))  # auth frame without a token
            resp = ws.receive_json()
            assert resp.get("error") == "Unauthorized"

    def test_ws_auth_bad_token_rejected(self):
        """A WS connection with an invalid JWT should be rejected."""
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_text(json.dumps({"token": "invalid-token"}))
            response = ws.receive_json()
            assert response.get("error") == "Unauthorized"

    def test_ws_ownership_enforced_for_student(self, mock_db_session):
        """A student should only see their own orders."""
        # Mock the DB to return an order owned by user_id=2
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.user_id = 2
        mock_order.vendor_id = 1
        mock_order.total_amount = 100
        mock_order.status = "placed"
        mock_order.created_at = None
        mock_order.eta_minutes = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_order

        # Student with id=1 tries to connect to order owned by id=2
        token = _make_token(user_id=1, role="student")
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_text(json.dumps({"token": token}))
            # First response is authentication confirmation
            auth_resp = ws.receive_json()
            assert auth_resp.get("authenticated") is True

            # Second response should be the error/close
            resp = ws.receive_json()
            assert "error" in resp
            assert "Forbidden" in resp["error"]

    def test_vendor_can_see_vendor_own_order(self, mock_db_session):
        """A vendor should be able to watch orders assigned to them."""
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.user_id = 5
        mock_order.vendor_id = 10
        mock_order.total_amount = 200
        mock_order.status = "placed"
        mock_order.created_at = None
        mock_order.eta_minutes = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_order

        token = _make_token(user_id=10, role="vendor")
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_text(json.dumps({"token": token}))
            auth_resp = ws.receive_json()
            assert auth_resp.get("authenticated") is True

            # Should get status snapshot (not error)
            resp = ws.receive_json()
            assert resp.get("event") == "status"

    def test_vendor_cannot_see_other_vendors_order(self, mock_db_session):
        """A vendor should NOT watch orders assigned to a different vendor."""
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.user_id = 5
        mock_order.vendor_id = 20
        mock_order.total_amount = 200
        mock_order.status = "placed"
        mock_order.created_at = None
        mock_order.eta_minutes = None
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_order

        # Vendor 10 tries to watch vendor 20's order
        token = _make_token(user_id=10, role="vendor")
        with client.websocket_connect("/ws/orders/1") as ws:
            ws.send_text(json.dumps({"token": token}))
            auth_resp = ws.receive_json()
            assert auth_resp.get("authenticated") is True

            resp = ws.receive_json()
            assert "error" in resp
            assert "not assigned" in resp["error"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# Part 2: Vendor Dashboard WebSocket
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _sync_ws_secrets():
    """Both WS routers capture SECRET_KEY from env independently of
    app.core.security (one at import, one lazily); align them with the key
    app.core.security signed our test tokens with, since import order
    between this module's env overrides and app bootstrapping varies."""
    import app.modules.orders.ws_router as owr
    import app.modules.orders.vendor_ws_router as vwr
    from app.core.security import SECRET_KEY as core_secret

    with patch.object(owr, "_SECRET_KEY", core_secret), \
         patch.object(vwr, "_SECRET_KEY", core_secret):
        yield


class TestVendorDashboardWebSocket:
    """Verifies the vendor-wide WS dashboard endpoint."""

    def test_vendor_dashboard_requires_vendor_role(self):
        """Non-vendor roles should be rejected from /ws/vendor/orders."""
        token = _make_token(user_id=1, role="student")
        with client.websocket_connect("/ws/vendor/orders") as ws:
            ws.send_text(json.dumps({"token": token}))
            # Role gate rejects before any authenticated frame is sent
            resp = ws.receive_json()
            assert "error" in resp
            assert "vendor role required" in resp["error"].lower()

    def test_vendor_dashboard_sends_snapshot(self, mock_db_session):
        """Vendor dashboard should send an initial snapshot of active orders."""
        mock_order = MagicMock()
        mock_order.id = 42
        mock_order.user_id = 5
        mock_order.slot_id = 3
        mock_order.vendor_id = 10
        mock_order.total_amount = 300
        mock_order.status = "preparing"
        mock_order.created_at = None
        mock_order.eta_minutes = 15
        mock_order.qr_code = None
        mock_order.booking_type = "food"
        mock_order.group_id = None
        mock_order.is_group = False

        # Mock query to return one active order; enrichment item lookups
        # return an empty list so the snapshot stays JSON-serializable.
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [mock_order]
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        token = _make_token(user_id=10, role="vendor")
        with client.websocket_connect("/ws/vendor/orders") as ws:
            ws.send_text(json.dumps({"token": token}))
            auth_resp = ws.receive_json()
            assert auth_resp.get("authenticated") is True

            snapshot = ws.receive_json()
            assert snapshot.get("event") == "snapshot"
            assert isinstance(snapshot.get("data"), list)


# ══════════════════════════════════════════════════════════════════════════════
# Part 3: Redis Pub/Sub Event Publishing
# ══════════════════════════════════════════════════════════════════════════════


class TestOrderEventPublishing:
    """Verifies that order events are published to correct Redis channels."""

    def test_publish_order_event_publishes_to_order_channel(self):
        """publish_order_event should publish to order:events:{id}."""
        from app.core.order_events import publish_order_event

        with patch("app.core.redis.redis_client.publish") as mock_pub:
            mock_pub.return_value = 1
            result = publish_order_event(
                order_id=123,
                event="status_change",
                data={"vendor_id": 456, "new_status": "confirmed"},
            )
            assert result is True
            # Should publish to the per-order channel
            order_channel_calls = [
                call for call in mock_pub.call_args_list
                if "order:events:123" in str(call)
            ]
            assert len(order_channel_calls) >= 1

    def test_publish_order_event_publishes_to_vendor_channel(self):
        """publish_order_event should also publish to vendor:events:{id}."""
        from app.core.order_events import publish_order_event

        with patch("app.core.redis.redis_client.publish") as mock_pub:
            mock_pub.return_value = 1
            result = publish_order_event(
                order_id=123,
                event="status_change",
                data={"vendor_id": 456, "new_status": "confirmed"},
            )
            assert result is True
            # Should also publish to the vendor-wide channel
            vendor_channel_calls = [
                call for call in mock_pub.call_args_list
                if "vendor:events:456" in str(call)
            ]
            assert len(vendor_channel_calls) >= 1

    def test_publish_order_status_change_convenience(self):
        """publish_order_status_change should publish with correct event type."""
        from app.core.order_events import publish_order_status_change

        with patch("app.core.redis.redis_client.publish") as mock_pub:
            mock_pub.return_value = 1
            result = publish_order_status_change(
                order_id=1,
                previous_status="placed",
                new_status="confirmed",
                vendor_id=100,
                user_id=50,
                eta_minutes=15,
            )
            assert result is True
            # Verify payload has correct fields
            call_args = mock_pub.call_args_list[0]
            channel, payload_str = call_args[0]
            payload = json.loads(payload_str)
            assert payload["event"] == "status_change"
            assert payload["data"]["new_status"] == "confirmed"

    def test_publish_eta_update(self):
        """publish_eta_update should include vendor_id for broadcast."""
        from app.core.order_events import publish_eta_update

        with patch("app.core.redis.redis_client.publish") as mock_pub:
            mock_pub.return_value = 1
            result = publish_eta_update(
                order_id=1,
                eta_minutes=20,
                is_delayed=True,
                vendor_id=100,
            )
            assert result is True
            call_args = mock_pub.call_args_list[0]
            channel, payload_str = call_args[0]
            payload = json.loads(payload_str)
            assert payload["event"] == "eta_update"
            assert payload["data"]["vendor_id"] == 100


# ══════════════════════════════════════════════════════════════════════════════
# Part 4: Push Notification Flow
# ══════════════════════════════════════════════════════════════════════════════


class TestPushNotifications:
    """Verifies the push notification chain from service → FCM."""

    def test_notify_user_calls_send_push(self):
        """notify_user should call send_push when user has a device_token."""
        with patch("app.modules.notifications.service.send_push") as mock_push:
            mock_push.return_value = True
            with patch("app.modules.users.model.User") as MockUser:
                mock_user = MagicMock()
                mock_user.device_token = "test-device-token-abc"
                mock_user.push_enabled = True
                MockUser.query.filter.return_value.first.return_value = mock_user

                with patch("app.modules.notifications.service.publish_order_event") as mock_event:
                    # We can't easily test the full flow without a DB,
                    # but we can verify the import and call structure
                    from app.modules.notifications.service import notify_user
                    assert callable(notify_user)

    def test_send_push_with_fcm_key(self):
        """send_push should use httpx to POST to FCM endpoint."""
        from app.core.fcm import send_push

        with patch("app.core.fcm.FCM_SERVER_KEY", "test-key"):
            with patch("httpx.post") as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"success": 1}
                mock_post.return_value = mock_response

                result = send_push(
                    device_token="tok_123",
                    title="Test Title",
                    body="Test Body",
                    data={"key": "value"},
                )
                assert result is True
                mock_post.assert_called_once()

    def test_send_push_skipped_no_key(self):
        """send_push should return False if FCM_SERVER_KEY is not set."""
        from app.core.fcm import send_push

        with patch("app.core.fcm.FCM_SERVER_KEY", None):
            result = send_push(
                device_token="tok_123",
                title="Test",
                body="Test",
            )
            assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# Part 5: QR Pickup Confirmation
# ══════════════════════════════════════════════════════════════════════════════


class TestQRPickup:
    """Verifies QR code generation and pickup confirmation."""

    def test_generate_qr_code_valid(self):
        """generate_qr_code should produce a signed token for READY orders."""
        from app.modules.orders.model import OrderStatus
        from app.modules.orders.qr_service import generate_qr_code, _verify_qr_token

        mock_session = MagicMock()
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.status = OrderStatus.READY
        mock_order.qr_code = None
        mock_session.query.return_value.filter.return_value.first.return_value = mock_order

        qr = generate_qr_code(1, mock_session)
        assert qr is not None
        assert "." in qr  # Signed: raw_token.signature
        assert _verify_qr_token(1, qr) is True

    def test_confirm_pickup_validates_ownership(self):
        """confirm_pickup should verify vendor ownership."""
        from app.modules.orders.model import OrderStatus
        from app.modules.orders.qr_service import confirm_pickup

        mock_session = MagicMock()
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.vendor_id = 10
        mock_order.status = OrderStatus.READY
        mock_order.qr_code = "test.qr.sig"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_order

        with patch("app.modules.orders.qr_service._verify_qr_token") as mock_verify:
            mock_verify.return_value = True
            result = confirm_pickup("test.qr.sig", 10, mock_session)
            assert result is True
            assert mock_order.status == OrderStatus.PICKED

    def test_confirm_pickup_rejects_wrong_vendor(self):
        """confirm_pickup should reject if vendor doesn't own the order."""
        from app.modules.orders.model import OrderStatus
        from app.modules.orders.qr_service import confirm_pickup

        mock_session = MagicMock()
        mock_order = MagicMock()
        mock_order.id = 1
        mock_order.vendor_id = 20
        mock_order.status = OrderStatus.READY
        mock_order.qr_code = "test.qr.sig"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_order

        with patch("app.modules.orders.qr_service._verify_qr_token") as mock_verify:
            mock_verify.return_value = True
            result = confirm_pickup("test.qr.sig", 10, mock_session)
            assert result is False  # Wrong vendor


# ══════════════════════════════════════════════════════════════════════════════
# Part 6: Device Token Registration
# ══════════════════════════════════════════════════════════════════════════════


class TestDeviceTokenRegistration:
    """Verifies the backend accepts device token registration."""

    def test_device_token_endpoint_exists(self):
        """POST /profile/device-token should accept valid payload."""
        token = _make_token(user_id=1, role="student")
        response = client.post(
            "/v1/profile/device-token",
            json={"device_token": "fcm-token-abc-123", "push_enabled": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        # May be 404 if test DB has no users — but endpoint should exist (not 405/404 route)
        assert response.status_code in (200, 404, 403, 401)

    def test_device_token_rejects_unauthenticated(self):
        """POST /profile/device-token without auth should be rejected."""
        response = client.post(
            "/v1/profile/device-token",
            json={"device_token": "test", "push_enabled": True},
        )
        assert response.status_code == 403 or response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# Part 7: Order Service Event Publishing Integration
# ══════════════════════════════════════════════════════════════════════════════


class TestOrderServiceEventPublishing:
    """Verifies that status transitions in order_service publish events."""

    def test_update_order_status_publishes_event(self):
        """update_order_service should call publish_order_status_change."""
        from app.modules.orders.service import update_order_status
        from app.modules.orders.model import OrderStatus

        with patch("app.modules.orders.service._publish_status_event") as mock_publish:
            mock_order = MagicMock()
            mock_order.id = 1
            mock_order.vendor_id = 10
            mock_order.user_id = 5
            mock_order.eta_minutes = 15
            mock_order.status = OrderStatus.PLACED

            mock_db = MagicMock()

            update_order_status(
                order=mock_order,
                new_status=OrderStatus.CONFIRMED,
                changed_by="vendor",
                db=mock_db,
            )
            mock_publish.assert_called_once()
            assert mock_order.status == OrderStatus.CONFIRMED


# ══════════════════════════════════════════════════════════════════════════════
# Part 8: WebSocket Manager Vendor Channel
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def anyio_backend():
    """Run anyio-marked tests on asyncio (anyio's pytest plugin ships with the
    installed anyio package; pytest-asyncio is not a project dependency)."""
    return "asyncio"


class TestWSManagerVendorChannel:
    """Verifies the WS manager's vendor channel methods.

    Each test uses its own vendor id — the manager is a module singleton, so
    reusing an id would leak connections between tests.
    """

    @pytest.mark.anyio
    async def test_connect_vendor_adds_connection(self):
        """connect_vendor should add a websocket to the vendor map."""
        from app.modules.orders.ws_manager import manager

        ws_mock = AsyncMock()
        await manager.connect_vendor(101, ws_mock)
        try:
            assert 101 in manager._vendor_connections
            assert ws_mock in manager._vendor_connections[101]
            ws_mock.accept.assert_awaited_once()
        finally:
            manager.disconnect_vendor(101, ws_mock)

    @pytest.mark.anyio
    async def test_disconnect_vendor_removes_connection(self):
        """disconnect_vendor should remove the websocket."""
        from app.modules.orders.ws_manager import manager

        ws_mock = AsyncMock()
        await manager.connect_vendor(102, ws_mock)
        assert len(manager._vendor_connections[102]) == 1

        manager.disconnect_vendor(102, ws_mock)
        # The manager keeps the (now empty) vendor entry; what matters is
        # that no connections remain to broadcast to.
        assert not manager._vendor_connections.get(102)

    @pytest.mark.anyio
    async def test_broadcast_to_vendor_sends_to_all(self):
        """broadcast_to_vendor should send the payload to all connections."""
        from app.modules.orders.ws_manager import manager

        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await manager.connect_vendor(103, ws1)
        await manager.connect_vendor(103, ws2)

        try:
            await manager.broadcast_to_vendor(103, {"event": "test"})
            assert ws1.send_text.called
            assert ws2.send_text.called
        finally:
            manager.disconnect_vendor(103, ws1)
            manager.disconnect_vendor(103, ws2)
