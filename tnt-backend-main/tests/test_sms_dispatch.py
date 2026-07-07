"""
Tests that SMS is actually dispatched (calls app.core.sms.send_sms) for the
three urgent event types — ORDER_READY, DELAY_ALERT, ORDER_CANCELLED — and
that promotional/marketing events correctly skip SMS.

Also verifies the sms_fallback suppression mechanism.

Import strategy: load models in dependency order to satisfy SQLAlchemy's
declarative mapper, then patch Notification.__init__ to avoid DB writes.
"""
from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock, patch, PropertyMock

# ── Controlled model imports to satisfy SQLAlchemy mapper forward-refs ──
# User has relationship("Group") — load Group first, then User
# User also has relationship("StationeryService") — load that module too
import app.modules.group_cart.model       # noqa: F401 — defines Group
import app.modules.users.model             # noqa: F401 — satisfies 'Group' ref
import app.modules.orders.model            # noqa: F401 — OrderStatus etc
import app.modules.notifications.model     # noqa: F401 — Notification, NotificationType
import app.modules.menu.model              # noqa: F401 — satisfies 'MenuItem' ref on User
import app.modules.stationery.service_model  # noqa: F401 — satisfies 'StationeryService' ref on User

# Now we can safely import the service
from app.modules.notifications.model import NotificationType
from app.modules.notifications.service import notify_user
from app.modules.slots.model import BookingStatus  # type: ignore[attr-defined]


class _NotifyUserTestBase(TestCase):
    """Provides _call_notify helper with mocked DB session."""

    def setUp(self):
        # Make Notification() return a pre-built mock so we never hit
        # SQLAlchemy's ORM constructor or mapper initialization.
        self.mock_notification_inst = MagicMock()
        self.mock_notification_inst.id = 9999
        # Patch Notification in the service module where it's imported and used
        self._patch_notification = patch(
            "app.modules.notifications.service.Notification",
            return_value=self.mock_notification_inst,
        )
        self.mock_notification_cls = self._patch_notification.start()

        self.mock_db = MagicMock()
        self.mock_db.add.return_value = None
        self.mock_db.flush.return_value = None
        self.mock_db.commit.return_value = None
        self.mock_user = MagicMock()
        self.mock_user.device_token = None
        self.mock_user.push_enabled = True
        self.mock_user.preferences = {}
        # Patch the User query to return our mock
        user_query = MagicMock()
        user_query.filter.return_value.first.return_value = self.mock_user
        self.mock_db.query.return_value = user_query

    def tearDown(self):
        self._patch_notification.stop()

    def _call_notify(self, **overrides):
        kwargs = {
            "user_id": 1, "phone": "+919999999999",
            "title": "Test", "message": "Test message",
            "db": self.mock_db, "send_sms_flag": True,
            "notification_type": NotificationType.SYSTEM,
            "reference_id": None,
        }
        kwargs.update(overrides)
        return notify_user(**kwargs)


class TestUrgentEventSMSSent(_NotifyUserTestBase):
    """Verify send_sms is called for ORDER_READY, DELAY_ALERT, ORDER_CANCELLED."""

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_order_ready_triggers_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=1, phone="+919999999999",
            title="Order Ready",
            message="Your order #42 is ready for pickup!",
            send_sms_flag=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=42,
        )
        mock_sms.assert_called_once_with("+919999999999", "Your order #42 is ready for pickup!")

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_delay_alert_triggers_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=2, phone="+919999999998",
            title="Order Delay",
            message="Your order #99 is delayed by 15 minutes.",
            send_sms_flag=True,
            notification_type=NotificationType.DELAY_ALERT,
            reference_id=99,
        )
        mock_sms.assert_called_once_with("+919999999998", "Your order #99 is delayed by 15 minutes.")

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_order_cancelled_triggers_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=3, phone="+919999999997",
            title="Order Cancelled",
            message="Your order #17 has been cancelled.",
            send_sms_flag=True,
            notification_type=NotificationType.ORDER_CANCELLED,
            reference_id=17,
        )
        mock_sms.assert_called_once_with("+919999999997", "Your order #17 has been cancelled.")


class TestPromotionalSMSNotSent(_NotifyUserTestBase):
    """Verify send_sms is NOT called for PROMO events (send_sms_flag=False)."""

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_promo_sms_skipped_when_flag_false(self, mock_push, mock_sms):
        self._call_notify(
            user_id=10, phone="+919999999990",
            title="Special Offer!",
            message="Get 20% off!",
            send_sms_flag=False,
            notification_type=NotificationType.PROMO,
            reference_id=100,
        )
        mock_sms.assert_not_called()

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_system_defaults_to_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=11, phone="+919999999989",
            title="System Notice",
            message="Maintenance tonight.",
            notification_type=NotificationType.SYSTEM,
        )
        mock_sms.assert_called_once()


