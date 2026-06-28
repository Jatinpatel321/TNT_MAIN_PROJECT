"""
Recommendation Ranking Service
==============================

Advanced ranking system for recommendations with weighted scoring:

Scores:
- Trending score: Based on recent order volume
- Popularity score: Based on total orders and ratings
- Personal affinity score: Based on user preferences and history
- Recency score: Based on how recently user ordered similar items
- Recommendation confidence: Overall confidence in the recommendation

Generates human-readable reasons for each recommendation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.users.model import User
from app.modules.feedback.model import VendorReview
from app.modules.recommendations.models import UserPreferenceSnapshot
from app.modules.slots.model import Slot
import json

logger = logging.getLogger("tnt.recommendations.ranking")


class RecommendationRankingService:
    """Service for ranking and scoring recommendations."""

    def __init__(self, db: Session):
        self.db = db

    # ── Score Calculations ────────────────────────────────────────────────

    def calculate_trending_score(self, menu_item_id: int, days: int = 7) -> Dict[str, Any]:
        """Calculate trending score for a menu item.

        Based on:
        - Order volume in recent days
        - Order growth rate
        - Time-of-day relevance

        Returns:
            - trending_score: 0.0-1.0
            - order_count: Number of orders
            - total_quantity: Total items ordered
            - growth_rate: Order growth rate
        """
        since = utcnow_naive() - timedelta(days=days)
        prev_since = since - timedelta(days=days)  # Previous period for growth

        # Current period orders
        current_orders = (
            self.db.query(
                func.count(OrderItem.id).label("order_count"),
                func.sum(OrderItem.quantity).label("total_qty"),
            )
            .join(Order)
            .filter(
                OrderItem.menu_item_id == menu_item_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .first()
        )

        # Previous period orders (for growth rate)
        prev_orders = (
            self.db.query(func.count(OrderItem.id))
            .join(Order)
            .filter(
                OrderItem.menu_item_id == menu_item_id,
                Order.created_at >= prev_since,
                Order.created_at < since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .scalar() or 0
        )

        order_count = current_orders.order_count or 0
        total_qty = current_orders.total_qty or 0

        # Base score from order volume (max 30 orders = 1.0)
        volume_score = min(1.0, order_count / 30.0)

        # Growth rate
        growth_rate = 0.0
        if prev_orders > 0:
            growth_rate = (order_count - prev_orders) / prev_orders
        elif order_count > 0:
            growth_rate = 1.0  # New trending item

        # Growth bonus (max 0.3)
        growth_bonus = min(0.3, max(0.0, growth_rate * 0.3))

        # Final trending score
        trending_score = min(1.0, volume_score + growth_bonus)

        return {
            "trending_score": round(trending_score, 2),
            "order_count": order_count,
            "total_quantity": total_qty,
            "growth_rate": round(growth_rate, 2),
        }

    def calculate_popularity_score(self, menu_item_id: int) -> Dict[str, Any]:
        """Calculate popularity score for a menu item.

        Based on:
        - Total orders (all time)
        - Average rating
        - Order frequency

        Returns:
            - popularity_score: 0.0-1.0
            - total_orders: All-time orders
            - avg_rating: Average rating
            - rating_count: Number of ratings
        """
        # Total orders
        total_orders = (
            self.db.query(func.count(OrderItem.id))
            .join(Order)
            .filter(
                OrderItem.menu_item_id == menu_item_id,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .scalar() or 0
        )

        # Average rating
        from app.modules.feedback.model import MenuItemReview
        avg_rating = (
            self.db.query(func.avg(MenuItemReview.rating))
            .filter(MenuItemReview.menu_item_id == menu_item_id)
            .scalar() or 0
        )
        rating_count = (
            self.db.query(func.count(MenuItemReview.id))
            .filter(MenuItemReview.menu_item_id == menu_item_id)
            .scalar() or 0
        )

        # Order score (max 100 orders = 1.0)
        order_score = min(1.0, total_orders / 100.0)

        # Rating score (0-5 stars = 0.0-1.0)
        rating_score = float(avg_rating) / 5.0 if avg_rating else 0.0

        # Weighted combination
        popularity_score = (order_score * 0.6) + (rating_score * 0.4)

        return {
            "popularity_score": round(popularity_score, 2),
            "total_orders": total_orders,
            "avg_rating": round(float(avg_rating), 1),
            "rating_count": rating_count,
        }

    def calculate_personal_affinity_score(
        self, user_id: int, menu_item_id: int
    ) -> Dict[str, Any]:
        """Calculate personal affinity score for a user-item pair.

        Based on:
        - User's order history with this item
        - Category preference
        - Vendor preference
        - Time-of-day preference

        Returns:
            - affinity_score: 0.0-1.0
            - order_count: Times user ordered this
            - last_ordered: Last order date
            - factors: Breakdown of scoring factors
        """
        snapshot = (
            self.db.query(UserPreferenceSnapshot)
            .filter(UserPreferenceSnapshot.user_id == user_id)
            .first()
        )

        menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            return {"affinity_score": 0.0, "factors": {}}

        # Factor 1: Direct order history (0-0.4)
        order_history = (
            self.db.query(
                func.count(OrderItem.id).label("order_count"),
                func.max(Order.created_at).label("last_ordered"),
            )
            .join(Order)
            .filter(
                OrderItem.menu_item_id == menu_item_id,
                Order.user_id == user_id,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .first()
        )

        order_count = order_history.order_count or 0
        history_score = min(0.4, order_count * 0.1)  # 10 orders = 1.0

        # Factor 2: Category preference (0-0.2)
        category_score = 0.0
        if snapshot and snapshot.favourite_categories:
            try:
                fav_cats = json.loads(snapshot.favourite_categories) if isinstance(snapshot.favourite_categories, str) else snapshot.favourite_categories
                for cat in fav_cats:
                    if cat["category"] == menu_item.category:
                        category_score = min(0.2, cat["score"] / 500 * 0.2)
                        break
            except Exception:
                pass

        # Factor 3: Vendor preference (0-0.2)
        vendor_score = 0.0
        if snapshot and snapshot.favourite_vendors:
            try:
                fav_vends = json.loads(snapshot.favourite_vendors) if isinstance(snapshot.favourite_vendors, str) else snapshot.favourite_vendors
                for vendor in fav_vends:
                    if vendor["vendor_id"] == menu_item.vendor_id:
                        vendor_score = min(0.2, vendor["score"] / 500 * 0.2)
                        break
            except Exception:
                pass

        # Factor 4: Time-of-day preference (0-0.2)
        time_score = 0.0
        if snapshot and snapshot.preferred_timings:
            try:
                pref_times = json.loads(snapshot.preferred_timings) if isinstance(snapshot.preferred_timings, str) else snapshot.preferred_timings
                preferred_hour = pref_times.get("preferred_hour", 12)
                current_hour = utcnow_naive().hour
                hour_diff = abs(preferred_hour - current_hour)
                if hour_diff <= 2:
                    time_score = 0.2
                elif hour_diff <= 4:
                    time_score = 0.1
            except Exception:
                pass

        # Default heuristic score
        affinity_score = history_score + category_score + vendor_score + time_score
        method = "heuristic"

        # Try ML SVD model inference (AI preference learning)
        try:
            from app.ml.registry import ModelRegistry
            model_data = ModelRegistry.load("recommendation_engine")
            if model_data is not None:
                model_package, _ = model_data
                if model_package.get("type") == "collaborative_filtering_svd":
                    user_encoder = model_package.get("user_encoder", {})
                    item_encoder = model_package.get("item_encoder", {})
                    if user_id in user_encoder and menu_item_id in item_encoder:
                        u_idx = user_encoder[user_id]
                        i_idx = item_encoder[menu_item_id]
                        u_factors = model_package["user_factors"]
                        i_factors = model_package["item_factors"]
                        import numpy as np
                        ml_val = float(np.dot(u_factors[u_idx], i_factors[i_idx]))
                        # interaction strength is capped at 10, scale to 0.0-1.0
                        affinity_score = max(0.0, min(1.0, ml_val / 10.0))
                        method = "ml_svd"
                elif model_package.get("type") == "popularity_based":
                    popularity_list = model_package.get("popularity", [])
                    for rank, pop_item in enumerate(popularity_list):
                        if pop_item.get("item_id") == menu_item_id:
                            affinity_score = max(0.0, 1.0 - (rank / max(len(popularity_list), 1)))
                            method = "ml_popularity"
                            break
        except Exception as e:
            logger.error("Failed ML affinity inference, falling back to heuristic: %s", e)

        return {
            "affinity_score": round(affinity_score, 2),
            "order_count": order_count,
            "last_ordered": order_history.last_ordered.isoformat() if order_history.last_ordered else None,
            "method": method,
            "factors": {
                "history_score": round(history_score, 2),
                "category_score": round(category_score, 2),
                "vendor_score": round(vendor_score, 2),
                "time_score": round(time_score, 2),
            },
        }

    def calculate_recency_score(
        self, user_id: int, menu_item_id: int
    ) -> Dict[str, Any]:
        """Calculate recency score for a user-item pair.

        Based on:
        - Days since last order
        - Order frequency

        Returns:
            - recency_score: 0.0-1.0
            - days_since_last_order: Days since last order
            - last_order_date: Last order date
        """
        last_order = (
            self.db.query(Order.created_at)
            .join(OrderItem)
            .filter(
                OrderItem.menu_item_id == menu_item_id,
                Order.user_id == user_id,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .order_by(Order.created_at.desc())
            .first()
        )

        if not last_order:
            return {
                "recency_score": 0.0,
                "days_since_last_order": None,
                "last_order_date": None,
            }

        last_date = last_order.created_at
        days_since = (utcnow_naive() - last_date).days

        # Recency score: 0 days = 1.0, 30 days = 0.0
        recency_score = max(0.0, 1.0 - (days_since / 30.0))

        return {
            "recency_score": round(recency_score, 2),
            "days_since_last_order": days_since,
            "last_order_date": last_date.isoformat(),
        }

    def calculate_recommendation_confidence(
        self,
        trending_score: float,
        popularity_score: float,
        affinity_score: float,
        recency_score: float,
    ) -> Dict[str, Any]:
        """Calculate overall recommendation confidence.

        Weighted combination:
        - Trending: 20%
        - Popularity: 25%
        - Personal affinity: 35%
        - Recency: 20%

        Returns:
            - confidence: 0.0-1.0
            - confidence_level: HIGH/MEDIUM/LOW
            - score_breakdown: Individual scores
        """
        # Weighted combination
        confidence = (
            trending_score * 0.20 +
            popularity_score * 0.25 +
            affinity_score * 0.35 +
            recency_score * 0.20
        )

        # Confidence level
        if confidence >= 0.7:
            confidence_level = "HIGH"
        elif confidence >= 0.4:
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        return {
            "confidence": round(confidence, 2),
            "confidence_level": confidence_level,
            "score_breakdown": {
                "trending": round(trending_score, 2),
                "popularity": round(popularity_score, 2),
                "affinity": round(affinity_score, 2),
                "recency": round(recency_score, 2),
            },
        }

    # ── Recommendation Reasons ────────────────────────────────────────────

    def generate_recommendation_reason(
        self,
        user_id: int,
        menu_item_id: int,
        scores: Dict[str, Any],
        category: str = "recommended",
    ) -> str:
        """Generate human-readable reason for recommendation.

        Args:
            user_id: User ID
            menu_item_id: Menu item ID
            scores: Score dictionary
            category: Recommendation category

        Returns:
            Human-readable reason string
        """
        reasons = []

        # Get item details
        menu_item = self.db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            return "Recommended for you"

        item_name = menu_item.name

        # Personal affinity reasons
        affinity = scores.get("affinity", {})
        if affinity.get("order_count", 0) > 0:
            reasons.append(f"You've ordered {item_name} {affinity['order_count']} times")
        
        if affinity.get("factors", {}).get("history_score", 0) > 0.3:
            reasons.append(f"You frequently order {item_name}")

        # Recency reasons
        recency = scores.get("recency", {})
        days_since = recency.get("days_since_last_order")
        if days_since is not None:
            if days_since == 0:
                reasons.append(f"You ordered {item_name} today")
            elif days_since == 1:
                reasons.append(f"You ordered {item_name} yesterday")
            elif days_since <= 7:
                reasons.append(f"You ordered {item_name} this week")
            elif days_since <= 30:
                reasons.append(f"You ordered {item_name} recently")

        # Trending reasons
        trending = scores.get("trending", {})
        if trending.get("trending_score", 0) > 0.7:
            reasons.append(f"{item_name} is trending right now")
        elif trending.get("order_count", 0) > 20:
            reasons.append(f"Popular right now")

        # Popularity reasons
        popularity = scores.get("popularity", {})
        if popularity.get("avg_rating", 0) >= 4.5:
            reasons.append(f"Highly rated ({popularity['avg_rating']}★)")
        elif popularity.get("total_orders", 0) > 100:
            reasons.append(f"Popular among students")

        # Time-of-day reasons
        current_hour = utcnow_naive().hour
        if 6 <= current_hour < 11:
            reasons.append("Perfect for breakfast")
        elif 11 <= current_hour < 15:
            reasons.append("Great for lunch")
        elif 15 <= current_hour < 18:
            reasons.append("Good afternoon snack")
        else:
            reasons.append("Perfect for evening")

        # Category-specific reasons
        if menu_item.category:
            if menu_item.category.lower() in ["beverages", "drinks"]:
                reasons.append("Refreshing choice")
            elif menu_item.category.lower() in ["snacks"]:
                reasons.append("Quick bite")
            elif menu_item.category.lower() in ["indian", "south indian"]:
                reasons.append("Authentic taste")

        # Select best reason based on category
        if category == "frequently_ordered":
            if reasons:
                return reasons[0]
            return "You order this often"
        
        elif category == "recommended":
            # Prefer personal reasons
            personal_reasons = [r for r in reasons if "You" in r]
            if personal_reasons:
                return personal_reasons[0]
            if reasons:
                return reasons[0]
            return "Recommended for you"
        
        elif category == "trending":
            if reasons:
                return reasons[0]
            return "Trending now"
        
        elif category == "because_you_ordered":
            # Find items user ordered
            if reasons:
                return f"Because you ordered {item_name}"
            return "Because you ordered similar items"

        # Default
        if reasons:
            return reasons[0]
        return "Recommended for you"

    # ── Public API ────────────────────────────────────────────────────────

    def rank_recommendations(
        self,
        user_id: int,
        items: List[Dict[str, Any]],
        category: str = "recommended",
    ) -> List[Dict[str, Any]]:
        """Rank a list of recommendations with weighted scores.

        Args:
            user_id: User ID
            items: List of recommendation items
            category: Recommendation category

        Returns:
            Ranked and scored recommendations with reasons
        """
        ranked_items = []

        for item in items:
            menu_item_id = item.get("id")
            if not menu_item_id:
                continue

            # Calculate all scores
            trending = self.calculate_trending_score(menu_item_id)
            popularity = self.calculate_popularity_score(menu_item_id)
            affinity = self.calculate_personal_affinity_score(user_id, menu_item_id)
            recency = self.calculate_recency_score(user_id, menu_item_id)

            # Calculate overall confidence
            confidence = self.calculate_recommendation_confidence(
                trending["trending_score"],
                popularity["popularity_score"],
                affinity["affinity_score"],
                recency["recency_score"],
            )

            # Generate reason
            scores_dict = {
                "trending": trending,
                "popularity": popularity,
                "affinity": affinity,
                "recency": recency,
            }
            reason = self.generate_recommendation_reason(
                user_id, menu_item_id, scores_dict, category
            )

            # Calculate final weighted score
            final_score = (
                trending["trending_score"] * 0.20 +
                popularity["popularity_score"] * 0.25 +
                affinity["affinity_score"] * 0.35 +
                recency["recency_score"] * 0.20
            )

            # Merge with original item
            ranked_item = {
                **item,
                "trending_score": trending["trending_score"],
                "popularity_score": popularity["popularity_score"],
                "affinity_score": affinity["affinity_score"],
                "recency_score": recency["recency_score"],
                "confidence": confidence["confidence"],
                "confidence_level": confidence["confidence_level"],
                "score": round(final_score, 2),
                "reason": reason,
                "score_breakdown": confidence["score_breakdown"],
            }

            ranked_items.append(ranked_item)

        # Sort by final score
        ranked_items.sort(key=lambda x: x["score"], reverse=True)

        return ranked_items

    def get_recommendation_insights(
        self, user_id: int, menu_item_id: int
    ) -> Dict[str, Any]:
        """Get detailed insights for a recommendation.

        Returns:
            - all_scores: Complete score breakdown
            - reason: Human-readable reason
            - confidence: Overall confidence
            - insights: Additional insights
        """
        trending = self.calculate_trending_score(menu_item_id)
        popularity = self.calculate_popularity_score(menu_item_id)
        affinity = self.calculate_personal_affinity_score(user_id, menu_item_id)
        recency = self.calculate_recency_score(user_id, menu_item_id)

        confidence = self.calculate_recommendation_confidence(
            trending["trending_score"],
            popularity["popularity_score"],
            affinity["affinity_score"],
            recency["recency_score"],
        )

        scores_dict = {
            "trending": trending,
            "popularity": popularity,
            "affinity": affinity,
            "recency": recency,
        }
        reason = self.generate_recommendation_reason(user_id, menu_item_id, scores_dict)

        # Additional insights
        insights = []

        if trending["trending_score"] > 0.7:
            insights.append("This item is currently trending")
        
        if popularity["avg_rating"] >= 4.5:
            insights.append(f"Highly rated by students ({popularity['avg_rating']}★)")
        
        if affinity["order_count"] > 0:
            insights.append(f"You've ordered this {affinity['order_count']} times")
        
        if recency["days_since_last_order"] and recency["days_since_last_order"] <= 7:
            insights.append("You ordered this recently")

        return {
            "menu_item_id": menu_item_id,
            "scores": {
                "trending": trending,
                "popularity": popularity,
                "affinity": affinity,
                "recency": recency,
            },
            "confidence": confidence,
            "reason": reason,
            "insights": insights,
        }

    def rank_slots(
        self, user_id: int, slots: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank slots using slot_recommendation ML model with fallback to heuristics."""
        from app.ml.registry import ModelRegistry
        import numpy as np

        model_data = None
        try:
            model_data = ModelRegistry.load("slot_recommendation")
        except Exception as e:
            logger.error("Failed to load slot_recommendation model: %s", e)

        ranked_slots = []
        for s_data in slots:
            slot_id = s_data.get("slot_id") or s_data.get("id")
            slot = self.db.query(Slot).filter(Slot.id == slot_id).first()
            if not slot:
                continue

            # Compute features
            avg_completion = self.db.query(func.avg(Order.actual_completion_minutes)).filter(
                Order.slot_id == slot.id,
                Order.actual_completion_minutes.isnot(None),
            ).scalar() or 15.0

            occupancy = slot.current_orders / max(slot.max_orders, 1)
            hour = slot.start_time.hour if slot.start_time else 12
            weekday = slot.start_time.weekday() if slot.start_time else 0
            is_rush = 1 if (12 <= hour <= 14 or 19 <= hour <= 21) else 0

            features = np.array([[
                float(occupancy),
                float(hour),
                float(weekday),
                float(is_rush),
                float(avg_completion),
                float(slot.max_orders),
            ]])

            ml_score = None
            method = "heuristic"
            if model_data is not None:
                try:
                    model, _ = model_data
                    ml_score = float(model.predict(features)[0])
                    # Higher quality score = lower occupancy and wait. Invert occupancy target.
                    score = 1.0 - max(0.0, min(1.0, ml_score))
                    method = "ml"
                except Exception as e:
                    logger.error("Failed ML slot prediction: %s", e)

            if ml_score is None:
                score = 1.0 - occupancy

            ranked_slots.append({
                **s_data,
                "score": round(score, 3),
                "method": method,
            })

        ranked_slots.sort(key=lambda x: x["score"], reverse=True)
        return ranked_slots

    def rank_vendors(
        self, vendors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank vendors using vendor_ranking ML model with fallback."""
        from app.ml.registry import ModelRegistry
        import numpy as np

        model_data = None
        try:
            model_data = ModelRegistry.load("vendor_ranking")
        except Exception as e:
            logger.error("Failed to load vendor_ranking model: %s", e)

        ranked_vendors = []
        for v_data in vendors:
            vendor_id = v_data.get("vendor_id") or v_data.get("id")
            
            # Fetch vendor metrics
            thirty_days_ago = utcnow_naive() - timedelta(days=30)
            total_orders = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id, Order.created_at >= thirty_days_ago
            ).scalar() or 0

            completed = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED, OrderStatus.READY]),
                Order.created_at >= thirty_days_ago,
            ).scalar() or 0

            cancelled = self.db.query(func.count(Order.id)).filter(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CANCELLED,
                Order.created_at >= thirty_days_ago,
            ).scalar() or 0

            repeat_customers = self.db.query(
                Order.user_id
            ).filter(
                Order.vendor_id == vendor_id, Order.created_at >= thirty_days_ago
            ).group_by(Order.user_id).having(func.count(Order.id) > 1).count()

            unique_customers = self.db.query(Order.user_id).filter(
                Order.vendor_id == vendor_id, Order.created_at >= thirty_days_ago
            ).distinct().count()

            avg_rating = self.db.query(func.avg(VendorReview.rating)).filter(
                VendorReview.vendor_id == vendor_id
            ).scalar() or 0.0

            completion_rate = completed / max(total_orders, 1)
            repeat_rate = repeat_customers / max(unique_customers, 1)

            features = np.array([[
                float(completion_rate),
                float(avg_rating),
                float(repeat_rate),
                float(cancelled),
                float(cancelled),
                float(total_orders),
            ]])

            ml_score = None
            method = "heuristic"
            if model_data is not None:
                try:
                    model, _ = model_data
                    ml_score = float(model.predict(features)[0])
                    score = max(0.0, min(100.0, ml_score * 100))
                    method = "ml"
                except Exception as e:
                    logger.error("Failed ML vendor ranking: %s", e)

            if ml_score is None:
                score = completion_rate * 100

            ranked_vendors.append({
                **v_data,
                "score": round(score, 2),
                "method": method,
            })

        ranked_vendors.sort(key=lambda x: x["score"], reverse=True)
        return ranked_vendors

    def rank_offers(
        self, user_id: int, offers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank promotional offers using SVD item affinity."""
        from app.ml.registry import ModelRegistry
        import numpy as np

        model_data = None
        try:
            model_data = ModelRegistry.load("recommendation_engine")
        except Exception as e:
            logger.error("Failed to load recommendation_engine for offers: %s", e)

        user_encoder, item_encoder, u_factors, i_factors = {}, {}, None, None
        if model_data is not None:
            model_package, _ = model_data
            if model_package.get("type") == "collaborative_filtering_svd":
                user_encoder = model_package.get("user_encoder", {})
                item_encoder = model_package.get("item_encoder", {})
                u_factors = model_package["user_factors"]
                i_factors = model_package["item_factors"]

        ranked_offers = []
        for o_data in offers:
            vendor_id = o_data.get("vendor_id")
            discount_val = o_data.get("discount_value") or 10.0

            # Find user affinity for this vendor's menu items
            menu_items = self.db.query(MenuItem).filter(MenuItem.vendor_id == vendor_id).all()
            
            affinity_scores = []
            method = "heuristic"
            if u_factors is not None and user_id in user_encoder:
                for item in menu_items:
                    if item.id in item_encoder:
                        u_idx = user_encoder[user_id]
                        i_idx = item_encoder[item.id]
                        ml_val = float(np.dot(u_factors[u_idx], i_factors[i_idx]))
                        affinity_scores.append(max(0.0, min(1.0, ml_val / 10.0)))
                if affinity_scores:
                    method = "ml_svd"
            
            if not affinity_scores:
                ordered_count = self.db.query(Order).filter(
                    Order.user_id == user_id, Order.vendor_id == vendor_id
                ).count()
                affinity_scores.append(min(1.0, ordered_count / 10.0))

            avg_affinity = sum(affinity_scores) / len(affinity_scores) if affinity_scores else 0.1
            score = avg_affinity * discount_val

            ranked_offers.append({
                **o_data,
                "score": round(score, 2),
                "method": method,
            })

        ranked_offers.sort(key=lambda x: x["score"], reverse=True)
        return ranked_offers