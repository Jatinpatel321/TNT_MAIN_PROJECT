import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.orders.model import Order, OrderStatus
from app.modules.payments.reconciliation_service import reconcile_stuck_payments_job


def test_reconcile_stuck_payments_job():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    try:
        old_time = datetime.utcnow() - timedelta(minutes=20)
        
        # Stuck payment without rzp id -> fails & cancels order
        order1 = Order(user_id=1, vendor_id=1, slot_id=1, status=OrderStatus.PLACED, total_amount=100)
        db.add(order1)
        db.flush()
        payment1 = Payment(order_id=order1.id, amount=100, status=PaymentStatus.INITIATED, created_at=old_time)
        db.add(payment1)
        
        # Stuck payment with rzp id -> finalizes
        order2 = Order(user_id=1, vendor_id=1, slot_id=1, status=OrderStatus.PLACED, total_amount=200)
        db.add(order2)
        db.flush()
        payment2 = Payment(order_id=order2.id, amount=200, status=PaymentStatus.INITIATED, razorpay_payment_id="pay_test123", created_at=old_time)
        db.add(payment2)
        
        db.commit()

        results = reconcile_stuck_payments_job(db)
        
        assert results["total_stuck"] >= 2
        assert results["finalized"] >= 1
        assert results["failed"] >= 1

        db.refresh(payment1)
        db.refresh(payment2)
        assert payment1.status == PaymentStatus.FAILED
        assert payment2.status == PaymentStatus.SUCCESS
    finally:
        db.close()