class TestSMSFallbackSuppression(_NotifyUserTestBase):
    """Verify SMS is skipped when push just delivered (within 30s)."""

    def setUp(self):
        super().setUp()
        self.mock_user.device_token = "fcm-token-abc"

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_sms_skipped_when_push_delivered_recently(self, mock_push, mock_sms):
        mock_push.return_value = True
        self._call_notify(
            user_id=42, phone="+919999999991",
            title="Order Ready", message="Order #200 ready.",
            send_sms_flag=True, sms_fallback=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=200,
        )
        mock_sms.assert_not_called()

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_sms_not_skipped_when_fallback_false(self, mock_push, mock_sms):
        mock_push.return_value = True
        self._call_notify(
            user_id=43, phone="+919999999992",
            title="Order Ready", message="Order #201 ready.",
            send_sms_flag=True, sms_fallback=False,
            notification_type=NotificationType.ORDER_READY,
            reference_id=201,
        )
        mock_sms.assert_called_once()

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_sms_sent_when_push_fails(self, mock_push, mock_sms):
        mock_push.side_effect = Exception("FCM down")
        self._call_notify(
            user_id=44, phone="+919999999993",
            title="Order Ready", message="Order #202 ready.",
            send_sms_flag=True, sms_fallback=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=202,
        )
        mock_sms.assert_called_once()


class TestSMSMessageContent(_NotifyUserTestBase):
    """Verify SMS message content for each event type."""

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_ready_message(self, mock_push, mock_sms):
        self._call_notify(
            user_id=5, phone="+911111111111",
            title="Order Ready for Pickup!",
            message="Your order #88 is ready. Please collect it.",
            send_sms_flag=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=88,
        )
        msg = mock_sms.call_args[0][1]
        self.assertIn("ready", msg.lower())
        self.assertIn("#88", msg)

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_delay_message(self, mock_push, mock_sms):
        self._call_notify(
            user_id=6, phone="+912222222222",
            title="Order Delay",
            message="Your order #77 is delayed by 10 minutes.",
            send_sms_flag=True,
            notification_type=NotificationType.DELAY_ALERT,
            reference_id=77,
        )
        msg = mock_sms.call_args[0][1]
        self.assertIn("delay", msg.lower())
        self.assertIn("10 minutes", msg)
        self.assertIn("#77", msg)

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_cancellation_message(self, mock_push, mock_sms):
        self._call_notify(
            user_id=7, phone="+913333333333",
            title="Order Cancelled",
            message="Your order #55 has been cancelled.",
            send_sms_flag=True,
            notification_type=NotificationType.ORDER_CANCELLED,
            reference_id=55,
        )
        msg = mock_sms.call_args[0][1]
        self.assertIn("cancelled", msg.lower())
        self.assertIn("#55", msg)


class TestExistingCallersFlagFalse(_NotifyUserTestBase):
    """Verify callers that intentionally use send_sms_flag=False."""

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_promotion_router_skips_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=20, phone="+914444444444",
            title="Special Deal!", message="Check our offers!",
            send_sms_flag=False,
            notification_type=NotificationType.PROMO,
            reference_id=2001,
        )
        mock_sms.assert_not_called()

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_retention_service_skips_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=21, phone="+915555555555",
            title="Special Offer: 20% off!", message="20% off!",
            send_sms_flag=False,
            notification_type=NotificationType.PROMO,
            reference_id=3001,
        )
        mock_sms.assert_not_called()

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_inventory_alert_skips_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=22, phone="+916666666666",
            title="Inventory Alert", message="Item low.",
            send_sms_flag=False,
            notification_type=NotificationType.ALERT,
            reference_id=4001,
        )
        mock_sms.assert_not_called()

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    def test_group_cart_skips_sms(self, mock_push, mock_sms):
        self._call_notify(
            user_id=23, phone="+917777777777",
            title="Group Updated", message="John added items.",
            send_sms_flag=False,
            notification_type=NotificationType.SYSTEM,
        )
        mock_sms.assert_not_called()


