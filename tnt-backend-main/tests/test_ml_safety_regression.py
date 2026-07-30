"""
Regression tests enforcing safe ML behavior and fallback guarantees until data is sufficient:
1. ETA model gate: vendors below historical-order threshold (<30) use heuristic.
2. Demand model gate: vendors without enough history (<90 days) use heuristic.
3. Slot safety: slots >= 90% capacity are excluded even if model recommends them.
4. Vendor ranking: express pickup eligibility is a hard rule independent of ML score.
5. Fraud detection: deterministic rules trigger regardless of ML model state/confidence.
6. Payload metadata: response objects include source/method fields.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.ai_intelligence.ml_bridge import predict_with_fallback
from app.modules.ai_intelligence.planners.demand_planner import DemandPlanner
from app.modules.ai_intelligence.planners.eta_engine import ETAEngine
from app.modules.ai_intelligence.planners.slot_planner import SlotPlanner
from app.modules.ai_intelligence.planners.vendor_ranker import VendorRanker
from app.modules.fraud.fraud_detection_service import FraudDetectionService
from app.modules.fraud.fraud_rules import (
    check_rapid_multi_vendor,
    check_slot_hoarding,
    check_value_outlier,
    run_fraud_checks,
)
from app.modules.orders.model import Order, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

NOW = datetime(2024, 6, 15, 12, 0, 0)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Helper Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_vendor(db_session: Session) -> User:
    vendor = User(
        phone=f"+1555{_uid()[:7]}",
        name="Regression Test Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_approved=True,
    )
    db_session.add(vendor)
    db_session.commit()
    return vendor


@pytest.fixture
def sample_user(db_session: Session) -> User:
    user = User(
        phone=f"+1666{_uid()[:7]}",
        name="Regression Test Student",
        role=UserRole.STUDENT,
        vendor_type="food",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_slot(db_session: Session, sample_vendor: User) -> Slot:
    slot = Slot(
        vendor_id=sample_vendor.id,
        start_time=NOW + timedelta(hours=1),
        end_time=NOW + timedelta(hours=2),
        max_orders=20,
        current_orders=2,
        status="available",
    )
    db_session.add(slot)
    db_session.commit()
    return slot


# ===========================================================================
# 1. ETA Model Gate Tests
# ===========================================================================

class TestETAModelGate:

    def test_vendor_below_order_threshold_uses_heuristic(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        """Vendors with < 30 historical orders MUST use heuristic calculation."""
        # Seed 10 completed orders (< 30 threshold)
        for i in range(10):
            order = Order(
                user_id=sample_vendor.id,
                vendor_id=sample_vendor.id,
                slot_id=sample_slot.id,
                status=OrderStatus.COMPLETED,
                total_amount=15.0,
                eta_minutes=12,
                created_at=NOW - timedelta(days=i + 1),
            )
            db_session.add(order)

        db_session.commit()

        engine = ETAEngine(db_session)
        with patch("app.modules.ai_intelligence.planners.eta_engine.utcnow_naive", return_value=NOW):
            result = engine.predict_eta(sample_slot.id, sample_vendor.id)

        assert result["source"] == "heuristic"
        assert "predicted_eta_minutes" in result
        assert 5 <= result["predicted_eta_minutes"] <= 60

    def test_vendor_above_order_threshold_attempts_model(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        """Vendors with >= 30 historical orders proceed to model evaluation."""
        # Seed 35 completed orders (>= 30 threshold)
        for i in range(35):
            order = Order(
                user_id=sample_vendor.id,
                vendor_id=sample_vendor.id,
                slot_id=sample_slot.id,
                status=OrderStatus.COMPLETED,
                total_amount=15.0,
                eta_minutes=15,
                created_at=NOW - timedelta(days=(i % 25) + 1),
            )
            db_session.add(order)

        db_session.commit()

        engine = ETAEngine(db_session)
        with patch("app.modules.ai_intelligence.planners.eta_engine.utcnow_naive", return_value=NOW), \
             patch("app.modules.ai_intelligence.planners.eta_engine.predict_with_fallback", return_value=(18.0, "model")) as mock_bridge:

            result = engine.predict_eta(sample_slot.id, sample_vendor.id)

            # Verify predict_with_fallback WAS invoked when order_count >= 30
            mock_bridge.assert_called_once()
            assert result["source"] == "model"
            assert result["predicted_eta_minutes"] == 18


# ===========================================================================
# 2. Demand Model Gate Tests
# ===========================================================================

class TestDemandModelGate:

    def test_vendor_insufficient_history_uses_heuristic(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        """Vendors with < 90 days order history MUST use heuristic fallback."""
        # Seed oldest order 30 days ago (< 90 days threshold)
        oldest_order = Order(
            user_id=sample_vendor.id,
            vendor_id=sample_vendor.id,
            slot_id=sample_slot.id,
            status=OrderStatus.COMPLETED,
            total_amount=20.0,
            created_at=NOW - timedelta(days=30),
        )
        db_session.add(oldest_order)
        db_session.commit()

        planner = DemandPlanner(db_session)
        with patch("app.modules.ai_intelligence.planners.demand_planner.utcnow_naive", return_value=NOW), \
             patch("app.modules.ai_intelligence.planners.demand_planner.predict_with_fallback") as mock_bridge:

            res = planner.get_demand_planning(sample_vendor.id)

            # Verify ML bridge was NOT called due to history gate
            mock_bridge.assert_not_called()
            assert res["forecast"]["source"] == "heuristic"
            assert res["forecast"]["forecast"][0]["confidence"] == 0.75
            assert "total_predicted" in res["forecast"]

    def test_vendor_sufficient_history_proceeds_to_model(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        """Vendors with >= 90 days order history attempt ML forecast."""
        # Seed oldest order 95 days ago (>= 90 days threshold)
        oldest_order = Order(
            user_id=sample_vendor.id,
            vendor_id=sample_vendor.id,
            slot_id=sample_slot.id,
            status=OrderStatus.COMPLETED,
            total_amount=20.0,
            created_at=NOW - timedelta(days=95),
        )
        db_session.add(oldest_order)
        db_session.commit()

        planner = DemandPlanner(db_session)
        with patch("app.modules.ai_intelligence.planners.demand_planner.utcnow_naive", return_value=NOW), \
             patch("app.modules.ai_intelligence.planners.demand_planner.predict_with_fallback", return_value=(25.0, "model")) as mock_bridge:

            res = planner.get_demand_planning(sample_vendor.id)

            mock_bridge.assert_called_once()
            assert "forecast" in res
            assert res["forecast"]["source"] == "model"


# ===========================================================================
# 3. Slot Safety Rule Tests
# ===========================================================================

class TestSlotSafetyRule:

    def test_slots_at_or_above_90_percent_capacity_excluded(
        self, db_session: Session, sample_vendor: User
    ):
        """Slots at >= 90% capacity MUST be excluded regardless of ML recommendation score."""
        # Slot A: 90% capacity (9/10) -> SHOULD BE EXCLUDED
        slot_90 = Slot(
            vendor_id=sample_vendor.id,
            start_time=NOW + timedelta(hours=1),
            end_time=NOW + timedelta(hours=2),
            max_orders=10,
            current_orders=9,
            status="available",
        )
        # Slot B: 100% capacity (10/10) -> SHOULD BE EXCLUDED
        slot_100 = Slot(
            vendor_id=sample_vendor.id,
            start_time=NOW + timedelta(hours=2),
            end_time=NOW + timedelta(hours=3),
            max_orders=10,
            current_orders=10,
            status="available",
        )
        # Slot C: 50% capacity (5/10) -> SHOULD BE INCLUDED
        slot_50 = Slot(
            vendor_id=sample_vendor.id,
            start_time=NOW + timedelta(hours=3),
            end_time=NOW + timedelta(hours=4),
            max_orders=10,
            current_orders=5,
            status="available",
        )
        # Slot D: 80% capacity (8/10) -> SHOULD BE INCLUDED
        slot_80 = Slot(
            vendor_id=sample_vendor.id,
            start_time=NOW + timedelta(hours=4),
            end_time=NOW + timedelta(hours=5),
            max_orders=10,
            current_orders=8,
            status="available",
        )
        db_session.add_all([slot_90, slot_100, slot_50, slot_80])
        db_session.commit()

        planner = SlotPlanner(db_session)

        # Mock ML bridge to return 0.99 (super high score) for ALL slots
        with patch("app.modules.ai_intelligence.planners.slot_planner.predict_with_fallback", return_value=(0.99, "model")):
            ranked = planner.get_available_slots_ranked(sample_vendor.id)

        returned_slot_ids = [s["slot_id"] for s in ranked]

        # Hard safety verification
        assert slot_90.id not in returned_slot_ids
        assert slot_100.id not in returned_slot_ids
        assert slot_50.id in returned_slot_ids
        assert slot_80.id in returned_slot_ids

        # Ensure returned slot items contain source metadata
        for s in ranked:
            assert "source" in s
            assert s["occupancy_pct"] < 90


# ===========================================================================
# 4. Vendor Ranking Express Pickup Hard Rule Tests
# ===========================================================================

class TestVendorRankingExpressPickupHardRule:

    def test_express_pickup_eligibility_is_hard_rule_independent_of_model_score(
        self, db_session: Session
    ):
        """Express pickup eligibility depends ONLY on live capacity, NOT ML score."""
        # Vendor A: high ML score (95.0), BUT full slots (current_orders=10, max_orders=10 -> ineligible)
        vendor_a = User(
            phone=f"+1555{_uid()[:7]}",
            name="Vendor A (Busy)",
            role=UserRole.VENDOR,
            vendor_type="food",
            is_approved=True,
        )
        # Vendor B: low ML score (20.0), BUT empty slots (current_orders=1, max_orders=10 -> eligible)
        vendor_b = User(
            phone=f"+1555{_uid()[:7]}",
            name="Vendor B (Free)",
            role=UserRole.VENDOR,
            vendor_type="food",
            is_approved=True,
        )
        db_session.add_all([vendor_a, vendor_b])
        db_session.flush()

        slot_a = Slot(
            vendor_id=vendor_a.id,
            start_time=NOW,
            end_time=NOW + timedelta(hours=1),
            max_orders=10,
            current_orders=10,
            status="available",
        )
        slot_b = Slot(
            vendor_id=vendor_b.id,
            start_time=NOW,
            end_time=NOW + timedelta(hours=1),
            max_orders=10,
            current_orders=1,
            status="available",
        )
        db_session.add_all([slot_a, slot_b])
        db_session.commit()

        # Seed 10 completed orders for Vendor A and 1 for Vendor B so total_orders differs
        for i in range(10):
            db_session.add(Order(
                user_id=vendor_a.id, vendor_id=vendor_a.id, slot_id=slot_a.id,
                status=OrderStatus.COMPLETED, created_at=NOW - timedelta(days=1),
            ))
        db_session.add(Order(
            user_id=vendor_b.id, vendor_id=vendor_b.id, slot_id=slot_b.id,
            status=OrderStatus.COMPLETED, created_at=NOW - timedelta(days=1),
        ))
        db_session.commit()

        ranker = VendorRanker(db_session)

        def mock_predict(model_type, features, heuristic_fn):
            # Vendor A has total_orders == 10.0
            if features.get("total_orders") == 10.0:
                return 0.95, "model"
            return 0.20, "model"

        with patch("app.modules.ai_intelligence.planners.vendor_ranker.predict_with_fallback", side_effect=mock_predict), \
             patch("app.modules.ai_intelligence.planners.vendor_ranker.utcnow_naive", return_value=NOW):

            rankings = ranker.get_vendor_rankings()

        v_a_rank = next(r for r in rankings if r["vendor_id"] == vendor_a.id)
        v_b_rank = next(r for r in rankings if r["vendor_id"] == vendor_b.id)

        # Confirm Vendor A has high rank score but is NOT express pickup eligible
        assert v_a_rank["vendor_rank_score"] == 95.0
        assert v_a_rank["express_pickup_eligible"] is False

        # Confirm Vendor B has lower rank score but IS express pickup eligible
        assert v_b_rank["vendor_rank_score"] == 20.0
        assert v_b_rank["express_pickup_eligible"] is True


# ===========================================================================
# 5. Fraud Detection Rule Safety Tests
# ===========================================================================

class TestFraudDeterministicRulesSafety:

    def test_rapid_multi_vendor_rule_triggers_without_ml(
        self, db_session: Session, sample_user: User, sample_vendor: User, sample_slot: Slot
    ):
        """Rapid multi-vendor rule fires deterministically regardless of ML models."""
        vendor_2 = User(
            phone=f"+1555{_uid()[:7]}",
            name="Vendor 2",
            role=UserRole.VENDOR,
            vendor_type="food",
            is_approved=True,
        )
        db_session.add(vendor_2)
        db_session.flush()

        slot_2 = Slot(
            vendor_id=vendor_2.id,
            start_time=NOW,
            end_time=NOW + timedelta(hours=1),
            max_orders=10,
            current_orders=1,
            status="available",
        )
        db_session.add(slot_2)
        db_session.commit()

        # Seed 2 recent orders across 2 different vendors in last 5 mins
        o1 = Order(user_id=sample_user.id, vendor_id=sample_vendor.id, slot_id=sample_slot.id, total_amount=10.0, created_at=NOW - timedelta(minutes=3))
        o2 = Order(user_id=sample_user.id, vendor_id=vendor_2.id, slot_id=slot_2.id, total_amount=12.0, created_at=NOW - timedelta(minutes=1))
        db_session.add_all([o1, o2])
        db_session.commit()

        # 3rd order placed now
        o3 = Order(user_id=sample_user.id, vendor_id=sample_vendor.id, slot_id=sample_slot.id, total_amount=15.0, created_at=NOW)
        db_session.add(o3)
        db_session.commit()

        with patch("app.modules.fraud.fraud_rules.utcnow_naive", return_value=NOW):
            reason = check_rapid_multi_vendor(o3, db_session)

        assert reason is not None
        assert "Rapid multi-vendor" in reason

    def test_value_outlier_rule_triggers_without_ml(
        self, db_session: Session, sample_user: User, sample_vendor: User, sample_slot: Slot
    ):
        """Value outlier rule fires deterministically when order is >5x past mean."""
        # Seed 5 past orders averaging ₹100.0 (10000 paise)
        for i in range(5):
            past_order = Order(
                user_id=sample_user.id,
                vendor_id=sample_vendor.id,
                slot_id=sample_slot.id,
                total_amount=10000,
                status=OrderStatus.COMPLETED,
                created_at=NOW - timedelta(days=i + 1),
            )
            db_session.add(past_order)
        db_session.commit()

        # Current order amount = ₹10,000.0 (1000000 paise) -> 100x mean
        outlier_order = Order(
            user_id=sample_user.id,
            vendor_id=sample_vendor.id,
            slot_id=sample_slot.id,
            total_amount=1000000,
            status=OrderStatus.PENDING,
            created_at=NOW,
        )
        db_session.add(outlier_order)
        db_session.commit()

        reason = check_value_outlier(outlier_order, db_session)
        assert reason is not None
        assert "Value outlier" in reason

    def test_slot_hoarding_rule_triggers_without_ml(
        self, db_session: Session, sample_user: User, sample_vendor: User, sample_slot: Slot
    ):
        """Slot hoarding rule fires deterministically when user has 2+ recent cancellations."""
        for i in range(2):
            cancelled = Order(
                user_id=sample_user.id,
                vendor_id=sample_vendor.id,
                slot_id=sample_slot.id,
                status=OrderStatus.CANCELLED,
                total_amount=15.0,
                created_at=NOW - timedelta(minutes=i + 2),
            )
            db_session.add(cancelled)
        db_session.commit()

        current_order = Order(
            user_id=sample_user.id,
            vendor_id=sample_vendor.id,
            slot_id=sample_slot.id,
            status=OrderStatus.PENDING,
            total_amount=15.0,
            created_at=NOW,
        )
        db_session.add(current_order)
        db_session.commit()

        with patch("app.modules.fraud.fraud_rules.utcnow_naive", return_value=NOW):
            reason = check_slot_hoarding(current_order, db_session)

        assert reason is not None
        assert "Slot-hoarding abuse" in reason

    def test_deterministic_fraud_checks_execute_even_if_ml_is_down(
        self, db_session: Session, sample_user: User, sample_vendor: User, sample_slot: Slot
    ):
        """run_fraud_checks returns deterministic reason regardless of ML availability."""
        # Seed 2 cancellations to trigger slot hoarding
        for i in range(2):
            db_session.add(Order(
                user_id=sample_user.id,
                vendor_id=sample_vendor.id,
                slot_id=sample_slot.id,
                status=OrderStatus.CANCELLED,
                created_at=NOW - timedelta(minutes=i + 1),
            ))
        db_session.commit()

        current_order = Order(
            user_id=sample_user.id,
            vendor_id=sample_vendor.id,
            slot_id=sample_slot.id,
            status=OrderStatus.PENDING,
            created_at=NOW,
        )
        db_session.add(current_order)
        db_session.commit()

        with patch("app.modules.fraud.fraud_rules.utcnow_naive", return_value=NOW):
            reason = run_fraud_checks(current_order, db_session)

        assert reason is not None
        assert "Slot-hoarding abuse" in reason


# ===========================================================================
# 6. Response Payload Source & Method Metadata Tests
# ===========================================================================

class TestPayloadMetadata:

    def test_eta_engine_payload_includes_source(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        engine = ETAEngine(db_session)
        with patch("app.modules.ai_intelligence.planners.eta_engine.utcnow_naive", return_value=NOW):
            res = engine.predict_eta(sample_slot.id, sample_vendor.id)

        assert "source" in res
        assert res["source"] in ("heuristic", "model")

    def test_slot_planner_payload_includes_source(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        planner = SlotPlanner(db_session)
        ranked = planner.get_available_slots_ranked(sample_vendor.id)

        assert len(ranked) > 0
        for item in ranked:
            assert "source" in item
            assert item["source"] in ("heuristic", "model")

    def test_vendor_ranker_payload_includes_source(
        self, db_session: Session, sample_vendor: User, sample_slot: Slot
    ):
        ranker = VendorRanker(db_session)
        with patch("app.modules.ai_intelligence.planners.vendor_ranker.utcnow_naive", return_value=NOW):
            rankings = ranker.get_vendor_rankings()

        assert len(rankings) >= 1
        v_res = next(r for r in rankings if r["vendor_id"] == sample_vendor.id)
        assert "source" in v_res
        assert v_res["source"] in ("heuristic", "model")
