"""ML-powered prediction service.

Loads trained models from the registry and makes predictions with
confidence scores and explainability.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ml.registry import ModelRegistry
from app.ml.features import (
    extract_eta_features,
    is_rush_hour,
    build_user_item_matrix,
    ETA_FEATURE_NAMES,
)
from app.ml.explain import confidence_score, explain_prediction, get_feature_importance
from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.slots.model import Slot
from app.modules.users.model import User, UserRole
from app.modules.menu.model import MenuItem
from app.modules.feedback.model import VendorReview

logger = logging.getLogger("tnt.ml.predictions")

# ETA_FEATURE_NAMES is imported from app.ml.features


class MLPredictionService:
    """Service that loads ML models and makes predictions with explainability."""

    _models_cache: dict[str, Any] = {}

    def __init__(self, db: Session):
        self.db = db

    def predict(self, model_type: str) -> Optional[tuple[Any, dict[str, Any]]]:
        """Lazy load and cache a model artifact.

        Returns:
            tuple[Any, dict[str, Any]]: The loaded model and its metadata, or None if missing.
        """
        if model_type not in self._models_cache:
            try:
                model_data = ModelRegistry.load(model_type)
                if model_data is not None:
                    self._models_cache[model_type] = model_data
                    logger.info("Successfully loaded and cached ML model: %s", model_type)
                else:
                    self._models_cache[model_type] = None
            except Exception as e:
                logger.error("Failed to lazy load ML model '%s': %s", model_type, e)
                self._models_cache[model_type] = None
        return self._models_cache[model_type]

    # ── ETA Prediction ──────────────────────────────────────────────────

    def predict_eta(self, vendor_id: int, slot_id: int,
                    item_count: int = 1) -> dict[str, Any]:
        """Predict ETA using ML model. Falls back to heuristic if no model."""
        slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return self._default_eta_response("Slot not found")

        now = utcnow_naive()

        features = np.array([[
            float(vendor_id),
            float(slot.current_orders),
            float(slot.current_orders / max(slot.max_orders, 1)),
            float(item_count),
            float(now.hour),
            float(now.weekday()),
            float(1 if is_rush_hour(now) else 0),
        ]])

        # Try to load ML model
        model_data = self.predict("eta_prediction")
        if model_data is not None:
            model, metadata = model_data
            try:
                prediction = float(model.predict(features)[0])
                prediction = max(5, min(prediction, 60))
                conf = confidence_score(model, features[0], prediction)

                # Explainability
                explanation = explain_prediction(model, features[0], ETA_FEATURE_NAMES, prediction)

                return {
                    "method": "ml",
                    "model": metadata.get("version_id", "unknown"),
                    "predicted_eta_minutes": int(round(prediction)),
                    "confidence_score": round(conf, 3),
                    "delay_risk_level": self._risk_level(prediction, slot),
                    "explanation": explanation,
                    "feature_names": ETA_FEATURE_NAMES,
                }
            except Exception as e:
                logger.error("ML ETA prediction failed: %s", e)
                logger.warning("ML ETA prediction failed, falling back to heuristic.")
        else:
            logger.warning("ML model 'eta_prediction' artifact is missing/inactive, falling back to heuristic.")

        # Fallback to heuristic
        return self._heuristic_eta(vendor_id, slot, item_count)

    def _heuristic_eta(self, vendor_id: int, slot: Slot,
                       item_count: int) -> dict[str, Any]:
        """Heuristic fallback ETA calculation."""
        base_prep = 15.0
        queue_factor = 1.0 + (slot.current_orders / max(slot.max_orders, 1))
        efficiency = 1.0
        predicted = int(base_prep * queue_factor * efficiency * (1 + 0.1 * max(0, item_count - 1)))
        predicted = max(5, min(predicted, 60))

        return {
            "method": "heuristic",
            "model": None,
            "predicted_eta_minutes": predicted,
            "confidence_score": 0.5,
            "delay_risk_level": self._risk_level(predicted, slot),
            "explanation": {"prediction": predicted, "top_contributing_features": [], "explanation": "Heuristic fallback"},
            "feature_names": ETA_FEATURE_NAMES,
        }

    def _risk_level(self, eta: float, slot: Slot) -> str:
        util = slot.current_orders / max(slot.max_orders, 1)
        if util > 0.9 and eta > 30:
            return "HIGH"
        if util > 0.7 or eta > 25:
            return "MEDIUM"
        return "LOW"

    def _default_eta_response(self, reason: str) -> dict[str, Any]:
        return {
            "method": "default",
            "model": None,
            "predicted_eta_minutes": 15,
            "confidence_score": 0.3,
            "delay_risk_level": "MEDIUM",
            "explanation": {"prediction": 15, "top_contributing_features": [], "explanation": reason},
            "feature_names": ETA_FEATURE_NAMES,
        }

    # ── Demand Forecasting ──────────────────────────────────────────────

    def forecast_demand(self, vendor_id: int, days_ahead: int = 7) -> dict[str, Any]:
        """Forecast demand for a vendor using ML model."""
        model_data = self.predict(f"demand_forecast_vendor{vendor_id}")
        if model_data is None:
            model_data = self.predict("demand_forecast")
        now = utcnow_naive()
        forecasts = []

        if model_data is not None:
            model, metadata = model_data
            feature_names_cache = metadata.get("features", ["hour", "weekday", "day_of_month", "month", "rush_hour"])

            for d in range(days_ahead):
                day = now + timedelta(days=d)
                for hour in range(6, 23):
                    features = np.array([[
                        float(hour), float(day.weekday()),
                        float(day.day), float(day.month),
                        float(1 if is_rush_hour(day.replace(hour=hour)) else 0),
                    ]])
                    try:
                        pred = max(0, float(model.predict(features)[0]))
                        forecasts.append({
                            "date": day.strftime("%Y-%m-%d"),
                            "hour": hour,
                            "predicted_orders": int(round(pred)),
                        })
                    except Exception as e:
                        logger.error("Demand forecast error: %s", e)

        # If no model or failed, use daily average
        if not forecasts:
            logger.warning(
                "ML demand forecast model artifact is missing or failed for vendor %s, falling back to heuristic.",
                vendor_id,
            )
            thirty_days_ago = now - timedelta(days=30)
            daily_avg = self.db.query(Order.id).filter(
                Order.vendor_id == vendor_id, Order.created_at >= thirty_days_ago
            ).count() / 30.0

            for d in range(days_ahead):
                day = now + timedelta(days=d)
                for hour in [8, 9, 12, 13, 14, 18, 19, 20]:
                    forecasts.append({
                        "date": day.strftime("%Y-%m-%d"),
                        "hour": hour,
                        "predicted_orders": int(round(daily_avg / 8)),
                    })

        return {
            "vendor_id": vendor_id,
            "forecasts": forecasts,
            "method": "ml" if model_data and len(forecasts) > 0 else "heuristic",
            "total_predicted": sum(f["predicted_orders"] for f in forecasts),
        }

    # ── Slot Recommendation ─────────────────────────────────────────────

    def recommend_slot(self, user_id: int) -> dict[str, Any]:
        """Recommend best slot based on ML model and user preferences."""
        model_data = self.predict("slot_recommendation")
        if model_data is None:
            logger.warning("ML slot recommendation model artifact is missing, falling back to heuristic.")
        slots = self.db.query(Slot).filter(
            Slot.status.notin_(["full", "blocked"]),
            Slot.start_time >= utcnow_naive(),
        ).all()

        scored_slots = []
        for slot in slots:
            avg_completion = self.db.query(Order.actual_completion_minutes).filter(
                Order.slot_id == slot.id,
                Order.actual_completion_minutes.isnot(None),
            ).first()
            avg_completion_val = avg_completion[0] if avg_completion else 15.0

            occupancy = slot.current_orders / max(slot.max_orders, 1)
            features = np.array([[
                float(occupancy),
                float(slot.start_time.hour),
                float(slot.start_time.weekday()),
                float(1 if is_rush_hour(slot.start_time) else 0),
                float(avg_completion_val),
                float(slot.max_orders),
            ]])

            ml_score = None
            if model_data is not None:
                model, _ = model_data
                try:
                    ml_score = float(model.predict(features)[0])
                except Exception:
                    pass

            # Composite score (lower is better for occupancy prediction)
            score = ml_score if ml_score is not None else occupancy
            # Invert so lower occupancy = higher recommendation score
            rec_score = 1.0 - score

            # Apply congestion-based ranking
            if occupancy < 0.3:
                congestion_label = "LOW"
            elif occupancy < 0.6:
                congestion_label = "MEDIUM"
            else:
                congestion_label = "HIGH"

            scored_slots.append({
                "slot_id": slot.id,
                "vendor_id": slot.vendor_id,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "recommendation_score": round(rec_score, 3),
                "congestion": congestion_label,
                "occupancy_pct": int(occupancy * 100),
                "eta_estimate": self.predict_eta(slot.vendor_id, slot.id)["predicted_eta_minutes"],
                "reason": self._slot_reason(congestion_label, rec_score),
            })

        scored_slots.sort(key=lambda s: s["recommendation_score"], reverse=True)

        return {
            "recommended_slots": scored_slots[:5],
            "fastest": min(scored_slots, key=lambda s: s["eta_estimate"]) if scored_slots else None,
            "least_crowded": min(scored_slots, key=lambda s: s["occupancy_pct"]) if scored_slots else None,
            "cheapest": None,  # Price not available at slot level
            "method": "ml" if model_data else "heuristic",
        }

    def _slot_reason(self, congestion: str, score: float) -> str:
        if score > 0.8:
            return "Excellent slot choice - low congestion"
        if score > 0.6:
            return f"Good option - {congestion.lower()} congestion"
        if congestion == "HIGH":
            return "High congestion expected - consider alternatives"
        return "Average slot option"

    # ── Personalized Recommendations ─────────────────────────────────────

    def get_personalized_recommendations(self, user_id: int,
                                         limit: int = 10) -> dict[str, Any]:
        """Hybrid recommendation: collaborative filtering + content-based.

        Collaborative: uses user-item interaction matrix with similarity.
        Content-based: matches user's preferred categories and vendors.
        """
        matrix_data = build_user_item_matrix(self.db)
        user_ids = matrix_data["user_ids"]
        item_ids = matrix_data["item_ids"]
        matrix = matrix_data["matrix"]

        # Find user index
        if user_id not in matrix_data["user_idx"]:
            return self._cold_start_recommendations(limit)

        user_idx = matrix_data["user_idx"][user_id]
        user_vector = matrix[user_idx]

        # Collaborative: find similar users
        similarities = []
        for i in range(len(user_ids)):
            if i == user_idx:
                continue
            v1, v2 = matrix[i], user_vector
            dot = np.dot(v1, v2)
            norm = (np.linalg.norm(v1) * np.linalg.norm(v2)) or 1
            sim = dot / norm
            similarities.append((i, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        similar_users = [i for i, _ in similarities[:5]]

        # Items liked by similar users but not by this user
        scores = np.zeros(len(item_ids))
        for su in similar_users:
            scores += matrix[su]
        scores[user_vector > 0] = 0  # exclude already ordered items

        # Content-based boost: user's preferred vendors/categories
        user_orders = self.db.query(Order.vendor_id).filter(
            Order.user_id == user_id,
            Order.status.notin_([OrderStatus.CANCELLED]),
        ).distinct().all()
        preferred_vendors = set(r.vendor_id for r in user_orders)

        # Get menu items for scoring
        items_map = {}
        for iid in item_ids:
            mi = self.db.query(MenuItem).filter(MenuItem.id == iid).first()
            if mi:
                items_map[iid] = mi

        recommendations = []
        for idx, score in enumerate(scores):
            if score <= 0:
                continue
            item_id = item_ids[idx]
            mi = items_map.get(item_id)
            if not mi or not mi.is_available:
                continue

            # Content-based boost
            boost = 1.2 if mi.vendor_id in preferred_vendors else 1.0
            final_score = float(score) * boost

            recommendations.append({
                "item_id": item_id,
                "name": mi.name,
                "vendor_id": mi.vendor_id,
                "price": mi.price,
                "score": round(final_score, 3),
                "reason": "Similar users ordered this" if boost == 1.0 else "From a vendor you like",
            })

        recommendations.sort(key=lambda r: r["score"], reverse=True)
        top_recs = recommendations[:limit]

        # Also get content-based recommendations
        content_recs = self._content_based_recommendations(user_id, preferred_vendors, limit)

        return {
            "collaborative": top_recs,
            "content_based": content_recs[:limit],
            "hybrid": self._merge_recommendations(top_recs, content_recs, limit),
            "method": "collaborative_filtering + content_based",
        }

    def _content_based_recommendations(self, user_id: int,
                                       preferred_vendors: set[int],
                                       limit: int = 10) -> list[dict[str, Any]]:
        """Content-based recommendations based on user's order history preferences."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)

        # Get items user ordered
        ordered_items = self.db.query(OrderItem.menu_item_id).join(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= thirty_days_ago,
            Order.status.notin_([OrderStatus.CANCELLED]),
        ).distinct().all()
        ordered_ids = set(r.menu_item_id for r in ordered_items)

        # Get items from preferred vendors that user hasn't ordered
        from app.modules.menu.model import MenuItem
        candidates = self.db.query(MenuItem).filter(
            MenuItem.vendor_id.in_(preferred_vendors) if preferred_vendors else True,
            MenuItem.id.notin_(ordered_ids) if ordered_ids else True,
            MenuItem.is_available == True,
        ).limit(limit * 2).all()

        return [{
            "item_id": c.id,
            "name": c.name,
            "vendor_id": c.vendor_id,
            "price": c.price,
            "score": 0.7,
            "reason": "From a vendor you frequently order from",
        } for c in candidates]

    def _merge_recommendations(self, collab: list, content: list,
                                limit: int) -> list:
        """Merge collaborative + content-based recommendations."""
        seen = set()
        merged = []
        for rec in collab + content:
            key = (rec["item_id"], rec.get("name"))
            if key not in seen:
                seen.add(key)
                merged.append(rec)
        return merged[:limit]

    def _cold_start_recommendations(self, limit: int) -> dict[str, Any]:
        """Cold-start recommendations for new users with no history."""
        popular = self.db.query(
            MenuItem.id, MenuItem.name, MenuItem.vendor_id,
            MenuItem.price,
        ).filter(MenuItem.is_available == True).order_by(MenuItem.id).limit(limit).all()

        items = [{
            "item_id": mi.id,
            "name": mi.name,
            "vendor_id": mi.vendor_id,
            "price": mi.price,
            "score": 0.5,
            "reason": "Popular on campus",
        } for mi in popular]

        return {
            "collaborative": [],
            "content_based": items,
            "hybrid": items,
            "method": "cold_start_popularity",
        }

    # ── Vendor Ranking ──────────────────────────────────────────────────

    def rank_vendors(self) -> list[dict[str, Any]]:
        """Rank vendors using ML model."""
        model_data = self.predict("vendor_ranking")
        if model_data is None:
            logger.warning("ML vendor ranking model artifact is missing, falling back to heuristic.")
        vendors = self.db.query(User).filter(
            User.role == UserRole.VENDOR, User.is_approved == True
        ).all()

        rankings = []
        for vendor in vendors:
            rating = self.db.query(VendorReview.rating).filter(
                VendorReview.vendor_id == vendor.id
            ).all()
            avg_rating = sum(r[0] for r in rating) / len(rating) if rating else 3.0

            thirty_days_ago = utcnow_naive() - timedelta(days=30)
            completed = self.db.query(Order.id).filter(
                Order.vendor_id == vendor.id,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED, OrderStatus.READY]),
                Order.created_at >= thirty_days_ago,
            ).count()

            total_orders = self.db.query(Order.id).filter(
                Order.vendor_id == vendor.id,
                Order.created_at >= thirty_days_ago,
            ).count()

            cancelled = self.db.query(Order.id).filter(
                Order.vendor_id == vendor.id,
                Order.status == OrderStatus.CANCELLED,
                Order.created_at >= thirty_days_ago,
            ).count()

            repeat = self.db.query(
                Order.user_id, self.db.query(func.count(Order.id)).filter(
                    Order.vendor_id == vendor.id
                ).correlate(Order).as_scalar()
            ).filter(
                Order.vendor_id == vendor.id,
                Order.created_at >= thirty_days_ago,
            ).group_by(Order.user_id).having(func.count(Order.id) > 1).count()

            completion_rate = completed / max(total_orders, 1)
            ml_score = None

            if model_data is not None:
                model, _ = model_data
                try:
                    features = np.array([[
                        float(completion_rate), float(avg_rating),
                        float(repeat / max(total_orders, 1)),
                        float(cancelled), float(0), float(total_orders),
                    ]])
                    ml_score = float(model.predict(features)[0])
                except Exception:
                    pass

            score = round(ml_score * 100, 1) if ml_score else round(completion_rate * 100, 1)
            rankings.append({
                "vendor_id": vendor.id,
                "vendor_name": vendor.name or f"Vendor #{vendor.id}",
                "rank_score": score,
                "avg_rating": round(avg_rating, 1),
                "completion_rate": round(completion_rate, 2),
                "total_orders": total_orders,
                "cancellations": cancelled,
                "method": "ml" if ml_score else "heuristic",
            })

        rankings.sort(key=lambda r: r["rank_score"], reverse=True)
        return rankings

    # ── Fraud Detection ─────────────────────────────────────────────────

    def detect_fraud(self, user_id: int, order_id: int) -> dict[str, Any]:
        """Check if an order/user is potentially fraudulent."""
        model_data = self.predict("fraud_detection")
        if model_data is None:
            logger.warning("ML fraud detection model artifact is missing, falling back to heuristic.")
            return self._heuristic_fraud_check(user_id, order_id)

        model, metadata = model_data
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"is_fraud": False, "reason": "User not found", "score": 0.0}

        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.user_id == user_id, Order.created_at >= thirty_days_ago
        ).scalar() or 0

        cancelled = self.db.query(func.count(Order.id)).filter(
            Order.user_id == user_id, Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0

        total_amount = self.db.query(func.sum(Order.total_amount)).filter(
            Order.user_id == user_id, Order.created_at >= thirty_days_ago
        ).scalar() or 0

        fraud_flagged = self.db.query(func.count(Order.id)).filter(
            Order.user_id == user_id, Order.fraud_flag == True
        ).scalar() or 0

        features = np.array([[
            float(total_orders), float(cancelled),
            float(cancelled / max(total_orders, 1)),
            float(total_amount / max(total_orders, 1)),
            float(1 if user.device_token else 0),
            float(fraud_flagged),
        ]])

        try:
            fraud_prob = float(model.predict_proba(features)[0][1])
        except Exception:
            try:
                fraud_prob = float(model.predict(features)[0])
            except Exception:
                fraud_prob = 0.0

        return {
            "is_fraud": fraud_prob > 0.5,
            "fraud_probability": round(fraud_prob, 3),
            "score": round(fraud_prob, 3),
            "risk_level": "HIGH" if fraud_prob > 0.7 else "MEDIUM" if fraud_prob > 0.3 else "LOW",
            "method": "ml",
            "model": metadata.get("version_id", "unknown"),
        }

    def _heuristic_fraud_check(self, user_id: int, order_id: int) -> dict[str, Any]:
        """Heuristic fraud detection fallback."""
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        order = self.db.query(Order).filter(Order.id == order_id).first()

        if not order:
            return {"is_fraud": False, "reason": "Order not found", "score": 0.0}

        # Heuristic rules
        cancelled_rate = 0.0
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.user_id == user_id, Order.created_at >= thirty_days_ago
        ).scalar() or 0
        cancelled = self.db.query(func.count(Order.id)).filter(
            Order.user_id == user_id, Order.status == OrderStatus.CANCELLED,
            Order.created_at >= thirty_days_ago,
        ).scalar() or 0
        cancelled_rate = cancelled / max(total_orders, 1)

        # Flag if high cancellation rate or no device token
        red_flags = 0
        if cancelled_rate > 0.5:
            red_flags += 1
        if cancelled > 5 and total_orders < 10:
            red_flags += 1
        if order.fraud_flag:
            red_flags += 2

        score = min(1.0, red_flags * 0.33)
        return {
            "is_fraud": score > 0.5,
            "fraud_probability": round(score, 3),
            "score": round(score, 3),
            "risk_level": "HIGH" if score > 0.7 else "MEDIUM" if score > 0.3 else "LOW",
            "method": "heuristic",
            "model": None,
        }

    # ── Registry Status ─────────────────────────────────────────────────

    def get_model_registry_summary(self) -> dict[str, Any]:
        """Get summary of all models in registry."""
        return ModelRegistry.get_registry_summary()