class TestSlotCancellationSMSTriggered(_NotifyUserTestBase):
    """Verify slot cancellation flows through cancel_slot_booking and
    actually calls notify_user with send_sms_flag=True and the right
    message for cancellation."""

    @patch("app.modules.notifications.service.send_sms")
    @patch("app.modules.notifications.service.send_push")
    @patch("app.modules.slots.service.SlotBooking")
    @patch("app.modules.slots.service.Slot")
    @patch("app.modules.slots.service.User")
    def test_cancel_slot_triggers_notification(
        self, mock_User, mock_Slot, mock_SlotBooking,
        mock_send_push, mock_send_sms,
    ):
        """cancel_slot_booking calls notify_user which in turn calls
        send_sms with send_sms_flag=True and a cancellation message."""
        from datetime import datetime
        from app.modules.slots.service import cancel_slot_booking

        # Build controlled mocks
        mock_booking = MagicMock()
        mock_booking.id = 99
        mock_booking.status = BookingStatus.CONFIRMED
        mock_booking.slot_id = 10
        mock_booking.user_id = 42

        mock_slot = MagicMock()
        mock_slot.id = 10
        mock_slot.vendor_id = 1
        mock_slot.start_time = datetime(2026, 6, 24, 10, 30)
        mock_slot.current_orders = 5
        mock_slot.max_orders = 10

        mock_user = MagicMock()
        mock_user.id = 42
        mock_user.phone = "+919999999999"
        mock_user.preferences = {}
        mock_user.device_token = None  # prevent push success → SMS suppression

        # prevent db.commit from failing
        self.mock_db.commit.return_value = None

        # Import the real User class so we can match it in side_effect
        from app.modules.users.model import User as RealUser

        def query_side_effect(model):
            if model == mock_SlotBooking:
                q = MagicMock()
                q.filter.return_value.first.return_value = mock_booking
                return q
            if model == mock_Slot:
                q = MagicMock()
                q.filter.return_value.first.return_value = mock_slot
                return q
            if model == mock_User or model == RealUser:
                q = MagicMock()
                q.filter.return_value.first.return_value = mock_user
                return q
            return MagicMock()

        self.mock_db.query.side_effect = query_side_effect

        slot, booking = cancel_slot_booking(99, 42, self.mock_db)

        # Verify send_sms was called with the cancellation message
        mock_send_sms.assert_called_once()
        msg = mock_send_sms.call_args[0][1]
        self.assertIn("cancelled", msg.lower())
        self.assertIn("99", msg)


@patch("app.modules.notifications.service.send_sms")
@patch("app.modules.notifications.service.send_push")
class TestPerUserSMSFallbackPreference(_NotifyUserTestBase):
    """Verify per-user sms_fallback from user.preferences JSON column."""

    def test_sms_fallback_true_from_prefs(self, mock_push, mock_sms):
        """When user.preferences={'sms_fallback': True} and push succeeds,
        SMS is skipped (fallback suppression active)."""
        self.mock_user.device_token = "fcm-token"
        self.mock_user.preferences = {"sms_fallback": True}
        self._call_notify(
            user_id=1, phone="+919999999999",
            title="Order Ready", message="Order #1 ready.",
            send_sms_flag=True, sms_fallback=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=1,
        )
        # sms_fallback=True + push succeeded → SMS suppressed
        mock_sms.assert_not_called()

    def test_sms_fallback_false_from_prefs(self, mock_push, mock_sms):
        """When user.preferences={'sms_fallback': False}, SMS is always sent
        even when push succeeds (user opted out of suppression)."""
        self.mock_user.device_token = "fcm-token"
        self.mock_user.preferences = {"sms_fallback": False}
        self._call_notify(
            user_id=2, phone="+919999999998",
            title="Order Ready", message="Order #2 ready.",
            send_sms_flag=True, sms_fallback=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=2,
        )
        # sms_fallback=False → bypass suppression, send SMS
        mock_sms.assert_called_once()

    def test_sms_fallback_missing_from_prefs(self, mock_push, mock_sms):
        """When user.preferences has no 'sms_fallback' key, fallback to
        caller-supplied value (default True)."""
        self.mock_user.device_token = "fcm-token"
        self.mock_user.preferences = {"push_enabled": True}
        self._call_notify(
            user_id=3, phone="+919999999997",
            title="Order Ready", message="Order #3 ready.",
            send_sms_flag=True, sms_fallback=True,
            notification_type=NotificationType.ORDER_READY,
            reference_id=3,
        )
        # default sms_fallback=True + push succeeded → SMS suppressed
        mock_sms.assert_not_called()

    def test_sms_fallback_prefs_overrides_caller_false(self, mock_push, mock_sms):
        """user.preferences={'sms_fallback': True} overrides caller's
        sms_fallback=False — suppression still active."""
        self.mock_user.device_token = "fcm-token"
        self.mock_user.preferences = {"sms_fallback": True}
        self._call_notify(
            user_id=4, phone="+919999999996",
            title="Order Ready", message="Order #4 ready.",
            send_sms_flag=True, sms_fallback=False,
            notification_type=NotificationType.ORDER_READY,
            reference_id=4,
        )
        # prefs says True → suppression check applies → SMS suppressed
        mock_sms.assert_not_called()
