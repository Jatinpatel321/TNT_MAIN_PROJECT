"""
Group AI Coordination Service
==============================

AI-powered coordination for group orders:

Features:
- Suggest best ordering time based on member availability
- Suggest best common pickup slot
- Suggest common menu items across members
- Calculate member availability
- Detect ordering conflicts
- Pickup synchronization

Integrates with existing Group Cart system.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.group_cart.model import Group, GroupMember, GroupCartItem, GroupSlotLock, GroupStatus
from app.modules.orders.model import Order, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.users.model import User
from app.modules.recommendations.models import UserPreferenceSnapshot

logger = logging.getLogger("tnt.group_ai")


class GroupAIService:
    """AI-powered group coordination service."""

    def __init__(self, db: Session):
        self.db = db

    # ── Member Availability Analysis ──────────────────────────────────────

    def analyze_member_availability(self, group_id: int) -> Dict[str, Any]:
        """Analyze availability of all group members.

        Returns:
            - members: List of members with availability scores
            - optimal_ordering_time: Suggested time for group order
            - availability_score: Overall group availability (0.0-1.0)
            - conflicts: List of scheduling conflicts
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        members_data = []
        conflicts = []
        availability_scores = []

        for member in group.members:
            user = member.user
            if not user:
                continue

            # Analyze user's ordering patterns
            availability = self._calculate_user_availability(user.id)
            
            members_data.append({
                "user_id": user.id,
                "user_name": user.name or user.phone,
                "role": member.role.value,
                "availability_score": availability["score"],
                "preferred_hours": availability["preferred_hours"],
                "preferred_days": availability["preferred_days"],
                "conflicts": availability["conflicts"],
            })

            availability_scores.append(availability["score"])
            conflicts.extend(availability["conflicts"])

        # Calculate optimal ordering time
        optimal_time = self._find_optimal_ordering_time(group_id)

        # Overall availability score
        avg_score = sum(availability_scores) / len(availability_scores) if availability_scores else 0.0

        return {
            "group_id": group_id,
            "members": members_data,
            "optimal_ordering_time": optimal_time,
            "availability_score": round(avg_score, 2),
            "conflicts": list(set(conflicts)),  # Unique conflicts
            "member_count": len(members_data),
        }

    def _calculate_user_availability(self, user_id: int) -> Dict[str, Any]:
        """Calculate availability score for a single user.

        Based on:
        - Historical ordering times
        - Preferred pickup hours
        - Current active orders
        - User preferences
        """
        # Get user's ordering history (last 30 days)
        thirty_days_ago = utcnow_naive() - timedelta(days=30)
        
        orders = (
            self.db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= thirty_days_ago,
                Order.status.in_([OrderStatus.COMPLETED, OrderStatus.PICKED]),
            )
            .all()
        )

        # Get user preferences
        prefs = (
            self.db.query(UserPreferenceSnapshot)
            .filter(UserPreferenceSnapshot.user_id == user_id)
            .first()
        )

        # Extract preferred hours from orders
        hour_counts = Counter()
        day_counts = Counter()
        
        for order in orders:
            hour = order.created_at.hour
            day = order.created_at.weekday()
            hour_counts[hour] += 1
            day_counts[day] += 1

        # Get preferred hours (top 3)
        preferred_hours = [hour for hour, _ in hour_counts.most_common(3)]
        preferred_days = [day for day, _ in day_counts.most_common(3)]

        # Check for conflicts (active orders)
        active_orders = (
            self.db.query(func.count(Order.id))
            .filter(
                Order.user_id == user_id,
                Order.status.in_([
                    OrderStatus.PLACED,
                    OrderStatus.CONFIRMED,
                    OrderStatus.PREPARING,
                ]),
            )
            .scalar() or 0
        )

        conflicts = []
        if active_orders > 0:
            conflicts.append(f"Has {active_orders} active order(s)")

        # Calculate availability score (0.0-1.0)
        score = 1.0

        # Reduce score if has active orders
        if active_orders > 0:
            score -= 0.2 * min(active_orders, 3)

        # Reduce score if no ordering history
        if len(orders) == 0:
            score -= 0.3

        # Boost score if consistent ordering pattern
        if len(hour_counts) <= 3:  # Orders within 3 different hours
            score += 0.1

        score = max(0.0, min(1.0, score))

        return {
            "score": score,
            "preferred_hours": preferred_hours,
            "preferred_days": preferred_days,
            "active_orders": active_orders,
            "conflicts": conflicts,
            "order_count": len(orders),
        }

    def _find_optimal_ordering_time(self, group_id: int) -> Dict[str, Any]:
        """Find optimal ordering time for the entire group.

        Considers:
        - All members' preferred hours
        - Peak/off-peak times
        - Vendor availability
        - Slot availability
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {}

        # Collect all members' preferred hours
        all_preferred_hours = []
        for member in group.members:
            availability = self._calculate_user_availability(member.user_id)
            all_preferred_hours.extend(availability["preferred_hours"])

        if not all_preferred_hours:
            # Default to lunch time (12-14)
            return {
                "suggested_hour": 13,
                "suggested_day": 0,  # Monday
                "reasoning": "No history available, suggesting default lunch time",
                "confidence": 0.3,
            }

        # Find most common hour
        hour_counts = Counter(all_preferred_hours)
        best_hour = hour_counts.most_common(1)[0][0]

        # Find best day (prefer weekdays for food, any for stationery)
        hour_counts_day = Counter()
        for member in group.members:
            availability = self._calculate_user_availability(member.user_id)
            for day in availability["preferred_days"]:
                hour_counts_day[day] += 1

        best_day = hour_counts_day.most_common(1)[0][0] if hour_counts_day else 0

        # Calculate confidence
        confidence = min(1.0, len(all_preferred_hours) / (len(group.members) * 3))

        # Determine if it's peak hour
        is_peak = (11 <= best_hour <= 14) or (18 <= best_hour <= 20)
        reasoning = f"Based on {len(all_preferred_hours)} ordering patterns"
        if is_peak:
            reasoning += " (peak hour - expect higher wait times)"

        return {
            "suggested_hour": best_hour,
            "suggested_day": best_day,
            "reasoning": reasoning,
            "confidence": round(confidence, 2),
            "is_peak_hour": is_peak,
        }

    # ── Pickup Slot Suggestions ───────────────────────────────────────────

    def suggest_best_pickup_slot(self, group_id: int, vendor_id: int) -> Dict[str, Any]:
        """Suggest the best pickup slot for the group.

        Considers:
        - Member availability
        - Slot capacity
        - Vendor workload
        - Time-of-day preferences
        - ETA predictions

        Returns:
            - suggested_slot_id
            - suggested_slot_time
            - alternative_slots
            - reasoning
            - confidence
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        # Get member availability
        availability = self.analyze_member_availability(group_id)
        optimal_time = availability.get("optimal_ordering_time", {})

        # Get available slots for vendor
        from app.modules.slots.model import Slot
        from app.modules.ai_intelligence.planners.eta_engine import ETAEngine

        now = utcnow_naive()
        slots = (
            self.db.query(Slot)
            .filter(
                Slot.vendor_id == vendor_id,
                Slot.start_time >= now,
                Slot.current_orders < Slot.max_orders,
            )
            .order_by(Slot.start_time)
            .limit(10)
            .all()
        )

        if not slots:
            return {
                "suggested_slot_id": None,
                "suggested_slot_time": None,
                "reasoning": "No available slots found",
                "confidence": 0.0,
            }

        # Score each slot
        eta_engine = ETAEngine(self.db)
        scored_slots = []

        for slot in slots:
            score = 0.0
            reasons = []

            # Factor 1: Time match with member preferences (0-0.4)
            slot_hour = slot.start_time.hour if isinstance(slot.start_time, datetime) else 12
            if optimal_time.get("suggested_hour") == slot_hour:
                score += 0.4
                reasons.append("Matches member preferences")

            # Factor 2: Capacity availability (0-0.3)
            utilization = slot.current_orders / slot.max_orders if slot.max_orders > 0 else 1.0
            if utilization < 0.5:
                score += 0.3
                reasons.append("Low utilization")
            elif utilization < 0.8:
                score += 0.2
                reasons.append("Moderate utilization")

            # Factor 3: ETA prediction (0-0.2)
            eta_prediction = eta_engine.predict_eta(slot.id, vendor_id)
            eta = eta_prediction.get("predicted_eta_minutes", 15)
            if eta <= 15:
                score += 0.2
                reasons.append("Fast ETA")
            elif eta <= 25:
                score += 0.1
                reasons.append("Moderate ETA")

            # Factor 4: Time buffer (0-0.1)
            time_until_slot = (slot.start_time - now).total_seconds() / 60.0
            if 15 <= time_until_slot <= 120:  # 15 min to 2 hours
                score += 0.1
                reasons.append("Good time buffer")

            scored_slots.append({
                "slot_id": slot.id,
                "score": score,
                "slot_time": slot.start_time.isoformat() if isinstance(slot.start_time, datetime) else str(slot.start_time),
                "reasons": reasons,
                "utilization": round(utilization, 2),
                "eta_minutes": eta,
            })

        # Sort by score
        scored_slots.sort(key=lambda x: x["score"], reverse=True)

        best_slot = scored_slots[0]
        alternatives = scored_slots[1:4]  # Top 3 alternatives

        return {
            "group_id": group_id,
            "suggested_slot_id": best_slot["slot_id"],
            "suggested_slot_time": best_slot["slot_time"],
            "suggested_slot_score": round(best_slot["score"], 2),
            "reasoning": best_slot["reasons"],
            "confidence": round(best_slot["score"], 2),
            "alternatives": alternatives,
            "member_availability": optimal_time,
        }

    # ── Common Menu Item Suggestions ──────────────────────────────────────

    def suggest_common_menu_items(self, group_id: int, vendor_id: int, limit: int = 10) -> Dict[str, Any]:
        """Suggest menu items that are common across group members.

        Uses:
        - Member order history
        - Preference snapshots
        - Co-occurrence patterns
        - Popular items

        Returns:
            - suggested_items: List of common items
            - member_preferences: Breakdown by member
            - conflicts: Conflicting preferences
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        # Collect all members' favourite items
        member_favourites = {}
        all_items = Counter()

        for member in group.members:
            user = member.user
            if not user:
                continue

            # Get user's preference snapshot
            prefs = (
                self.db.query(UserPreferenceSnapshot)
                .filter(UserPreferenceSnapshot.user_id == user.id)
                .first()
            )

            if prefs and prefs.favourite_menu_items:
                favourites = [item["item_id"] for item in prefs.favourite_menu_items[:5]]
                member_favourites[user.id] = favourites
                all_items.update(favourites)

        # Find items that appear in multiple members' favourites
        common_items = []
        for item_id, count in all_items.items():
            if count >= 2:  # At least 2 members like it
                menu_item = self.db.query(MenuItem).filter(MenuItem.id == item_id).first()
                if menu_item and menu_item.is_available:
                    # Find which members like this item
                    liking_members = [
                        uid for uid, favs in member_favourites.items() if item_id in favs
                    ]

                    common_items.append({
                        "item_id": item_id,
                        "item_name": menu_item.name,
                        "vendor_id": menu_item.vendor_id,
                        "price": menu_item.price,
                        "category": menu_item.category,
                        "liking_members": len(liking_members),
                        "total_members": len(group.members),
                        "popularity_score": count / len(group.members),
                        "image_url": menu_item.image_url,
                    })

        # Sort by popularity
        common_items.sort(key=lambda x: x["popularity_score"], reverse=True)

        # Detect conflicts (members with no overlap)
        conflicts = []
        if len(common_items) == 0:
            conflicts.append("No common preferences found among members")

        return {
            "group_id": group_id,
            "suggested_items": common_items[:limit],
            "member_preferences": {
                str(uid): favs for uid, favs in member_favourites.items()
            },
            "conflicts": conflicts,
            "total_suggestions": len(common_items),
        }

    # ── Ordering Conflict Detection ───────────────────────────────────────

    def detect_ordering_conflicts(self, group_id: int) -> Dict[str, Any]:
        """Detect potential ordering conflicts in the group.

        Conflicts:
        - Different vendor preferences
        - Conflicting time preferences
        - Dietary restrictions
        - Budget constraints
        - Duplicate items

        Returns:
            - conflicts: List of detected conflicts
            - severity: LOW, MEDIUM, HIGH
            - suggestions: How to resolve conflicts
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        conflicts = []
        suggestions = []

        # Check 1: Vendor diversity in cart
        cart_vendors = set()
        for item in group.cart_items:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if menu_item:
                cart_vendors.add(menu_item.vendor_id)

        if len(cart_vendors) > 1:
            conflicts.append({
                "type": "MULTIPLE_VENDORS",
                "severity": "MEDIUM",
                "description": f"Cart has items from {len(cart_vendors)} different vendors",
                "affected_members": [],
            })
            suggestions.append("Consider consolidating orders from a single vendor for faster pickup")

        # Check 2: Time conflicts
        availability = self.analyze_member_availability(group_id)
        if len(availability.get("conflicts", [])) > 0:
            conflicts.append({
                "type": "TIME_CONFLICT",
                "severity": "HIGH",
                "description": "Some members have scheduling conflicts",
                "details": availability["conflicts"],
                "affected_members": [],
            })
            suggestions.append("Consider rescheduling to a time when all members are available")

        # Check 3: Dietary restrictions
        dietary_issues = self._check_dietary_conflicts(group)
        if dietary_issues:
            conflicts.append({
                "type": "DIETARY_CONFLICT",
                "severity": "HIGH",
                "description": "Dietary restriction conflicts detected",
                "details": dietary_issues,
                "affected_members": [],
            })
            suggestions.append("Ensure menu items accommodate all dietary restrictions")

        # Check 4: Duplicate items
        item_counts = Counter([item.menu_item_id for item in group.cart_items])
        duplicates = {item_id: count for item_id, count in item_counts.items() if count > 1}
        if duplicates:
            conflicts.append({
                "type": "DUPLICATE_ITEMS",
                "severity": "LOW",
                "description": f"Found {len(duplicates)} duplicate items in cart",
                "details": duplicates,
                "affected_members": [],
            })
            suggestions.append("Review duplicate items to avoid over-ordering")

        # Check 5: Budget imbalance
        member_totals = {}
        for item in group.cart_items:
            if item.owner_id not in member_totals:
                member_totals[item.owner_id] = 0
            member_totals[item.owner_id] += item.price_at_time * item.quantity

        if member_totals:
            max_total = max(member_totals.values())
            min_total = min(member_totals.values())
            if max_total > min_total * 2:  # 2x difference
                conflicts.append({
                    "type": "BUDGET_IMBALANCE",
                    "severity": "LOW",
                    "description": "Large difference in order totals among members",
                    "details": {
                        "max": max_total,
                        "min": min_total,
                        "ratio": round(max_total / min_total, 1),
                    },
                    "affected_members": [],
                })
                suggestions.append("Consider equal payment split to balance costs")

        # Overall severity
        severity = "LOW"
        if any(c["severity"] == "HIGH" for c in conflicts):
            severity = "HIGH"
        elif any(c["severity"] == "MEDIUM" for c in conflicts):
            severity = "MEDIUM"

        return {
            "group_id": group_id,
            "conflicts": conflicts,
            "severity": severity,
            "suggestions": suggestions,
            "total_conflicts": len(conflicts),
        }

    def _check_dietary_conflicts(self, group: Group) -> List[str]:
        """Check for dietary restriction conflicts."""
        issues = []

        for item in group.cart_items:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if not menu_item:
                continue

            # Check if item is vegetarian
            if hasattr(menu_item, 'is_veg') and menu_item.is_veg is False:
                # Check if any member has vegetarian preference
                for member in group.members:
                    prefs = (
                        self.db.query(UserPreferenceSnapshot)
                        .filter(UserPreferenceSnapshot.user_id == member.user_id)
                        .first()
                    )
                    if prefs and prefs.is_veg_preferred == 1:
                        issues.append(f"Item '{menu_item.name}' may not be suitable for vegetarian member")
                        break

        return issues

    # ── Pickup Synchronization ────────────────────────────────────────────

    def calculate_pickup_synchronization(self, group_id: int) -> Dict[str, Any]:
        """Calculate pickup synchronization metrics.

        Returns:
            - synchronization_score: How well orders can be synchronized (0.0-1.0)
            - estimated_pickup_time: When all orders will be ready
            - pickup_windows: Individual pickup windows
            - synchronization_plan: Recommended pickup strategy
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        if not group.slot_lock:
            return {
                "group_id": group_id,
                "synchronization_score": 0.0,
                "error": "No slot locked for group",
            }

        slot = group.slot_lock.slot
        slot_start = slot.start_time if isinstance(slot.start_time, datetime) else datetime.combine(datetime.today(), slot.start_time)

        # Get all cart items and their ETAs
        from app.modules.ai_intelligence.planners.eta_engine import ETAEngine
        eta_engine = ETAEngine(self.db)

        pickup_windows = []
        max_eta = 0

        for item in group.cart_items:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if not menu_item:
                continue

            # Predict ETA for this item
            eta_prediction = eta_engine.predict_eta(slot.id, menu_item.vendor_id)
            eta = eta_prediction.get("predicted_eta_minutes", 15)

            pickup_time = slot_start + timedelta(minutes=eta)
            max_eta = max(max_eta, eta)

            pickup_windows.append({
                "menu_item_id": item.menu_item_id,
                "item_name": menu_item.name,
                "owner_id": item.owner_id,
                "eta_minutes": eta,
                "pickup_time": pickup_time.isoformat(),
            })

        # Calculate synchronization score
        if not pickup_windows:
            sync_score = 0.0
        else:
            # Score based on how close ETAs are
            eta_values = [w["eta_minutes"] for w in pickup_windows]
            eta_range = max(eta_values) - min(eta_values)
            
            # Lower range = better synchronization
            if eta_range <= 5:
                sync_score = 1.0
            elif eta_range <= 10:
                sync_score = 0.8
            elif eta_range <= 20:
                sync_score = 0.6
            else:
                sync_score = 0.4

        # Estimated pickup time (when latest item is ready)
        estimated_pickup = slot_start + timedelta(minutes=max_eta)

        # Synchronization plan
        if sync_score >= 0.8:
            plan = "EXCELLENT"
            strategy = "All items will be ready around the same time. Single pickup recommended."
        elif sync_score >= 0.6:
            plan = "GOOD"
            strategy = "Items ready within 10 minutes. Coordinated pickup recommended."
        elif sync_score >= 0.4:
            plan = "MODERATE"
            strategy = "Items have varying ETAs. Staggered pickup may be needed."
        else:
            plan = "POOR"
            strategy = "Large ETA variance. Consider splitting into multiple orders."

        return {
            "group_id": group_id,
            "synchronization_score": round(sync_score, 2),
            "estimated_pickup_time": estimated_pickup.isoformat(),
            "pickup_windows": pickup_windows,
            "synchronization_plan": plan,
            "strategy": strategy,
            "eta_range": max_eta - min(w["eta_minutes"] for w in pickup_windows) if pickup_windows else 0,
        }

    # ── Public API ────────────────────────────────────────────────────────

    def get_group_ai_suggestions(self, group_id: int) -> Dict[str, Any]:
        """Get comprehensive AI suggestions for group coordination.

        This is the main entry point for group AI analysis.

        Returns:
            - member_availability
            - optimal_ordering_time
            - suggested_pickup_slot
            - common_menu_items
            - ordering_conflicts
            - pickup_synchronization
            - overall_recommendations
        """
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return {"error": "Group not found"}

        # Get vendor from cart items
        vendor_id = None
        if group.cart_items:
            menu_item = self.db.query(MenuItem).filter(MenuItem.id == group.cart_items[0].menu_item_id).first()
            if menu_item:
                vendor_id = menu_item.vendor_id

        # Analyze all aspects
        availability = self.analyze_member_availability(group_id)
        optimal_time = availability.get("optimal_ordering_time", {})
        
        slot_suggestion = None
        if vendor_id:
            slot_suggestion = self.suggest_best_pickup_slot(group_id, vendor_id)
        
        common_items = self.suggest_common_menu_items(group_id, vendor_id) if vendor_id else {}
        conflicts = self.detect_ordering_conflicts(group_id)
        sync = self.calculate_pickup_synchronization(group_id)

        # Generate overall recommendations
        recommendations = self._generate_recommendations(
            availability, optimal_time, slot_suggestion, conflicts, sync
        )

        return {
            "group_id": group_id,
            "group_name": group.name,
            "member_count": len(group.members),
            "member_availability": availability,
            "optimal_ordering_time": optimal_time,
            "suggested_pickup_slot": slot_suggestion,
            "common_menu_items": common_items,
            "ordering_conflicts": conflicts,
            "pickup_synchronization": sync,
            "overall_recommendations": recommendations,
        }

    def _generate_recommendations(
        self,
        availability: Dict[str, Any],
        optimal_time: Dict[str, Any],
        slot_suggestion: Optional[Dict[str, Any]],
        conflicts: Dict[str, Any],
        sync: Dict[str, Any],
    ) -> List[str]:
        """Generate overall recommendations for the group."""
        recommendations = []

        # Availability recommendations
        if availability.get("availability_score", 0) < 0.7:
            recommendations.append("Some members have scheduling conflicts. Consider rescheduling.")

        # Time recommendations
        if optimal_time.get("is_peak_hour"):
            recommendations.append("Suggested time is during peak hours. Expect longer wait times.")

        # Slot recommendations
        if slot_suggestion and slot_suggestion.get("confidence", 0) < 0.5:
            recommendations.append("Limited slot availability. Consider alternative times.")

        # Conflict recommendations
        if conflicts.get("severity") == "HIGH":
            recommendations.append("Critical conflicts detected. Review before proceeding.")
        elif conflicts.get("severity") == "MEDIUM":
            recommendations.append("Some issues detected. Review suggestions for improvement.")

        # Synchronization recommendations
        sync_score = sync.get("synchronization_score", 0)
        if sync_score < 0.6:
            recommendations.append("Orders may not be ready simultaneously. Consider staggered pickup.")

        if not recommendations:
            recommendations.append("Group is well-coordinated. Proceed with ordering!")

        return recommendations

    def save_ai_suggestions(self, group_id: int, suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Save AI suggestions to database for tracking.

        Args:
            group_id: Group ID
            suggestions: AI suggestions to save

        Returns:
            - saved: Success status
            - suggestion_id: ID of saved suggestion
        """
        # This would typically save to a GroupAISuggestion table
        # For now, we'll just log it
        logger.info(f"Saving AI suggestions for group {group_id}: {suggestions}")

        return {
            "saved": True,
            "group_id": group_id,
            "suggestions": suggestions,
        }