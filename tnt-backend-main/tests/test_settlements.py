"""Tests for Settlements API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.users.model import User, UserRole
from app.modules.vendors.model import Vendor, VendorStatus
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.vendors.settlement_models import VendorWallet, VendorTransaction, VendorSettlement
from app.core.security import create_access_token


class TestSettlementsAPI:
    """Test settlement endpoints."""

    def _create_vendor_with_payments(self, db: Session) -> Vendor:
        """Helper to create vendor with payments."""
        user = User(phone="+919999999101", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Settlement Test Shop",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        # Create orders and payments
        for i in range(3):
            order = Order(
                vendor_id=vendor.vendor_id,
                user_id=user.id,
                total_amount=100 + i * 50,
                status=OrderStatus.COMPLETED,
            )
            db.add(order)
            db.commit()
            db.refresh(order)

            payment = Payment(
                order_id=order.id,
                amount=order.total_amount * 100,
                status=PaymentStatus.SUCCESS,
                razorpay_payment_id=f"pay_{200000 + i}",
            )
            db.add(payment)

        db.commit()
        return vendor

    def _get_auth_header(self, vendor_id: int) -> dict:
        """Helper to create auth header."""
        token = create_access_token(vendor_id, "vendor_owner")
        return {"Authorization": f"Bearer {token}"}

    def test_get_revenue_summary(self, client: TestClient, db: Session):
        """Test getting revenue summary."""
        vendor = self._create_vendor_with_payments(db)
        response = client.get(
            "/v1/vendors/settlement/revenue",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "wallet" in data
        assert "today" in data
        assert "breakdown" in data
        assert "total_earned" in data["wallet"]
        assert "current_balance" in data["wallet"]

    def test_get_transactions(self, client: TestClient, db: Session):
        """Test getting transactions."""
        vendor = self._create_vendor_with_payments(db)
        response = client.get(
            "/v1/vendors/settlement/transactions?days=30",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "transactions" in data
        assert "summary" in data
        assert "total_online" in data["summary"]
        assert "total_cash" in data["summary"]

    def test_get_settlements(self, client: TestClient, db: Session):
        """Test getting settlements."""
        vendor = self._create_vendor_with_payments(db)

        # Create wallet
        wallet = VendorWallet(
            vendor_id=vendor.vendor_id,
            total_earned=1000.0,
            total_pending=300.0,
            total_settled=700.0,
            total_refunded=50.0,
            balance=950.0,
        )
        db.add(wallet)

        # Create settlement
        settlement = VendorSettlement(
            vendor_id=vendor.vendor_id,
            period_start="2024-01-01",
            period_end="2024-01-31",
            total_amount=5000.0,
            total_fees=100.0,
            net_amount=4900.0,
            order_count=50,
            online_payments=3000.0,
            cash_orders=2000.0,
            refunds=100.0,
            status="completed",
        )
        db.add(settlement)
        db.commit()

        response = client.get(
            "/v1/vendors/settlement/settlements",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "wallet" in data
        assert "pending_settlement" in data
        assert "settlements" in data
        assert len(data["settlements"]) == 1

    def test_get_refunds(self, client: TestClient, db: Session):
        """Test getting refunds."""
        vendor = self._create_vendor_with_payments(db)

        # Create refunded payment
        order = Order(
            vendor_id=vendor.vendor_id,
            user_id=vendor.owner_id,
            total_amount=200,
            status=OrderStatus.COMPLETED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        payment = Payment(
            order_id=order.id,
            amount=20000,
            status=PaymentStatus.REFUNDED,
            razorpay_payment_id="pay_refund_test",
            razorpay_refund_id="refund_123",
        )
        db.add(payment)
        db.commit()

        response = client.get(
            "/v1/vendors/settlement/refunds",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_refunds" in data
        assert "total_refunded_amount" in data
        assert "refunds" in data
        assert "monthly_refunds" in data

    def test_get_daily_revenue(self, client: TestClient, db: Session):
        """Test getting daily revenue."""
        vendor = self._create_vendor_with_payments(db)
        response = client.get(
            "/v1/vendors/settlement/daily-revenue?days=7",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "daily_revenue" in data
        assert "total_online" in data
        assert "total_cash" in data
        assert "total_net" in data
        assert len(data["daily_revenue"]) == 7

    def test_unauthorized_access(self, client: TestClient):
        """Test unauthorized access."""
        response = client.get("/v1/vendors/settlement/revenue")
        assert response.status_code == 401

        response = client.get("/v1/vendors/settlement/transactions")
        assert response.status_code == 401

    def test_wallet_auto_creation(self, client: TestClient, db: Session):
        """Test wallet is auto-created on first access."""
        user = User(phone="+919999999102", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Auto Wallet Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()

        # Access revenue endpoint - should create wallet
        response = client.get(
            "/v1/vendors/settlement/revenue",
            headers=self._get_auth_header(vendor.vendor_id),
        )
        assert response.status_code == 200
        data = response.json()
        assert "wallet" in data

        # Verify wallet was created
        wallet = db.query(VendorWallet).filter(VendorWallet.vendor_id == vendor.vendor_id).first()
        assert wallet is not None


class TestSettlementModels:
    """Test settlement models."""

    def test_create_wallet(self, db: Session):
        """Test creating vendor wallet."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999103", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Wallet Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        wallet = VendorWallet(
            vendor_id=vendor.vendor_id,
            total_earned=5000.0,
            total_pending=1500.0,
            total_settled=3500.0,
            total_refunded=200.0,
            balance=4800.0,
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

        assert wallet.id is not None
        assert wallet.vendor_id == vendor.vendor_id
        assert wallet.total_earned == 5000.0
        assert wallet.balance == 4800.0

    def test_create_transaction(self, db: Session):
        """Test creating vendor transaction."""
        from app.modules.users.model import User, UserRole
        from app.modules.vendors.model import Vendor, VendorStatus

        user = User(phone="+919999999104", role=UserRole.VENDOR, is_active=True)
        db.add(user)
        db.commit()

        vendor = Vendor(
            vendor_name="Transaction Model Test",
            category="food",
            owner_id=user.id,
            password_hash=Vendor.hash_password("pass"),
            status=VendorStatus.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        transaction = VendorTransaction(
            vendor_id=vendor.vendor_id,
            order_id=1,
            transaction_type="online_payment",
            amount=500.0,
            fee=10.0,
            net_amount=490.0,
            description="Test transaction",
            payment_method="online",
            is_online=True,
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        assert transaction.id is not None
        assert transaction.vendor_id == vendor.vendor_id
        assert transaction.amount == 500.0
        assert transaction.fee == 10.0
