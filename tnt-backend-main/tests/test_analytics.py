"""Tests for Analytics API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.menu.model import MenuItem
from app.core.security import create_access_token


class TestAnalyticsAPI:
    """Test analytics endpoints."""

    def _create_vendor_with_orders(self, db: Session) -> Vendor:
        """Helper to create vendor with sample orders."""
        user = User(phone="+919999999201", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Analytics Test Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        # Create menu items
        for i in range(3):
            item = MenuItem(
                vendor_id=vendor.vendor_id,
                name=f"Item {i}",
                description=f"Description {i}",
                price=100 + i * 50,
                category="main",
                is_available=True,
                preparation_time=10,
            )
            db.add(item)
        db.commit()

        # Create orders
        for i in range(5):
            order = Order(
                vendor_id=vendor.vendor_id,
                user_id=user.id,
                total_amount=100 + i * 50,
                status=OrderStatus.COMPLETED,
            )
            db.add(order)
            db.commit()
            db.refresh(order)

            # Add payment
            payment = Payment(
                order_id=order.id,
                amount=order.total_amount * 100,
                status=PaymentStatus.SUCCESS,
                razorpay_payment_id=f"pay_{100000 + i}",
            )
            db.add(payment)

        db.commit()
        return vendor

    def _get_auth_header(self, vendor_id: int) -> dict:
        """Helper to create auth header."""
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_get_daily_sales(self, client: TestClient, db: Session):
        """Test getting daily sales."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/daily?days=7",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "sales_data" in data
        assert "total_revenue" in data
        assert "total_orders" in data

    def test_get_weekly_sales(self, client: TestClient, db: Session):
        """Test getting weekly sales."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/weekly?weeks=4",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "weekly_data" in data
        assert "total_revenue" in data
        assert "growth_percentage" in data

    def test_get_monthly_sales(self, client: TestClient, db: Session):
        """Test getting monthly sales."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/monthly?months=6",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "monthly_data" in data
        assert "total_revenue" in data

    def test_get_yearly_sales(self, client: TestClient, db: Session):
        """Test getting yearly sales."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/yearly",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "yearly_data" in data

    def test_get_peak_hours(self, client: TestClient, db: Session):
        """Test getting peak hours analysis."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/peak-hours",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "hourly_distribution" in data
        assert "peak_periods" in data

    def test_get_item_analysis(self, client: TestClient, db: Session):
        """Test getting item analysis."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/items",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "popular_items" in data
        assert "low_selling_items" in data

    def test_get_waste_analysis(self, client: TestClient, db: Session):
        """Test getting waste analysis."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/waste",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "cancellation_rate" in data
        assert "wasted_revenue" in data
        assert "cancelled_orders" in data

    def test_get_revenue_trends(self, client: TestClient, db: Session):
        """Test getting revenue trends."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/revenue-trends",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "daily_average_revenue" in data["summary"]
        assert "weekly_growth" in data["summary"]

    def test_export_csv_daily(self, client: TestClient, db: Session):
        """Test exporting daily report as CSV."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/export/csv/daily",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_export_csv_weekly(self, client: TestClient, db: Session):
        """Test exporting weekly report as CSV."""
        vendor = self._create_vendor_with_orders(db)
        response = client.get(
            "/v1/vendors/analytics/export/csv/weekly",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access."""
        response = client.get("/v1/vendors/analytics/daily")
        assert response.status_code == 401

    def test_analytics_with_no_orders(self, client: TestClient, db: Session):
        """Test analytics with no orders returns empty data."""
        user = User(phone="+919999999202", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="No Orders Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        response = client.get(
            "/v1/vendors/analytics/daily?days=7",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_revenue"] == 0
        assert data["total_orders"] == 0


class TestAnalyticsModel:
    """Test analytics-related models."""

    def test_order_with_payment(self, db: Session):
        """Test order and payment relationship."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999203", role=UserRole.VENDOR, is_verified=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=user.id,
            total_amount=200,
            status=OrderStatus.COMPLETED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        payment = Payment(
            order_id=order.id,
            amount=20000,  # paise
            status=PaymentStatus.SUCCESS,
            razorpay_payment_id="pay_test123",
        )
        db.add(payment)
        db.commit()

        assert order.id is not None
        assert payment.order_id == order.id
        assert payment.status == PaymentStatus.SUCCESS