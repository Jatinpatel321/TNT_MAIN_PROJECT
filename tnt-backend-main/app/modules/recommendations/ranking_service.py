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
            for cat in snapshot.favourite_categories:
                if cat["category"] == menu_item.category:
                    category_score = min(0.2, cat["score"] / 500 * 0.2)
                    break

        # Factor 3: Vendor preference (0-0.2)
        vendor_score = 0.0
        if snapshot and snapshot.favourite_vendors:
            for vendor in snapshot.favourite_vendors:
                if vendor["vendor_id"] == menu_item.vendor_id:
                    vendor_score = min(0.2, vendor["score"] / 500 * 0.2)
                    break

        # Factor 4: Time-of-day preference (0-0.2)
        time_score = 0.0
        if snapshot and snapshot.preferred_timings:
            preferred_hour = snapshot.preferred_timings.get("preferred_hour", 12)
            current_hour = utcnow_naive().hour
            hour_diff = abs(preferred_hour - current_hour)
            if hour_diff <= 2:
                time_score = 0.2
            elif hour_diff <= 4:
                time_score = 0.1

        # Total affinity score
        affinity_score = history_score + category_score + vendor_score + time_score

        return {
            "affinity_score": round(affinity_score, 2),
            "order_count": order_count,
            "last_ordered": order_history.last_ordered.isoformat() if order_history.last_ordered else None,
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