"""Tests for Promotions API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.vendors.retention_models import VendorPromotion, VendorLoyaltyProgram
from app.core.security import create_access_token


class TestPromotionsAPI:
    """Test promotions endpoints."""

    def _create_vendor(self, db: Session) -> Vendor:
        """Helper to create a test vendor."""
        user = User(phone="+919999999301", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Promo Test Shop",
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

    def test_create_promotion(self, client: TestClient, db: Session):
        """Test creating promotion."""
        vendor = self._create_vendor(db)
        response = client.post(
            "/v1/vendors/promotions",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "vendor_id": vendor.vendor_id,
                "title": "Test Promotion",
                "description": "Test description",
                "discount_type": "percentage",
                "discount_value": 20,
                "min_order_amount": 100,
                "max_discount": 50,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "is_active": True,
                "usage_limit": 100,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Promotion"
        assert data["discount_value"] == 20

    def test_get_promotions(self, client: TestClient, db: Session):
        """Test getting promotions."""
        vendor = self._create_vendor(db)

        # Create promotions
        for i in range(3):
            promo = VendorPromotion(
                vendor_id=vendor.vendor_id,
                title=f"Promo {i}",
                description=f"Description {i}",
                discount_type="percentage",
                discount_value=10 + i * 5,
                min_order_amount=100,
                max_discount=50,
                start_date="2024-01-01",
                end_date="2024-12-31",
                is_active=True,
                usage_limit=100,
                usage_count=0,
            )
            db.add(promo)
        db.commit()

        response = client.get(
            "/v1/vendors/promotions",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_update_promotion(self, client: TestClient, db: Session):
        """Test updating promotion."""
        vendor = self._create_vendor(db)

        promo = VendorPromotion(
            vendor_id=vendor.vendor_id,
            title="Original Promo",
            description="Original",
            discount_type="percentage",
            discount_value=10,
            min_order_amount=100,
            max_discount=50,
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_active=True,
            usage_limit=100,
            usage_count=0,
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)

        response = client.put(
            f"/v1/vendors/promotions/{promo.id}",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "title": "Updated Promo",
                "discount_value": 25,
                "is_active": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Promo"
        assert data["discount_value"] == 25
        assert data["is_active"] is False

    def test_delete_promotion(self, client: TestClient, db: Session):
        """Test deleting promotion."""
        vendor = self._create_vendor(db)

        promo = VendorPromotion(
            vendor_id=vendor.vendor_id,
            title="To Delete",
            description="Will be deleted",
            discount_type="fixed",
            discount_value=50,
            min_order_amount=200,
            max_discount=50,
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_active=True,
            usage_limit=100,
            usage_count=0,
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)

        response = client.delete(
            f"/v1/vendors/promotions/{promo.id}",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access."""
        response = client.get("/v1/vendors/promotions")
        assert response.status_code == 401

    def test_loyalty_program(self, client: TestClient, db: Session):
        """Test loyalty program."""
        vendor = self._create_vendor(db)

        # Create loyalty program
        response = client.post(
            "/v1/vendors/loyalty",
            headers=self._get_auth_header(vendor.vendor_id),
            json={
                "vendor_id": vendor.vendor_id,
                "program_name": "Test Rewards",
                "points_per_rupee": 1.0,
                "redemption_rate": 0.1,
                "min_points_redemption": 100,
                "is_active": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["program_name"] == "Test Rewards"
        assert data["points_per_rupee"] == 1.0

        # Get loyalty program
        response = client.get(
            "/v1/vendors/loyalty",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        assert response.json()["program_name"] == "Test Rewards"


class TestPromotionModel:
    """Test VendorPromotion model."""

    def test_create_promotion(self, db: Session):
        """Test creating promotion model."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999302", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Promo Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        promo = VendorPromotion(
            vendor_id=vendor.vendor_id,
            title="Test Promo",
            description="Test",
            discount_type="percentage",
            discount_value=20,
            min_order_amount=100,
            max_discount=50,
            start_date="2024-01-01",
            end_date="2024-12-31",
            is_active=True,
            usage_limit=100,
            usage_count=0,
        )
        db.add(promo)
        db.commit()
        db.refresh(promo)

        assert promo.id is not None
        assert promo.vendor_id == vendor.vendor_id
        assert promo.discount_value == 20
        assert promo.is_active is True
