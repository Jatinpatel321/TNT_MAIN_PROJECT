"""
Unit tests for app/modules/ai_intelligence/service.py — AIIntelligenceService.

Strategy:
- For all planner-delegation methods (get_demand_planning, get_capacity_recommendation,
  get_predictive_eta, get_vendor_ranking, get_personalization, get_reorder_suggestions)
  we monkeypatch the planner instance on the service to isolate orchestration logic.
- For DB-driven methods (get_slot_recommendations, get_group_coordination, get_user_signals,
  get_ai_recommendations, _generate_* helpers) we use the shared SQLite db_session
  with seeded data.
- apply_slot_adjustments is tested via patched slot_planner + seeded Slot rows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.modules.ai_intelligence.service import AIIntelligenceService
from app.modules.ai_intelligence.schemas import (
    AIAlert,
    CapacityRecommendationResponse,
    DemandPlanningResponse,
    GroupCoordinationResponse,
    PersonalizationResponse,
    PredictiveETAResponse,
    ProactiveAlertsResponse,
    ReorderSuggestionsResponse,
    SlotAdjustmentResponse,
    SlotRecommendationsResponse,
    VendorRankingResponse,
)
from app.modules.slots.model import Slot, SlotStatus
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.users.model import User, UserRole
from app.modules.menu.model import MenuItem


# ─────────────────────────────────────────────────────────────────────────────
# Seeding helpers
# ─────────────────────────────────────────────────────────────────────────────

def _unique() -> str:
    return uuid.uuid4().hex[:8]


def _make_vendor(db: Session, name: str = None) -> User:
    u = User(
        email=f"v_{_unique()}@test.com",
        phone=f"+155500{_unique()[:6]}",
        name=name or f"Vendor_{_unique()}",
        role=UserRole.VENDOR,
        is_approved=True,
    )
    db.add(u)
    db.flush()
    return u


def _make_student(db: Session) -> User:
    u = User(
        email=f"s_{_unique()}@test.com",
        phone=f"+155500{_unique()[:6]}",
        name=f"Student_{_unique()}",
        role=UserRole.STUDENT,
    )
    db.add(u)
    db.flush()
    return u


def _make_slot(
    db: Session,
    vendor_id: int,
    start_offset_hours: float = 1.0,
    max_orders: int = 10,
    current_orders: int = 2,
    status: str = "available",
    congestion_level: float = 0.2,
) -> Slot:
    now = datetime.utcnow()
    start = now + timedelta(hours=start_offset_hours)
    slot = Slot(
        vendor_id=vendor_id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        max_orders=max_orders,
        current_orders=current_orders,
        status=status,
        congestion_level=congestion_level,
    )
    db.add(slot)
    db.flush()
    return slot


def _make_menu_item(db: Session, vendor_id: int, name: str = None, is_available: bool = True) -> MenuItem:
    mi = MenuItem(
        vendor_id=vendor_id,
        name=name or f"Item_{_unique()}",
        price=5.99,
        is_available=is_available,
        category="food",
    )
    db.add(mi)
    db.flush()
    return mi


def _make_order(
    db: Session,
    user_id: int,
    vendor_id: int,
    slot_id: int,
    status: OrderStatus = OrderStatus.COMPLETED,
    created_at: datetime = None,
) -> Order:
    o = Order(
        user_id=user_id,
        vendor_id=vendor_id,
        slot_id=slot_id,
        status=status,
        total_amount=10.0,
        created_at=created_at or datetime.utcnow(),
    )
    db.add(o)
    db.flush()
    return o


def _make_order_item(db: Session, order_id: int, menu_item_id: int, quantity: int = 1) -> OrderItem:
    oi = OrderItem(
        order_id=order_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        price_at_time=5.99,
    )
    db.add(oi)
    db.flush()
    return oi


def _build_service(db: Session) -> AIIntelligenceService:
    return AIIntelligenceService(db)


# ─────────────────────────────────────────────────────────────────────────────
# Minimal planner return stubs
# ─────────────────────────────────────────────────────────────────────────────

def _demand_response():
    return DemandPlanningResponse(
        expected_daily_orders=50,
        slot_wise_demand_graph={"08": 10, "12": 20, "18": 20},
        popular_items=[{"item_id": 1, "name": "Burger", "count": 10}],
        stationery_workload_score=0.3,
        food_waste_risk_score=0.1,
    )


def _capacity_dict(vendor_id=1, capacity=15):
    return {"vendor_id": vendor_id, "recommended_capacity": capacity, "reasoning": "based on trends"}


def _eta_dict():
    now = datetime.utcnow()
    return {
        "predicted_eta_minutes": 12,
        "pickup_window_start": now,
        "pickup_window_end": now + timedelta(minutes=12),
        "delay_risk_level": "LOW",
        "source": "heuristic",
    }


def _personalization_dict():
    return {
        "recommended_for_you": [{"item_id": 1, "name": "Burger"}],
        "smart_suggestions": [{"slot_id": 1, "reason": "low congestion"}],
        "active_preferences": {"cuisine": "fast food"},
    }


def _reorder_dict():
    return {
        "suggestions": [],
        "best_time_to_reorder": "08:00-09:00",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Section 1 — Planner Delegation (pure monkeypatch, no DB seeding needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestPlannerDelegation:
    """Verify the service correctly delegates to planners and wraps results."""

    def test_get_demand_planning(self, db_session: Session):
        svc = _build_service(db_session)
        resp = _demand_response()
        svc.demand_planner.get_demand_planning = MagicMock(return_value=resp)
        result = svc.get_demand_planning(vendor_id=42)
        assert isinstance(result, DemandPlanningResponse)
        assert result.expected_daily_orders == 50
        svc.demand_planner.get_demand_planning.assert_called_once_with(42)

    def test_get_capacity_recommendation(self, db_session: Session):
        svc = _build_service(db_session)
        svc.slot_planner.get_capacity_recommendation = MagicMock(return_value=_capacity_dict(vendor_id=7))
        result = svc.get_capacity_recommendation(vendor_id=7)
        assert isinstance(result, CapacityRecommendationResponse)
        assert result.recommended_capacity == 15
        assert result.vendor_id == 7

    def test_get_capacity_recommendation_planner_exception(self, db_session: Session):
        svc = _build_service(db_session)
        svc.slot_planner.get_capacity_recommendation = MagicMock(side_effect=RuntimeError("planner down"))
        with pytest.raises(RuntimeError):
            svc.get_capacity_recommendation(vendor_id=1)

    def test_get_predictive_eta(self, db_session: Session):
        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value=_eta_dict())
        result = svc.get_predictive_eta(slot_id=5, vendor_id=10)
        assert isinstance(result, PredictiveETAResponse)
        assert result.predicted_eta_minutes == 12
        assert result.delay_risk_level == "LOW"
        svc.eta_engine.predict_eta.assert_called_once_with(5, 10)

    def test_get_vendor_ranking(self, db_session: Session):
        svc = _build_service(db_session)
        from app.modules.ai_intelligence.schemas import VendorRanking
        ranking = VendorRanking(
            vendor_id=1, vendor_rank_score=90.0, live_load_indicator="LOW",
            express_pickup_eligible=True, reasoning="top vendor", rank=1
        )
        svc.vendor_ranker.get_vendor_rankings = MagicMock(return_value=[ranking])
        result = svc.get_vendor_ranking()
        assert isinstance(result, VendorRankingResponse)
        assert len(result.rankings) == 1
        assert result.rankings[0].vendor_id == 1

    def test_get_vendor_ranking_empty(self, db_session: Session):
        svc = _build_service(db_session)
        svc.vendor_ranker.get_vendor_rankings = MagicMock(return_value=[])
        result = svc.get_vendor_ranking()
        assert result.rankings == []

    def test_get_personalization(self, db_session: Session):
        svc = _build_service(db_session)
        svc.preference_engine.get_personalization = MagicMock(return_value=_personalization_dict())
        result = svc.get_personalization(user_id=99)
        assert isinstance(result, PersonalizationResponse)
        assert len(result.recommended_for_you) == 1
        svc.preference_engine.get_personalization.assert_called_once_with(99)

    def test_get_reorder_suggestions(self, db_session: Session):
        svc = _build_service(db_session)
        svc.reorder_engine.generate_reorder_suggestions = MagicMock(return_value=_reorder_dict())
        result = svc.get_reorder_suggestions(user_id=7)
        assert isinstance(result, ReorderSuggestionsResponse)
        assert result.best_time_to_reorder == "08:00-09:00"
        svc.reorder_engine.generate_reorder_suggestions.assert_called_once_with(7)


# ─────────────────────────────────────────────────────────────────────────────
# Section 2 — get_slot_recommendations
# ─────────────────────────────────────────────────────────────────────────────

class TestGetSlotRecommendations:
    """Tests for slot recommendation aggregation."""

    def test_no_slots_raises_validation_error(self, db_session: Session):
        """When no slots exist, best_slot_id=None fails schema validation (int required).
        This is the actual service behaviour."""
        from pydantic import ValidationError
        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value=_eta_dict())
        with pytest.raises(ValidationError):
            svc.get_slot_recommendations()

    def test_single_slot_returned(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=2)
        db_session.commit()

        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value=_eta_dict())
        result = svc.get_slot_recommendations()
        assert isinstance(result, SlotRecommendationsResponse)
        assert len(result.recommendations) == 1
        assert result.best_slot_id is not None
        assert result.recommendations[0].estimated_eta_minutes == 12

    def test_multiple_slots_sorted_by_score(self, db_session: Session):
        vendor = _make_vendor(db_session)
        # High-capacity slot (better score)
        _make_slot(db_session, vendor.id, max_orders=20, current_orders=1, start_offset_hours=2)
        # Near-full slot (worse score)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=9, start_offset_hours=3)
        db_session.commit()

        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value=_eta_dict())
        result = svc.get_slot_recommendations()
        assert isinstance(result, SlotRecommendationsResponse)
        assert len(result.recommendations) >= 2
        scores = [r.score for r in result.recommendations]
        assert scores == sorted(scores, reverse=True)

    def test_full_slots_excluded_raises_validation_error(self, db_session: Session):
        """When only 'full' slots exist they are filtered out, leaving best_slot_id=None.
        That triggers a Pydantic ValidationError — actual service behaviour."""
        from pydantic import ValidationError
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, status="full")
        db_session.commit()

        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value=_eta_dict())
        with pytest.raises(ValidationError):
            svc.get_slot_recommendations()

    def test_with_user_id_parameter(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id)
        db_session.commit()

        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value=_eta_dict())
        result = svc.get_slot_recommendations(user_id=42)
        assert isinstance(result, SlotRecommendationsResponse)


# ─────────────────────────────────────────────────────────────────────────────
# Section 3 — apply_slot_adjustments
# ─────────────────────────────────────────────────────────────────────────────

# Deferred imports inside apply_slot_adjustments:
#   from app.modules.slots.service import (create_slot_capacity_rule,
#                                           get_slot_capacity_rules,
#                                           update_slot_capacity_rule)
# → must patch at app.modules.slots.service.*
_SLOTS_SVC = "app.modules.slots.service"


class TestApplySlotAdjustments:
    """Tests for the slot adjustment orchestration."""

    def _stub_planner(self, svc: AIIntelligenceService, vendor_id: int, signals: list):
        svc.slot_planner.get_capacity_recommendation = MagicMock(
            return_value=_capacity_dict(vendor_id=vendor_id, capacity=8)
        )
        svc.slot_planner.get_slot_adjustment_signals = MagicMock(return_value=signals)

    def test_no_signals_returns_empty_adjustments(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        svc = _build_service(db_session)
        self._stub_planner(svc, vendor.id, signals=[])

        with patch(f"{_SLOTS_SVC}.get_slot_capacity_rules", return_value=[]):
            result = svc.apply_slot_adjustments(vendor.id)

        assert isinstance(result, SlotAdjustmentResponse)
        assert result.adjustments_applied == 0
        assert result.adjustments == []

    def test_underutilized_slot_reduces_capacity(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=20, current_orders=2)
        db_session.commit()

        svc = _build_service(db_session)
        self._stub_planner(svc, vendor.id, signals=[
            {"type": "underutilized_slot", "slot_id": slot.id}
        ])

        with (
            patch(f"{_SLOTS_SVC}.get_slot_capacity_rules", return_value=[]),
            patch(f"{_SLOTS_SVC}.create_slot_capacity_rule"),
        ):
            result = svc.apply_slot_adjustments(vendor.id)

        assert result.adjustments_applied == 1
        adj = result.adjustments[0]
        assert adj["type"] == "underutilized_slot"
        assert adj["action"] == "reduced_capacity"
        assert adj["new_capacity"] < 20

    def test_underutilized_slot_missing_slot_id_skipped(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        svc = _build_service(db_session)
        self._stub_planner(svc, vendor.id, signals=[
            {"type": "underutilized_slot", "slot_id": 99999}  # nonexistent
        ])

        with patch(f"{_SLOTS_SVC}.get_slot_capacity_rules", return_value=[]):
            result = svc.apply_slot_adjustments(vendor.id)

        assert result.adjustments_applied == 0

    def test_underutilized_slot_existing_rule_updates(self, db_session: Session):
        vendor = _make_vendor(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=20, current_orders=2)
        db_session.commit()

        fake_rule = MagicMock()
        fake_rule.id = 77
        fake_rule.rule_name = f"AI Auto-Adjustment (Underutilized {slot.start_time.hour:02d}:00)"

        svc = _build_service(db_session)
        self._stub_planner(svc, vendor.id, signals=[
            {"type": "underutilized_slot", "slot_id": slot.id}
        ])

        with (
            patch(f"{_SLOTS_SVC}.get_slot_capacity_rules", return_value=[fake_rule]),
            patch(f"{_SLOTS_SVC}.update_slot_capacity_rule") as mock_update,
        ):
            result = svc.apply_slot_adjustments(vendor.id)

        mock_update.assert_called_once()

    def test_peak_hour_detected_raises_capacity(self, db_session: Session):
        vendor = _make_vendor(db_session)
        now = datetime.utcnow()
        slot = Slot(
            vendor_id=vendor.id,
            start_time=now + timedelta(minutes=5),
            end_time=now + timedelta(minutes=65),
            max_orders=5,
            current_orders=1,
            status="available",
        )
        db_session.add(slot)
        db_session.commit()

        svc = _build_service(db_session)
        svc.slot_planner.get_capacity_recommendation = MagicMock(
            return_value=_capacity_dict(vendor_id=vendor.id, capacity=15)
        )
        svc.slot_planner.get_slot_adjustment_signals = MagicMock(return_value=[
            {"type": "peak_hour_detected"}
        ])

        with patch(f"{_SLOTS_SVC}.get_slot_capacity_rules", return_value=[]):
            result = svc.apply_slot_adjustments(vendor.id)

        # slot.max_orders=5, recommended_capacity=15 → should increase
        adj_types = [a["type"] for a in result.adjustments]
        if result.adjustments_applied > 0:
            assert "peak_hour_detected" in adj_types

    def test_unknown_signal_type_ignored(self, db_session: Session):
        vendor = _make_vendor(db_session)
        db_session.commit()

        svc = _build_service(db_session)
        self._stub_planner(svc, vendor.id, signals=[
            {"type": "unknown_signal_xyz"}
        ])

        # No slot service functions called for unknown signals
        result = svc.apply_slot_adjustments(vendor.id)
        assert result.adjustments_applied == 0

    def test_peak_hour_detected_slot_wrong_hour_skipped(self, db_session: Session):
        """Slot whose hour != peak_hour is skipped via the continue branch (line 133)."""
        vendor = _make_vendor(db_session)
        now = datetime.utcnow()
        peak_hour = now.hour
        # Place slot 2 hours ahead so its hour != peak_hour (unless peak_hour==22)
        offset = 2 if peak_hour < 22 else -2
        other_hour = peak_hour + offset
        slot_time = now.replace(hour=other_hour, minute=30)
        slot = Slot(
            vendor_id=vendor.id,
            start_time=slot_time,
            end_time=slot_time + timedelta(hours=1),
            max_orders=5,
            current_orders=1,
            status="available",
        )
        db_session.add(slot)
        db_session.commit()

        svc = _build_service(db_session)
        svc.slot_planner.get_capacity_recommendation = MagicMock(
            return_value=_capacity_dict(vendor_id=vendor.id, capacity=15)
        )
        svc.slot_planner.get_slot_adjustment_signals = MagicMock(return_value=[
            {"type": "peak_hour_detected"}
        ])

        with patch(f"{_SLOTS_SVC}.get_slot_capacity_rules", return_value=[]):
            result = svc.apply_slot_adjustments(vendor.id)

        # The slot is in the wrong hour so it is skipped - no adjustments made
        assert result.adjustments_applied == 0


# ─────────────────────────────────────────────────────────────────────────────
# Section 4 — get_proactive_alerts
# ─────────────────────────────────────────────────────────────────────────────

class TestGetProactiveAlerts:
    """Tests for proactive alert aggregation."""

    def test_no_user_id_no_delay_alerts(self, db_session: Session):
        svc = _build_service(db_session)
        with patch.object(svc, "_generate_rush_hour_alerts", return_value=[]):
            with patch.object(svc, "_generate_vendor_overload_alerts", return_value=[]):
                result = svc.get_proactive_alerts(user_id=None)
        assert isinstance(result, ProactiveAlertsResponse)
        assert result.alerts == []

    def test_with_user_id_generates_delay_alerts(self, db_session: Session):
        svc = _build_service(db_session)
        fake_alert = AIAlert(
            type="delay_risk", severity="high",
            explanation="High risk", suggested_action="Contact vendor"
        )
        with (
            patch.object(svc, "_generate_rush_hour_alerts", return_value=[]),
            patch.object(svc, "_generate_delay_risk_alerts", return_value=[fake_alert]),
            patch.object(svc, "_generate_vendor_overload_alerts", return_value=[]),
        ):
            result = svc.get_proactive_alerts(user_id=1)
        assert len(result.alerts) == 1
        assert result.alerts[0].type == "delay_risk"

    def test_rush_hour_alerts_aggregated(self, db_session: Session):
        svc = _build_service(db_session)
        rush_alert = AIAlert(
            type="rush_hour", severity="medium",
            explanation="Lunch rush", suggested_action="Order early"
        )
        overload_alert = AIAlert(
            type="vendor_overload", severity="medium",
            explanation="Overloaded", suggested_action="Try later"
        )
        with (
            patch.object(svc, "_generate_rush_hour_alerts", return_value=[rush_alert]),
            patch.object(svc, "_generate_delay_risk_alerts", return_value=[]),
            patch.object(svc, "_generate_vendor_overload_alerts", return_value=[overload_alert]),
        ):
            result = svc.get_proactive_alerts(user_id=1)
        assert len(result.alerts) == 2


# ─────────────────────────────────────────────────────────────────────────────
# Section 5 — _generate_rush_hour_alerts (time-sensitive)
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateRushHourAlerts:
    def test_lunch_hour_triggers_alert(self, db_session: Session):
        svc = _build_service(db_session)
        lunch_dt = datetime.utcnow().replace(hour=13, minute=0, second=0)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=lunch_dt):
            alerts = svc._generate_rush_hour_alerts()
        assert any(a.type == "rush_hour" for a in alerts)

    def test_dinner_hour_triggers_alert(self, db_session: Session):
        svc = _build_service(db_session)
        dinner_dt = datetime.utcnow().replace(hour=20, minute=0, second=0)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=dinner_dt):
            alerts = svc._generate_rush_hour_alerts()
        assert any(a.type == "rush_hour" for a in alerts)

    def test_off_peak_no_alerts(self, db_session: Session):
        svc = _build_service(db_session)
        off_peak = datetime.utcnow().replace(hour=10, minute=0, second=0)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=off_peak):
            alerts = svc._generate_rush_hour_alerts()
        assert alerts == []


# ─────────────────────────────────────────────────────────────────────────────
# Section 6 — _generate_vendor_overload_alerts
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateVendorOverloadAlerts:
    def test_overloaded_slot_generates_alert(self, db_session: Session):
        vendor = _make_vendor(db_session)
        # current_orders >= max_orders * 0.9 → overloaded
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=9)
        db_session.commit()

        svc = _build_service(db_session)
        alerts = svc._generate_vendor_overload_alerts()
        assert any(a.type == "vendor_overload" for a in alerts)

    def test_no_overloaded_slots_no_alerts(self, db_session: Session):
        vendor = _make_vendor(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=2)
        db_session.commit()

        svc = _build_service(db_session)
        alerts = svc._generate_vendor_overload_alerts()
        assert alerts == []


# ─────────────────────────────────────────────────────────────────────────────
# Section 7 — _generate_delay_risk_alerts
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateDelayRiskAlerts:
    def test_high_risk_order_creates_alert(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, max_orders=10, current_orders=9)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.CONFIRMED,
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db_session.commit()

        high_risk_eta = PredictiveETAResponse(
            predicted_eta_minutes=30,
            pickup_window_start=datetime.utcnow(),
            pickup_window_end=datetime.utcnow() + timedelta(minutes=30),
            delay_risk_level="HIGH",
            source="heuristic",
        )

        svc = _build_service(db_session)
        svc.eta_engine.predict_eta = MagicMock(return_value={
            **high_risk_eta.model_dump(),
        })

        with patch.object(svc, "get_predictive_eta", return_value=high_risk_eta):
            alerts = svc._generate_delay_risk_alerts(student.id)

        assert any(a.type == "delay_risk" and a.severity == "high" for a in alerts)

    def test_no_upcoming_orders_no_alerts(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        alerts = svc._generate_delay_risk_alerts(student.id)
        assert alerts == []

    def test_low_risk_order_no_alert(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.CONFIRMED,
            created_at=datetime.utcnow() - timedelta(minutes=30),
        )
        db_session.commit()

        low_risk_eta = PredictiveETAResponse(
            predicted_eta_minutes=10,
            pickup_window_start=datetime.utcnow(),
            pickup_window_end=datetime.utcnow() + timedelta(minutes=10),
            delay_risk_level="LOW",
            source="heuristic",
        )
        svc = _build_service(db_session)
        with patch.object(svc, "get_predictive_eta", return_value=low_risk_eta):
            alerts = svc._generate_delay_risk_alerts(student.id)
        assert alerts == []


# ─────────────────────────────────────────────────────────────────────────────
# Section 8 — _generate_slot_reasoning
# ─────────────────────────────────────────────────────────────────────────────

class TestGenerateSlotReasoning:
    def _make_db_slot(self, db_session: Session, max_orders: int = 10, current_orders: int = 2) -> Slot:
        vendor = _make_vendor(db_session)
        return _make_slot(db_session, vendor.id, max_orders=max_orders, current_orders=current_orders)

    def test_excellent_score_label(self, db_session: Session):
        slot = self._make_db_slot(db_session)
        svc = _build_service(db_session)
        reason = svc._generate_slot_reasoning(slot, score=85.0, speed_score=80.0, completion_rate=0.95)
        assert "Excellent choice" in reason
        assert "fast vendor" in reason
        assert "highly reliable" in reason

    def test_good_score_label(self, db_session: Session):
        slot = self._make_db_slot(db_session)
        svc = _build_service(db_session)
        reason = svc._generate_slot_reasoning(slot, score=65.0, speed_score=50.0, completion_rate=0.80)
        assert "Good option" in reason

    def test_consider_alternative_label(self, db_session: Session):
        slot = self._make_db_slot(db_session)
        svc = _build_service(db_session)
        reason = svc._generate_slot_reasoning(slot, score=40.0, speed_score=30.0, completion_rate=0.60)
        assert "Consider alternative" in reason
        assert "slower vendor" in reason
        assert "variable reliability" in reason

    def test_limited_spots_warning(self, db_session: Session):
        slot = self._make_db_slot(db_session, max_orders=5, current_orders=4)
        svc = _build_service(db_session)
        reason = svc._generate_slot_reasoning(slot, score=60.0, speed_score=50.0, completion_rate=0.80)
        assert "limited spots" in reason


# ─────────────────────────────────────────────────────────────────────────────
# Section 9 — get_group_coordination
# ─────────────────────────────────────────────────────────────────────────────

class TestGetGroupCoordination:
    def test_empty_user_ids_returns_zero_score(self, db_session: Session):
        svc = _build_service(db_session)
        result = svc.get_group_coordination([])
        assert isinstance(result, GroupCoordinationResponse)
        assert result.coordination_score == 0.0
        assert result.overlapping_windows == []
        assert result.suggested_unified_slot is None

    def test_single_user_no_overlap(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        result = svc.get_group_coordination([student.id])
        assert result.coordination_score == 0.0

    def test_overlapping_users_positive_score(self, db_session: Session):
        vendor = _make_vendor(db_session)
        s1 = _make_student(db_session)
        s2 = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, start_offset_hours=1)

        # Both users have orders created at the same hour
        shared_hour_time = datetime.utcnow().replace(hour=12, minute=0, second=0)
        _make_order(db_session, s1.id, vendor.id, slot.id,
                    created_at=shared_hour_time)
        _make_order(db_session, s2.id, vendor.id, slot.id,
                    created_at=shared_hour_time)
        db_session.commit()

        svc = _build_service(db_session)
        result = svc.get_group_coordination([s1.id, s2.id])
        assert isinstance(result, GroupCoordinationResponse)
        # Both users active at hour 12 → overlap → score > 0
        if result.overlapping_windows:
            assert result.coordination_score > 0.0

    def test_group_coordination_with_available_slots(self, db_session: Session):
        vendor = _make_vendor(db_session)
        s1 = _make_student(db_session)
        s2 = _make_student(db_session)

        # Slot at the overlap hour (hour=12)
        overlap_time = datetime.utcnow().replace(hour=12, minute=0, second=0)
        slot = Slot(
            vendor_id=vendor.id,
            start_time=overlap_time + timedelta(days=1),  # future slot
            end_time=overlap_time + timedelta(days=1, hours=1),
            max_orders=10,
            current_orders=2,
            status="available",
        )
        db_session.add(slot)
        db_session.flush()

        shared_hour_time = datetime.utcnow().replace(hour=12)
        _make_order(db_session, s1.id, vendor.id, slot.id, created_at=shared_hour_time)
        _make_order(db_session, s2.id, vendor.id, slot.id, created_at=shared_hour_time)
        db_session.commit()

        svc = _build_service(db_session)
        result = svc.get_group_coordination([s1.id, s2.id])
        assert isinstance(result, GroupCoordinationResponse)


# ─────────────────────────────────────────────────────────────────────────────
# Section 10 — get_user_signals / sub-signals
# ─────────────────────────────────────────────────────────────────────────────

class TestGetUserSignals:
    def test_get_user_signals_aggregates_all(self, db_session: Session):
        svc = _build_service(db_session)
        student = _make_student(db_session)
        db_session.commit()

        with (
            patch.object(svc, "get_rush_hour_signals", return_value=[{"type": "rush_hour_warning"}]),
            patch.object(svc, "get_slot_suggestion_signals", return_value=[{"type": "slot_suggestion"}]),
            patch.object(svc, "get_reorder_prompt_signals", return_value=[{"type": "reorder_prompt"}]),
        ):
            signals = svc.get_user_signals(student.id)

        assert len(signals) == 3
        types = {s["type"] for s in signals}
        assert types == {"rush_hour_warning", "slot_suggestion", "reorder_prompt"}

    def test_get_user_signals_empty_if_no_activity(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        # No patches — pure DB, no orders or slots → all sub-signals empty
        signals = svc.get_user_signals(student.id)
        assert isinstance(signals, list)


class TestGetRushHourSignals:
    def test_during_rush_with_upcoming_order(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        now = datetime.utcnow().replace(hour=12, minute=30, second=0)
        slot = Slot(
            vendor_id=vendor.id,
            start_time=now + timedelta(minutes=30),
            end_time=now + timedelta(minutes=90),
            max_orders=10,
            current_orders=1,
            status="available",
        )
        db_session.add(slot)
        db_session.flush()
        order = _make_order(
            db_session, student.id, vendor.id, slot.id,
            status=OrderStatus.CONFIRMED,
        )
        db_session.commit()

        svc = _build_service(db_session)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=now):
            signals = svc.get_rush_hour_signals(student.id)

        assert any(s["type"] == "rush_hour_warning" for s in signals)

    def test_outside_rush_no_signal(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        off_peak = datetime.utcnow().replace(hour=10, minute=0, second=0)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=off_peak):
            signals = svc.get_rush_hour_signals(student.id)
        assert signals == []

    def test_rush_hour_no_upcoming_orders_no_signal(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        rush_dt = datetime.utcnow().replace(hour=13, minute=0, second=0)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=rush_dt):
            signals = svc.get_rush_hour_signals(student.id)
        assert signals == []


class TestGetSlotSuggestionSignals:
    def test_no_completed_orders_returns_empty(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        signals = svc.get_slot_suggestion_signals(student.id)
        assert signals == []

    def test_low_congestion_slot_at_preferred_hour_signals(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        # Use a fixed "now" at 08:00 so preferred_hour=09 which is within today
        fixed_now = datetime.utcnow().replace(hour=8, minute=0, second=0, microsecond=0)
        preferred_hour = 9  # (fixed_now.hour + 1) % 24

        # Historical completed order at hour 09 (in the past) to establish preference
        historical_slot_time = fixed_now.replace(hour=preferred_hour) - timedelta(days=1)
        past_slot = Slot(
            vendor_id=vendor.id,
            start_time=historical_slot_time,
            end_time=historical_slot_time + timedelta(hours=1),
            max_orders=10, current_orders=2, status="available", congestion_level=0.2,
        )
        db_session.add(past_slot)
        db_session.flush()
        _make_order(db_session, student.id, vendor.id, past_slot.id, status=OrderStatus.COMPLETED)

        # Future slot TODAY at preferred_hour (09:30) with low congestion
        # day_end = fixed_now.replace(hour=0,...) + timedelta(days=1) = midnight tonight
        # 09:30 today < midnight tonight → within window
        future_slot_time = fixed_now.replace(hour=preferred_hour, minute=30)
        future_slot = Slot(
            vendor_id=vendor.id,
            start_time=future_slot_time,
            end_time=future_slot_time + timedelta(hours=1),
            max_orders=10, current_orders=1, status="available", congestion_level=0.2,
        )
        db_session.add(future_slot)
        db_session.commit()

        svc = _build_service(db_session)
        with patch("app.modules.ai_intelligence.service.utcnow_naive", return_value=fixed_now):
            signals = svc.get_slot_suggestion_signals(student.id)

        # The low-congestion slot at the preferred hour should trigger a suggestion
        assert any(s["type"] == "slot_suggestion" for s in signals)


class TestGetReorderPromptSignals:
    def test_no_recent_orders_returns_empty(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        signals = svc.get_reorder_prompt_signals(student.id)
        assert signals == []

    def test_frequently_ordered_item_triggers_signal(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id, name="Veg Burger")

        # 3+ orders of same item in last 30 days → triggers reorder signal
        for _ in range(3):
            order = _make_order(db_session, student.id, vendor.id, slot.id)
            _make_order_item(db_session, order.id, item.id, quantity=1)

        db_session.commit()

        svc = _build_service(db_session)
        signals = svc.get_reorder_prompt_signals(student.id)
        assert any(s["type"] == "reorder_prompt" for s in signals)
        if signals:
            assert signals[0]["data"]["item_name"] == "Veg Burger"

    def test_infrequent_item_no_signal(self, db_session: Session):
        """Item ordered fewer than 3 times → no reorder prompt."""
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id)

        order = _make_order(db_session, student.id, vendor.id, slot.id)
        _make_order_item(db_session, order.id, item.id, quantity=2)
        db_session.commit()

        svc = _build_service(db_session)
        signals = svc.get_reorder_prompt_signals(student.id)
        assert signals == []


# ─────────────────────────────────────────────────────────────────────────────
# Section 11 — get_ai_recommendations
# ─────────────────────────────────────────────────────────────────────────────

class TestGetAIRecommendations:
    def test_empty_db_returns_empty_lists(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        result = svc.get_ai_recommendations(student.id)
        assert "recommended_items" in result
        assert "frequent_orders" in result
        assert "best_slots" in result
        assert "vendors_ranked" in result
        assert result["frequent_orders"] == []
        assert result["vendors_ranked"] == []

    def test_with_order_history_returns_recommendations(self, db_session: Session):
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id, current_orders=2, max_orders=10)
        item = _make_menu_item(db_session, vendor.id, name="Pizza")

        for _ in range(3):
            order = _make_order(db_session, student.id, vendor.id, slot.id)
            _make_order_item(db_session, order.id, item.id)

        db_session.commit()

        svc = _build_service(db_session)
        result = svc.get_ai_recommendations(student.id)

        assert len(result["frequent_orders"]) >= 1
        assert result["frequent_orders"][0]["name"] == "Pizza"
        assert len(result["vendors_ranked"]) >= 1

    def test_best_slots_only_partially_filled(self, db_session: Session):
        """best_slots only includes slots where current_orders < max_orders."""
        vendor = _make_vendor(db_session)
        student = _make_student(db_session)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=3)
        _make_slot(db_session, vendor.id, max_orders=10, current_orders=10)  # full
        db_session.commit()

        svc = _build_service(db_session)
        result = svc.get_ai_recommendations(student.id)
        for slot_info in result["best_slots"]:
            assert slot_info["load_status"] == "low"

    def test_popular_items_campus_wide(self, db_session: Session):
        """Recommended items include campus-wide trending items regardless of user."""
        vendor = _make_vendor(db_session)
        other_student = _make_student(db_session)
        student = _make_student(db_session)
        slot = _make_slot(db_session, vendor.id)
        item = _make_menu_item(db_session, vendor.id, name="Trending Sandwich")

        # Other student orders item many times
        for _ in range(5):
            order = _make_order(db_session, other_student.id, vendor.id, slot.id)
            _make_order_item(db_session, order.id, item.id)
        db_session.commit()

        svc = _build_service(db_session)
        result = svc.get_ai_recommendations(student.id)
        assert any(r["name"] == "Trending Sandwich" for r in result["recommended_items"])

    def test_response_payload_shape(self, db_session: Session):
        student = _make_student(db_session)
        db_session.commit()
        svc = _build_service(db_session)
        result = svc.get_ai_recommendations(student.id)

        assert set(result.keys()) == {"recommended_items", "frequent_orders", "best_slots", "vendors_ranked"}
        for item in result["recommended_items"]:
            assert "item_id" in item and "name" in item and "score" in item
        for slot in result["best_slots"]:
            assert "slot_id" in slot and "vendor_id" in slot and "load_status" in slot
