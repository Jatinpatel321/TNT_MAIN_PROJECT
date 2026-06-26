"""Tests for AI Services API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.core.security import create_access_token


class TestAIServicesAPI:
    """Test AI services endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999001", role=UserRole.VENDOR, is_verified=True)
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

    def _get_auth_header(self, vendor_id: int) -> dict:
        """Helper to create auth header."""
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_capacity_recommendations(self, client: TestClient, db: Session):
        """Test capacity recommendations endpoint."""
        vendor = self._create_vendor(db)
        response = client.get(
            "/v1/vendors/ai/capacity-recommendations",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "current_capacity" in data
        assert "suggested_capacity" in data

    def test_rush_prediction(self, client: TestClient, db: Session):
        """Test rush prediction endpoint."""
        vendor = self._create_vendor(db)
        response = client.get(
            "/v1/vendors/ai/rush-prediction",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "confidence" in data
        assert "peak_hours" in data

    def test_throughput_prediction(self, client: TestClient, db: Session):
        """Test throughput prediction endpoint."""
        vendor = self._create_vendor(db)
        response = client.get(
            "/v1/vendors/ai/throughput-prediction",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "current_throughput" in data
        assert "predicted_throughput" in data

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access to AI endpoints."""
        response = client.get("/v1/vendors/ai/capacity-recommendations")
        assert response.status_code == 401

        response = client.get("/v1/vendors/ai/rush-prediction")
        assert response.status_code == 401

        response = client.get("/v1/vendors/ai/throughput-prediction")
        assert response.status_code == 401

    def test_ai_response_structure(self, client: TestClient, db: Session):
        """Test AI response has proper structure."""
        vendor = self._create_vendor(db)

        # Test capacity recommendations structure
        response = client.get(
            "/v1/vendors/ai/capacity-recommendations",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_ai_with_no_historical_data(self, client: TestClient, db: Session):
        """Test AI endpoints with no historical data."""
        user = User(phone="+919999999002", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="No Data Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        # Should still return valid response even with no data
        response = client.get(
            "/v1/vendors/ai/capacity-recommendations",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

        response = client.get(
            "/v1/vendors/ai/rush-prediction",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

        response = client.get(
            "/v1/vendors/ai/throughput-prediction",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200


class TestAIServiceModel:
    """Test AI service models and logic."""

    def test_capacity_calculation(self, db: Session):
        """Test capacity calculation logic."""
        from app.modules.vendors.vendor_ai_service import calculate_capacity_recommendation

        # Test with mock data
        result = calculate_capacity_recommendation(
            current_capacity=10,
            avg_orders_per_day=50,
            peak_hours=2,
        )

        assert "recommended_capacity" in result
        assert "reason" in result
        assert isinstance(result["recommended_capacity"], int)

    def test_rush_prediction_logic(self, db: Session):
        """Test rush prediction logic."""
        from app.modules.vendors.vendor_ai_service import predict_rush_hours

        # Test with mock historical data
        historical_data = [
            {"hour": 9, "orders": 10},
            {"hour": 10, "orders": 25},
            {"hour": 11, "orders": 30},
            {"hour": 12, "orders": 45},
            {"hour": 13, "orders": 40},
        ]

        result = predict_rush_hours(historical_data)

        assert "peak_hours" in result
        assert "confidence" in result
        assert isinstance(result["peak_hours"], list)

    def test_throughput_calculation(self, db: Session):
        """Test throughput calculation logic."""
        from app.modules.vendors.vendor_ai_service import calculate_throughput

        # Test with mock data
        result = calculate_throughput(
            orders_per_hour=15,
            avg_prep_time=10,
            staff_count=2,
        )

        assert "throughput" in result
        assert "efficiency" in result
        assert isinstance(result["throughput"], (int, float))