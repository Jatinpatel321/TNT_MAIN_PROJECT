"""
Route-level FastAPI tests for AI Intelligence endpoints:
  - app/modules/ai_intelligence/router.py
  - app/modules/ai_intelligence/enhanced_eta_router.py
  - app/modules/ai_intelligence/vendor_speed_router.py

Tests routes directly via FastAPI TestClient on a dedicated test app instance.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_user
from app.modules.ai_intelligence.enhanced_eta_router import router as enhanced_eta_router
from app.modules.ai_intelligence.router import router as ai_router
from app.modules.ai_intelligence.vendor_speed_router import router as vendor_speed_router
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole

NOW = datetime(2024, 6, 15, 12, 0, 0)
FIVE_DAYS_AGO = NOW - timedelta(days=5)


def _uid() -> str:
    return uuid.uuid4().hex[:8]


# ---------------------------------------------------------------------------
# Test App & Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_db(db_session: Session):
    v = User(
        phone=f"+1555{_uid()[:7]}",
        name="Test Vendor",
        role=UserRole.VENDOR,
        vendor_type="food",
        is_approved=True,
    )
    s = User(
        phone=f"+1666{_uid()[:7]}",
        name="Test Student",
        role=UserRole.STUDENT,
        vendor_type="food",
    )
    db_session.add_all([v, s])
    db_session.flush()

    slot = Slot(
        vendor_id=v.id,
        start_time=NOW + timedelta(hours=1),
        end_time=NOW + timedelta(hours=2),
        max_orders=20,
        current_orders=15,  # 75% utilization
        status="available",
    )
    db_session.add(slot)
    db_session.flush()

    item = MenuItem(
        vendor_id=v.id,
        name="Special Thali",
        price=12.0,
        category="indian",
        is_available=True,
    )
    db_session.add(item)
    db_session.flush()

    order = Order(
        user_id=s.id,
        vendor_id=v.id,
        slot_id=slot.id,
        status=OrderStatus.COMPLETED,
        total_amount=12.0,
        created_at=FIVE_DAYS_AGO,
        eta_minutes=15,
    )
    db_session.add(order)
    db_session.flush()

    order_item = OrderItem(
        order_id=order.id,
        menu_item_id=item.id,
        quantity=1,
        price_at_time=12.0,
    )
    db_session.add(order_item)
    db_session.commit()

    return {
        "vendor": v,
        "student": s,
        "slot": slot,
        "item": item,
        "order": order,
    }


@pytest.fixture
def test_app(db_session: Session, seeded_db: dict):
    app = FastAPI(title="AI Routers Test App")
    app.include_router(ai_router)
    app.include_router(enhanced_eta_router)
    app.include_router(vendor_speed_router)

    student = seeded_db["student"]
    vendor = seeded_db["vendor"]

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_user] = lambda: {
        "id": student.id,
        "phone": student.phone,
        "role": student.role.value,
    }

    # Dynamically find non-get_db dependencies on /ai/apply-slot-adjustment to override vendor role
    for route in ai_router.routes:
        if getattr(route, "path", None) == "/ai/apply-slot-adjustment":
            for dep in route.dependant.dependencies:
                if dep.call != get_db:
                    app.dependency_overrides[dep.call] = lambda: {
                        "id": vendor.id,
                        "phone": vendor.phone,
                        "role": vendor.role.value,
                    }

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. Main AI Router Endpoints (app/modules/ai_intelligence/router.py)
# ---------------------------------------------------------------------------

class TestMainAIRouter:

    def test_demand_planning(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        resp = test_app.get(f"/ai/demand-planning?vendor_id={v_id}")
        assert resp.status_code == 200

    def test_capacity_recommendation(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        resp = test_app.get(f"/ai/capacity-recommendation?vendor_id={v_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vendor_id"] == v_id

    def test_slot_recommendations(self, test_app: TestClient):
        resp = test_app.get("/ai/slot-recommendations")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_predictive_eta(self, test_app: TestClient, seeded_db: dict):
        s_id = seeded_db["slot"].id
        v_id = seeded_db["vendor"].id
        resp = test_app.get(f"/ai/predictive-eta?slot_id={s_id}&vendor_id={v_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "predicted_eta_minutes" in data

    def test_vendor_ranking(self, test_app: TestClient):
        resp = test_app.get("/ai/vendor-ranking")
        assert resp.status_code == 200
        data = resp.json()
        assert "rankings" in data

    def test_personalization(self, test_app: TestClient):
        resp = test_app.get("/ai/personalization")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommended_for_you" in data

    def test_reorder_suggestions(self, test_app: TestClient):
        resp = test_app.get("/ai/reorder-suggestions")
        assert resp.status_code == 200
        data = resp.json()
        assert "suggestions" in data

    def test_proactive_alerts(self, test_app: TestClient):
        resp = test_app.get("/ai/proactive-alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data

    def test_group_coordination(self, test_app: TestClient, seeded_db: dict):
        s_id = seeded_db["student"].id
        resp = test_app.get(f"/ai/group-coordination?user_ids={s_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "coordination_score" in data

    def test_signals(self, test_app: TestClient):
        for ep in ["signals", "signals/rush-hour", "signals/slot-suggestions", "signals/reorder-prompts"]:
            resp = test_app.get(f"/ai/{ep}")
            assert resp.status_code == 200
            assert "signals" in resp.json()

    def test_recommendations_by_user_id(self, test_app: TestClient, seeded_db: dict):
        s_id = seeded_db["student"].id
        resp = test_app.get(f"/ai/recommendations/{s_id}")
        assert resp.status_code == 200

    def test_user_facing_smart_suggestions(self, test_app: TestClient):
        endpoints = [
            "vendor-recommendations", "menu-suggestions", "smart-reorder",
            "best-pickup-time", "peak-hour-alerts", "popular-nearby"
        ]
        with patch("app.modules.ai_intelligence.analytics_service.utcnow_naive", return_value=NOW):
            for ep in endpoints:
                resp = test_app.get(f"/ai/{ep}")
                assert resp.status_code == 200

    def test_heuristic_footer_with_dict_responses(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        best_pickup_payload = {
            "best_slot": {
                "slot_id": 1, "vendor_id": v_id, "vendor_name": "V",
                "start_time": "12:00", "end_time": "13:00",
                "available_capacity": 10, "occupancy_rate": 0.5,
                "congestion_level": "LOW", "recommended_reason": "ok",
                "eta_minutes": 15, "delay_risk": "LOW", "score": 0.9,
            },
            "alternative_slots": [],
            "preferred_hour": 12,
            "preferred_hour_source": "history",
        }
        peak_alerts_payload = {
            "is_peak_now": False,
            "peak_periods_today": [],
            "off_peak_windows": [],
            "suggested_action": "none",
        }
        popular_nearby_payload = {
            "food_vendors": [],
            "stationery_vendors": [],
        }
        with patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_demand_planning", return_value={"expected_daily_orders": 10}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_capacity_recommendation", return_value={"vendor_id": v_id, "recommended_capacity": 20, "reasoning": "ok"}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_slot_recommendations", return_value={"recommendations": [], "best_slot_id": 1}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_predictive_eta", return_value={"predicted_eta_minutes": 15, "pickup_window_start": "2024-01-01T12:00:00", "pickup_window_end": "2024-01-01T12:15:00", "delay_risk_level": "LOW"}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_vendor_ranking", return_value={"rankings": []}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_personalization", return_value={"recommended_for_you": [], "smart_suggestions": []}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_reorder_suggestions", return_value={"suggestions": [], "best_time_to_reorder": "12:00"}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_proactive_alerts", return_value={"alerts": []}), \
             patch("app.modules.ai_intelligence.service.AIIntelligenceService.get_group_coordination", return_value={"overlapping_windows": [], "suggested_unified_slot": None, "coordination_score": 1.0}), \
             patch("app.modules.ai_intelligence.analytics_service.AnalyticsService.get_vendor_recommendations", return_value={"recommendations": []}), \
             patch("app.modules.ai_intelligence.analytics_service.AnalyticsService.get_menu_suggestions", return_value={"personalized": [], "trending": []}), \
             patch("app.modules.ai_intelligence.analytics_service.AnalyticsService.get_smart_reorder", return_value={"items": []}), \
             patch("app.modules.ai_intelligence.analytics_service.AnalyticsService.get_best_pickup_time", return_value=best_pickup_payload), \
             patch("app.modules.ai_intelligence.analytics_service.AnalyticsService.get_peak_hour_alerts", return_value=peak_alerts_payload), \
             patch("app.modules.ai_intelligence.analytics_service.AnalyticsService.get_popular_nearby", return_value=popular_nearby_payload):

            assert test_app.get(f"/ai/demand-planning?vendor_id={v_id}").status_code == 200
            assert test_app.get(f"/ai/capacity-recommendation?vendor_id={v_id}").status_code == 200
            assert test_app.get("/ai/slot-recommendations").status_code == 200
            assert test_app.get(f"/ai/predictive-eta?slot_id=1&vendor_id={v_id}").status_code == 200
            assert test_app.get("/ai/vendor-ranking").status_code == 200
            assert test_app.get("/ai/personalization").status_code == 200
            assert test_app.get("/ai/reorder-suggestions").status_code == 200
            assert test_app.get("/ai/proactive-alerts").status_code == 200
            assert test_app.get("/ai/group-coordination?user_ids=1").status_code == 200
            assert test_app.get("/ai/vendor-recommendations").status_code == 200
            assert test_app.get("/ai/menu-suggestions").status_code == 200
            assert test_app.get("/ai/smart-reorder").status_code == 200
            assert test_app.get("/ai/best-pickup-time").status_code == 200
            assert test_app.get("/ai/peak-hour-alerts").status_code == 200
            assert test_app.get("/ai/popular-nearby").status_code == 200

    def test_apply_slot_adjustment(self, test_app: TestClient):
        resp = test_app.post("/ai/apply-slot-adjustment")
        assert resp.status_code == 200
        assert "adjustments" in resp.json()

    def test_apply_slot_adjustment_user_not_found(self, db_session: Session):
        app = FastAPI()
        app.include_router(ai_router)

        app.dependency_overrides[get_db] = lambda: db_session
        for route in ai_router.routes:
            if getattr(route, "path", None) == "/ai/apply-slot-adjustment":
                for dep in route.dependant.dependencies:
                    if dep.call != get_db:
                        app.dependency_overrides[dep.call] = lambda: {"id": 99999, "phone": "+19999999999", "role": "vendor"}

        with TestClient(app) as tc:
            resp = tc.post("/ai/apply-slot-adjustment")
            assert resp.status_code == 404

    def test_vendor_slot_capacity_recommendation(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        resp = test_app.get(f"/ai/vendor-slot-capacity-recommendation?vendor_id={v_id}")
        assert resp.status_code == 200
        assert "recommended_capacity" in resp.json()

    def test_vendor_rush_prediction_with_rush_hours(self, test_app: TestClient, db_session: Session, seeded_db: dict):
        v_id = seeded_db["vendor"].id

        # Mock DB query to return >20 orders (HIGH rush level)
        mock_row1 = MagicMock(hour=12, total_orders=25)
        mock_row2 = MagicMock(hour=13, total_orders=15)

        with patch("sqlalchemy.orm.Query.all", return_value=[mock_row1, mock_row2]):
            resp = test_app.get(f"/ai/vendor-rush-prediction?vendor_id={v_id}")
            assert resp.status_code == 200
            periods = resp.json()["rush_periods"]
            assert len(periods) == 2
            assert periods[0]["rush_level"] == "HIGH"
            assert periods[1]["rush_level"] == "MEDIUM"

    def test_vendor_throughput_prediction_utilization_tiers(self, test_app: TestClient, db_session: Session, seeded_db: dict):
        v_id = seeded_db["vendor"].id

        # Utilization > 80%
        slot_high = Slot(vendor_id=v_id, start_time=NOW, end_time=NOW, max_orders=10, current_orders=9)
        # Utilization > 50%
        slot_med = Slot(vendor_id=v_id, start_time=NOW, end_time=NOW, max_orders=10, current_orders=6)
        # Utilization <= 50%
        slot_low = Slot(vendor_id=v_id, start_time=NOW, end_time=NOW, max_orders=10, current_orders=2)

        with patch("sqlalchemy.orm.Query.all", return_value=[slot_high]):
            resp1 = test_app.get(f"/ai/vendor-throughput-prediction?vendor_id={v_id}")
            assert resp1.json()["recommendation"] == "Increase capacity"

        with patch("sqlalchemy.orm.Query.all", return_value=[slot_med]):
            resp2 = test_app.get(f"/ai/vendor-throughput-prediction?vendor_id={v_id}")
            assert resp2.json()["recommendation"] == "Maintain current capacity"

        with patch("sqlalchemy.orm.Query.all", return_value=[slot_low]):
            resp3 = test_app.get(f"/ai/vendor-throughput-prediction?vendor_id={v_id}")
            assert resp3.json()["recommendation"] == "Consider reducing capacity"

    def test_vendor_throughput_prediction_no_slots(self, test_app: TestClient):
        resp = test_app.get("/ai/vendor-throughput-prediction?vendor_id=99999")
        assert resp.status_code == 200
        assert resp.json()["prediction"] == "Insufficient data"


# ---------------------------------------------------------------------------
# 2. Enhanced ETA Router Endpoints (app/modules/ai_intelligence/enhanced_eta_router.py)
# ---------------------------------------------------------------------------

class TestEnhancedETARouter:

    def test_get_enhanced_eta(self, test_app: TestClient, seeded_db: dict):
        o_id = seeded_db["order"].id
        with patch("app.modules.ai_intelligence.planners.enhanced_eta_engine.utcnow_naive", return_value=NOW):
            resp = test_app.get(f"/ai/enhanced-eta/{o_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == o_id
        assert "predicted_eta_minutes" in data

    def test_get_eta_factors_success(self, test_app: TestClient, seeded_db: dict):
        o_id = seeded_db["order"].id
        with patch("app.modules.ai_intelligence.planners.enhanced_eta_engine.utcnow_naive", return_value=NOW):
            resp = test_app.get(f"/ai/eta-factors/{o_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_id"] == o_id
        assert "menu_items" in data

    def test_get_eta_factors_order_not_found(self, test_app: TestClient):
        resp = test_app.get("/ai/eta-factors/99999")
        assert resp.status_code == 200
        assert resp.json() == {"error": "Order not found"}


# ---------------------------------------------------------------------------
# 3. Vendor Speed Router Endpoints (app/modules/ai_intelligence/vendor_speed_router.py)
# ---------------------------------------------------------------------------

class TestVendorSpeedRouter:

    def test_get_vendor_speed(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        with patch("app.modules.ai_intelligence.vendor_speed_service.utcnow_naive", return_value=NOW):
            resp = test_app.get(f"/ai/vendor-speed/{v_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vendor_id"] == v_id

    def test_get_batch_vendor_speeds(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        with patch("app.modules.ai_intelligence.vendor_speed_service.utcnow_naive", return_value=NOW):
            resp = test_app.get(f"/ai/vendor-speed/batch?vendor_ids={v_id},99999")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_get_waiting_time(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        with patch("app.modules.ai_intelligence.vendor_speed_service.utcnow_naive", return_value=NOW):
            resp = test_app.get(f"/ai/vendor-speed/waiting-time/{v_id}?order_size=2")
        assert resp.status_code == 200
        assert "total_wait_time" in resp.json()

    def test_get_suggested_delay(self, test_app: TestClient, seeded_db: dict):
        v_id = seeded_db["vendor"].id
        with patch("app.modules.ai_intelligence.vendor_speed_service.utcnow_naive", return_value=NOW):
            resp = test_app.get(f"/ai/vendor-speed/suggested-delay/{v_id}")
        assert resp.status_code == 200
        assert "should_delay" in resp.json()

    def test_update_eta_with_speed(self, test_app: TestClient, seeded_db: dict):
        o_id = seeded_db["order"].id
        with patch("app.modules.ai_intelligence.vendor_speed_service.utcnow_naive", return_value=NOW):
            resp = test_app.post(f"/ai/vendor-speed/update-eta/{o_id}")
        assert resp.status_code == 200
        assert resp.json()["order_id"] == o_id
