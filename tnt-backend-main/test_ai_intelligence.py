from datetime import UTC, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.base import Base
from app.modules.group_cart import model as _group_cart_model
from app.modules.ai_intelligence.learning.usage_patterns import UsagePatterns
from app.modules.ai_intelligence.service import AIIntelligenceService
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole


def utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine, testing_session_local()


def _seed_data(db):
    student_1 = User(phone="9110000001", name="Student One", role=UserRole.STUDENT, is_active=True)
    student_2 = User(phone="9110000002", name="Student Two", role=UserRole.STUDENT, is_active=True)
    vendor_food = User(
        phone="9110000010",
        name="Food Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_active=True,
        is_approved=True,
    )
    vendor_stationery = User(
        phone="9110000011",
        name="Stationery Vendor",
        role=UserRole.VENDOR,
        vendor_type="stationery",
        is_active=True,
        is_approved=True,
    )

    db.add_all([student_1, student_2, vendor_food, vendor_stationery])
    db.commit()
    db.refresh(student_1)
    db.refresh(student_2)
    db.refresh(vendor_food)
    db.refresh(vendor_stationery)

    slot_overlap = Slot(
        vendor_id=vendor_food.id,
        start_time=utcnow_naive().replace(hour=13, minute=0, second=0, microsecond=0),
        end_time=utcnow_naive().replace(hour=13, minute=30, second=0, microsecond=0),
        max_orders=10,
        current_orders=3,
        status=SlotStatus.AVAILABLE,
    )
    db.add(slot_overlap)
    db.commit()
    db.refresh(slot_overlap)

    now = utcnow_naive()
    orders = [
        Order(
            user_id=student_1.id,
            slot_id=slot_overlap.id,
            vendor_id=vendor_food.id,
            status=OrderStatus.COMPLETED,
            total_amount=200,
            created_at=now.replace(hour=13, minute=5, second=0, microsecond=0),
            pickup_confirmed_at=now.replace(hour=13, minute=20, second=0, microsecond=0),
        ),
        Order(
            user_id=student_1.id,
            slot_id=slot_overlap.id,
            vendor_id=vendor_stationery.id,
            status=OrderStatus.COMPLETED,
            total_amount=100,
            created_at=now.replace(hour=13, minute=10, second=0, microsecond=0),
            pickup_confirmed_at=now.replace(hour=13, minute=25, second=0, microsecond=0),
        ),
        Order(
            user_id=student_2.id,
            slot_id=slot_overlap.id,
            vendor_id=vendor_food.id,
            status=OrderStatus.CONFIRMED,
            total_amount=150,
            created_at=now.replace(hour=13, minute=15, second=0, microsecond=0),
        ),
    ]

    db.add_all(orders)
    db.commit()

    return {
        "student_1": student_1,
        "student_2": student_2,
        "slot": slot_overlap,
        "vendor_food": vendor_food,
        "vendor_stationery": vendor_stationery,
    }


def test_group_coordination_returns_overlap_and_slot_suggestion():
    engine, db = _build_session()
    try:
        seed = _seed_data(db)
        service = AIIntelligenceService(db)

        result = service.get_group_coordination([seed["student_1"].id, seed["student_2"].id])

        assert result.overlapping_windows
        assert result.suggested_unified_slot == seed["slot"].id
        assert result.coordination_score > 0
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_usage_patterns_spending_and_category_are_data_backed():
    engine, db = _build_session()
    try:
        seed = _seed_data(db)
        patterns = UsagePatterns(db).analyze_user_patterns(seed["student_1"].id)

        spending = patterns["spending_patterns"]
        assert spending["avg_order_value"] == 150.0
        assert spending["total_spent"] == 300.0
        assert spending["spending_category"] == "medium"

        categories = patterns["category_preferences"]
        assert categories["preferred_category"] == "food"
        assert categories["category_distribution"]["food"] == 0.5
        assert categories["category_distribution"]["stationery"] == 0.5
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_system_patterns_use_live_vendor_category_and_trends():
    engine, db = _build_session()
    try:
        seed = _seed_data(db)
        patterns = UsagePatterns(db).analyze_system_patterns()

        popular = patterns["popular_categories"]
        assert popular["food_orders"] == 2
        assert popular["stationery_orders"] == 1
        assert popular["trending_category"] == "food"

        trends = patterns["vendor_performance_trends"]
        trend_vendor_ids = {row["vendor_id"] for row in trends}
        assert seed["vendor_food"].id in trend_vendor_ids
        assert seed["vendor_stationery"].id in trend_vendor_ids
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
