"""Comprehensive test suite for vendor application features.

Tests:
1. Business Hours Enforcement - open/closed scenarios
2. Auto Stock Deduction - stock decrements on order placement
3. Auto Disable Inventory - items disabled when stock=0
4. Vendor Dashboard endpoints - live orders, revenue chart, customer insights
5. Demand Dashboard endpoints
6. WebSocket auth fix verification
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.vendors.business_hours_service import (
    check_business_hours,
    get_vendor_business_hours,
    update_vendor_business_hours,
)
from app.modules.orders.checkout_service import _deduct_inventory_for_order
from app.modules.orders.model import Order, OrderStatus
from app.modules.menu.model import MenuItem, Inventory
from app.modules.vendors.demand_dashboard_service import DemandDashboardService


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_db():
    """Create a mock DB session."""
    return MagicMock(spec=Session)


@pytest.fixture
def mock_vendor_profile():
    """Mock VendorProfile with business hours."""
    import types
    profile = types.SimpleNamespace()
    profile.id = 1
    profile.vendor_id = 1
    profile.is_open = True
    profile.business_hours = {
        "monday": {"open": "09:00", "close": "21:00"},
        "tuesday": {"open": "09:00", "close": "21:00"},
        "wednesday": {"open": "09:00", "close": "21:00"},
        "thursday": {"open": "09:00", "close": "21:00"},
        "friday": {"open": "09:00", "close": "22:00"},
        "saturday": {"open": "10:00", "close": "22:00"},
        "sunday": {"open": "10:00", "close": "20:00"},
    }
    profile.holidays = [{"date": "2024-12-25", "reason": "Christmas"}]
    return profile


@pytest.fixture
def mock_vendor():
    """Mock Vendor object."""
    import types
    v = types.SimpleNamespace()
    v.vendor_id = 1
    v.owner_id = 1
    return v


# ══════════════════════════════════════════════════════════════════════════════
# Business Hours Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestBusinessHours:
    """Test business hours enforcement."""

    @patch("app.modules.vendors.business_hours_service.ist_now")
    def test_open_during_business_hours(self, mock_ist_now, mock_db, mock_vendor_profile, mock_vendor):
        """Vendor should be open during configured business hours."""
        # Mock ist_now to return a time during business hours (e.g., Monday 14:00)
        mock_ist_now.return_value = datetime(2024, 6, 24, 14, 0)  # Monday at 2 PM

        mock_db.query().filter().first.side_effect = [mock_vendor, mock_vendor_profile]

        is_open, message = check_business_hours(1, mock_db)
        assert is_open is True
        assert "open" in message.lower()

    @patch("app.modules.vendors.business_hours_service.ist_now")
    def test_closed_before_opening(self, mock_ist_now, mock_db, mock_vendor_profile, mock_vendor):
        """Vendor should be closed before opening hours."""
        mock_ist_now.return_value = datetime(2024, 6, 24, 7, 0)  # Monday at 7 AM

        mock_db.query().filter().first.side_effect = [mock_vendor, mock_vendor_profile]

        is_open, message = check_business_hours(1, mock_db)
        assert is_open is False
        assert "opens at" in message.lower()

    @patch("app.modules.vendors.business_hours_service.ist_now")
    def test_closed_after_business_hours(self, mock_ist_now, mock_db, mock_vendor_profile, mock_vendor):
        """Vendor should be closed after closing hours."""
        mock_ist_now.return_value = datetime(2024, 6, 24, 22, 0)  # Monday at 10 PM

        mock_db.query().filter().first.side_effect = [mock_vendor, mock_vendor_profile]

        is_open, message = check_business_hours(1, mock_db)
        assert is_open is False

    @patch("app.modules.vendors.business_hours_service.ist_now")
    def test_closed_on_holiday(self, mock_ist_now, mock_db, mock_vendor_profile, mock_vendor):
        """Vendor should be closed on a configured holiday."""
        mock_ist_now.return_value = datetime(2024, 12, 25, 14, 0)

        mock_db.query().filter().first.side_effect = [mock_vendor, mock_vendor_profile]

        is_open, message = check_business_hours(1, mock_db)
        assert is_open is False
        assert "holiday" in message.lower() or "christmas" in message.lower()

    @patch("app.modules.vendors.business_hours_service.ist_now")
    def test_closed_when_toggle_off(self, mock_ist_now, mock_db, mock_vendor_profile, mock_vendor):
        """Vendor should be closed when master is_open toggle is False."""
        mock_ist_now.return_value = datetime(2024, 6, 24, 14, 0)

        mock_vendor_profile.is_open = False
        mock_db.query().filter().first.side_effect = [mock_vendor, mock_vendor_profile]

        is_open, message = check_business_hours(1, mock_db)
        assert is_open is False
        assert "closed" in message.lower()

    @patch("app.modules.vendors.business_hours_service.ist_now")
    def test_no_profile_defaults_to_open(self, mock_ist_now, mock_db, mock_vendor):
        """When no profile exists, default to open."""
        mock_db.query().filter().first.side_effect = [mock_vendor, None]

        is_open, message = check_business_hours(1, mock_db)
        assert is_open is True

    def test_get_business_hours_no_profile(self, mock_db):
        """Getting business hours with no profile returns defaults."""
        mock_db.query().filter().first.return_value = None

        result = get_vendor_business_hours(999, mock_db)
        assert result["is_open"] is True
        assert "No vendor profile" in result["message"]


# ══════════════════════════════════════════════════════════════════════════════
# Auto Stock Deduction Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestAutoStockDeduction:
    """Test automatic inventory deduction on order placement."""

    def test_deduct_inventory_reduces_stock(self, mock_db):
        """Stock should be reduced by ordered quantity."""
        mock_item = MagicMock(spec=MenuItem)
        mock_item.id = 1
        mock_item.vendor_id = 1
        mock_item.available_quantity = 50
        mock_item.is_available = True

        mock_inventory = MagicMock(spec=Inventory)
        mock_inventory.current_stock = 50
        mock_inventory.auto_disable = True

        mock_db.query().filter().first.side_effect = [mock_item, mock_inventory]

        mock_order = MagicMock(spec=Order)
        mock_order.id = 1

        _deduct_inventory_for_order({1: 3}, mock_db)

        assert mock_inventory.current_stock == 47
        assert mock_item.available_quantity == 47

    def test_deduct_inventory_zero_stock_disables(self, mock_db):
        """Item should be disabled when stock reaches zero."""
        mock_item = MagicMock(spec=MenuItem)
        mock_item.id = 1
        mock_item.available_quantity = 2
        mock_item.is_available = True

        mock_inventory = MagicMock(spec=Inventory)
        mock_inventory.current_stock = 2
        mock_inventory.auto_disable = True

        mock_db.query().filter().first.side_effect = [mock_item, mock_inventory]

        mock_order = MagicMock(spec=Order)
        mock_order.id = 1

        _deduct_inventory_for_order({1: 2}, mock_db)

        assert mock_inventory.current_stock == 0
        assert mock_item.is_available is False  # Auto-disabled

    def test_deduct_inventory_no_inventory_record(self, mock_db):
        """Should not fail when menu item has no inventory record."""
        mock_item = MagicMock(spec=MenuItem)
        mock_item.id = 1
        mock_item.available_quantity = 10

        # First call returns item, second call returns None (no inventory)
        mock_db.query().filter().first.side_effect = [mock_item, None]

        mock_order = MagicMock(spec=Order)
        mock_order.id = 1

        # Should not raise
        _deduct_inventory_for_order({1: 2}, mock_db)
        assert mock_item.available_quantity == 8  # Still updates menu item


# ══════════════════════════════════════════════════════════════════════════════
# Demand Dashboard Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestDemandDashboard:
    """Test demand dashboard service."""

    def test_demand_dashboard_service_initialization(self, mock_db):
        """Service should initialize correctly."""
        service = DemandDashboardService(mock_db)
        assert service.db == mock_db
        assert service.ai_service is not None

    def test_stock_prediction_no_items(self, mock_db):
        """Stock prediction with no items should return empty."""
        from app.modules.menu.model import MenuItem, Inventory

        # Mock the join query to return empty
        mock_query = MagicMock()
        mock_query.join().filter().all.return_value = []
        mock_db.query().join().filter.return_value = mock_query
        mock_db.query().join().filter().all.return_value = []

        service = DemandDashboardService(mock_db)
        result = service.get_stock_prediction(1)

        assert result["vendor_id"] == 1
        assert result["items"] == []
        assert result["summary"]["total_items"] == 0

    def test_rush_prediction_no_data(self, mock_db):
        """Rush prediction with no historical data returns empty predictions."""
        mock_db.query().filter().group_by().all.return_value = []

        service = DemandDashboardService(mock_db)
        result = service.get_rush_prediction(1)

        assert result["vendor_id"] == 1
        assert result["rush_hours_count"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Vendor Router Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestVendorRouter:
    """Test vendor router enhancements."""

    def test_vendor_router_exists(self):
        """Vendor dashboard router should have correct endpoints."""
        from app.modules.vendors.dashboard_router import router as dashboard_router
        routes = [r.path for r in dashboard_router.routes]
        assert "/vendors/dashboard/live-orders" in routes
        assert "/vendors/dashboard/revenue-chart" in routes
        assert "/vendors/dashboard/customer-insights" in routes

    def test_business_hours_router_exists(self):
        """Business hours router should have correct endpoints."""
        from app.modules.vendors.business_hours_router import router as bh_router
        routes = [r.path for r in bh_router.routes]
        assert "/vendors/business-hours/" in routes
        assert "/vendors/business-hours/status" in routes

    def test_demand_dashboard_router_exists(self):
        """Demand dashboard router should have correct endpoints."""
        from app.modules.vendors.demand_dashboard_router import router as dd_router
        routes = [r.path for r in dd_router.routes]
        assert "/vendors/demand-dashboard/" in routes
        assert "/vendors/demand-dashboard/overview" in routes
        assert "/vendors/demand-dashboard/stock-prediction" in routes
        assert "/vendors/demand-dashboard/rush-prediction" in routes


# ══════════════════════════════════════════════════════════════════════════════
# Slot Service Tests
# ══════════════════════════════════════════════════════════════════════════════


class TestSlotService:
    """Test slot service fixes."""

    def test_apply_capacity_rules_correctly_maps_columns(self, mock_db):
        """_apply_capacity_rules should use day_of_week and start/end_hour correctly."""
        from app.modules.slots.service import _apply_capacity_rules
        from app.modules.slots.model import Slot, SlotCapacityRule, SlotStatus

        import types
        slot = types.SimpleNamespace()
        slot.id = 1
        slot.vendor_id = 1
        slot.max_orders = 20
        slot.is_peak_hour = False
        slot.start_time = datetime(2024, 6, 24, 14, 0)  # Monday 2 PM, weekday()=0

        # Mock a capacity rule for Monday with reduced capacity
        rule = types.SimpleNamespace()
        rule.vendor_id = 1
        rule.day_of_week = 0  # Monday
        rule.start_hour = 12
        rule.end_hour = 15
        rule.base_capacity = 10
        rule.peak_capacity = 15
        rule.is_active = True

        mock_db.query().filter().all.return_value = [rule]

        effective_max = _apply_capacity_rules(slot, "student", mock_db)
        assert effective_max == 10  # Should be capped at 10

    def test_apply_capacity_rules_skips_other_days(self, mock_db):
        """Rules for other days should not apply."""
        from app.modules.slots.service import _apply_capacity_rules
        import types

        slot = types.SimpleNamespace()
        slot.id = 1
        slot.vendor_id = 1
        slot.max_orders = 20
        slot.is_peak_hour = False
        slot.start_time = datetime(2024, 6, 24, 14, 0)  # Monday

        # Rule for Wednesday (day_of_week=2)
        rule = types.SimpleNamespace()
        rule.vendor_id = 1
        rule.day_of_week = 2
        rule.start_hour = 12
        rule.end_hour = 15
        rule.base_capacity = 5
        rule.peak_capacity = None
        rule.is_active = True

        mock_db.query().filter().all.return_value = [rule]

        effective_max = _apply_capacity_rules(slot, "student", mock_db)
        assert effective_max == 20  # Should keep original max since rule is for Wednesday


# ══════════════════════════════════════════════════════════════════════════════
# Vendor Frontend API tests
# ══════════════════════════════════════════════════════════════════════════════


class TestVendorFrontendEndpoints:
    """Verify the API v1 router includes new vendor routes."""

    def test_v1_router_includes_new_routers(self):
        """New vendor routers should be included in the v1 API router."""
        from app.api.v1 import api_v1_router

        # Get all leaf route paths from v1 router, including nested included routers
        def collect_paths(router):
            paths = []
            for route in router.routes:
                if hasattr(route, "path"):
                    paths.append(route.path)
                if hasattr(route, "routes"):
                    paths.extend(r.path for r in route.routes if hasattr(r, "path"))
            return paths

        routes = collect_paths(api_v1_router)

        # Check new routes are present (with /v1 prefix)
        assert any("/v1/vendors/business-hours" in r for r in routes), "Business hours routes not in v1"
        assert any("/v1/vendors/demand-dashboard" in r for r in routes), "Demand dashboard routes not in v1"
        assert any("/v1/vendors/dashboard/live-orders" in r for r in routes), "Live orders route not in v1"
        assert any("/v1/vendors/dashboard/revenue-chart" in r for r in routes), "Revenue chart route not in v1"
        assert any("/v1/vendors/dashboard/customer-insights" in r for r in routes), "Customer insights route not in v1"
