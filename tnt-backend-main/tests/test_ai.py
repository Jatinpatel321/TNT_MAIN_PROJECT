"""Tests for Vendor AI Services API endpoints."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.vendors.auth_service import _create_access_token as create_access_token
from app.modules.vendors.vendor_ai_service import VendorAIService


class TestAIServicesAPI:
    """Test AI services endpoints."""

    def _create_vendor(self, db: Session, phone: str = "+919999999001") -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone=phone, role=UserRole.VENDOR, is_active=True, is_approved=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="AI Test Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)
        return vendor

    def _seed_orders(self, db: Session, owner_id: int, count: int = 5) -> None:
        start = utcnow_naive() + timedelta(hours=1)
        slot = Slot(
            vendor_id=owner_id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            max_orders=50,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)
        for i in range(count):
            db.add(
                Order(
                    vendor_id=owner_id,
                    user_id=owner_id,
                    slot_id=slot.id,
                    total_amount=100 + i * 10,
                    status=OrderStatus.PICKED,
                )
            )
        db.commit()

    def _get_auth_header(self, vendor_id: int) -> dict:
        """Helper to create auth header."""
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_capacity_recommendations(self, client: TestClient, db: Session):
        """Daily forecast carries the capacity recommendation."""
        vendor = self._create_vendor(db)
        self._seed_orders(db, vendor.owner_id)
        response = client.get(
            "/v1/vendors/ai/forecast/daily",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "forecast" in data
        assert "daily_average" in data
        assert "recommendation" in data

    def test_rush_prediction(self, client: TestClient, db: Session):
        """Peak-times endpoint predicts rush hours."""
        vendor = self._create_vendor(db)
        self._seed_orders(db, vendor.owner_id)
        response = client.get(
            "/v1/vendors/ai/peak-times",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "peak_hours" in data
        assert "busiest_hour" in data
        assert "peak_periods" in data

    def test_throughput_prediction(self, client: TestClient, db: Session):
        """Workload endpoint returns throughput/peak prediction by vendor type."""
        vendor = self._create_vendor(db)
        self._seed_orders(db, vendor.owner_id)
        response = client.get(
            "/v1/vendors/ai/workload",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        # Food vendors get the peak-time prediction shape
        assert "peak_hours" in data

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to AI endpoints."""
        for path in (
            "/v1/vendors/ai/forecast/daily",
            "/v1/vendors/ai/peak-times",
            "/v1/vendors/ai/workload",
            "/v1/vendors/ai/dashboard",
        ):
            response = client.get(path)
            assert response.status_code in (401, 403), path

    def test_ai_response_structure(self, client: TestClient, db: Session):
        """Test the AI dashboard aggregates every sub-report."""
        from unittest.mock import patch

        vendor = self._create_vendor(db)
        self._seed_orders(db, vendor.owner_id)

        # Weekly/monthly forecasts use Postgres-only date_trunc; stub them on
        # SQLite while every other dashboard section runs real code.
        with patch.object(
            VendorAIService,
            "get_weekly_forecast",
            return_value={"forecast": [], "trend_direction": "stable"},
        ), patch.object(
            VendorAIService, "get_monthly_forecast", return_value={"forecast": []}
        ):
            response = client.get(
                "/v1/vendors/ai/dashboard",
                headers=self._get_auth_header(vendor.vendor_id),
            )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        for key in (
            "daily_forecast",
            "weekly_forecast",
            "monthly_forecast",
            "popular_items",
            "peak_times",
            "waste_insights",
            "inventory_suggestions",
            "recommendations",
        ):
            assert key in data, f"Missing dashboard key: {key}"
        assert isinstance(data["recommendations"], list)

    def test_ai_with_no_historical_data(self, client: TestClient, db: Session):
        """Test AI endpoints with no historical data."""
        vendor = self._create_vendor(db, phone="+919999999002")

        # Should still return valid responses even with no data
        for path in (
            "/v1/vendors/ai/forecast/daily",
            "/v1/vendors/ai/peak-times",
            "/v1/vendors/ai/workload",
        ):
            response = client.get(
                path,
                headers=self._get_auth_header(vendor.vendor_id),
            )
            assert response.status_code == 200, path


class TestAIServiceModel:
    """Test AI service logic directly."""

    def _make_owner(self, db: Session, phone: str) -> User:
        user = User(phone=phone, role=UserRole.VENDOR, is_active=True, is_approved=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_capacity_calculation(self, db: Session):
        """Capacity recommendation scales with daily average volume."""
        service = VendorAIService(db)

        assert service._get_capacity_recommendation(60) == "Increase capacity"
        assert service._get_capacity_recommendation(30) == "Maintain current capacity"
        low = service._get_capacity_recommendation(5)
        assert isinstance(low, str) and low  # some guidance is always returned

    def test_rush_prediction_logic(self, db: Session):
        """Peak-time prediction marks high-percentage hours as peaks."""
        owner = self._make_owner(db, "+919999999003")

        start = utcnow_naive() + timedelta(hours=1)
        slot = Slot(
            vendor_id=owner.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            max_orders=50,
            current_orders=0,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        db.refresh(slot)

        # Concentrate orders at a single hour so it dominates the distribution
        lunchtime = (utcnow_naive() - timedelta(days=1)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        for _ in range(10):
            db.add(
                Order(
                    vendor_id=owner.id,
                    user_id=owner.id,
                    slot_id=slot.id,
                    total_amount=100,
                    status=OrderStatus.PICKED,
                    created_at=lunchtime,
                )
            )
        db.commit()

        result = VendorAIService(db).get_peak_time_prediction(owner.id)

        assert "peak_hours" in result
        assert isinstance(result["peak_hours"], list)
        assert result["busiest_hour"] == 12

    def test_throughput_calculation(self, db: Session):
        """Daily forecast aggregates predicted volume with confidence."""
        owner = self._make_owner(db, "+919999999004")

        result = VendorAIService(db).get_daily_forecast(owner.id, days=7)

        assert "forecast" in result
        assert len(result["forecast"]) == 7
        assert "total_predicted" in result
        for day in result["forecast"]:
            assert "predicted_orders" in day
            assert "confidence" in day
            assert isinstance(day["predicted_orders"], int)
