"""
TNT Recommendation Engine
=========================

Three-layer recommendation strategy:

1. **Association rules** – hand-curated "bought X → suggest Y" pairs derived
   from campus food-court patterns.  Cheap, instant, always available.

2. **Collaborative popularity** – items most ordered across *all* users in the
   last 7 / 30 days, weighted by recency.  Captures "trending" campus items.

3. **Personalised history** – items the target user ordered before, ranked by
   frequency × recency.  Returns items the user likes but hasn't re-ordered
   in a while, plus associated pairings.

All three are combined, de-duplicated, and returned as:
    top_recommended   – best overall picks for this user
    trending_items    – campus-wide hot sellers
    personalized_items – tailored to this user's habits
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from app.modules.menu.image_utils import menu_image_for
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus

# Ensure Group/GroupMember models are registered so SQLAlchemy can resolve
# User.owned_groups / User.group_memberships relationships during queries.
import app.modules.group_cart.model as _  # noqa: F401


# ─── Association rules ────────────────────────────────────────────────────
# key = lowercase item name → list of suggested item names
# These are the campus food-court combos students actually buy together.

ASSOCIATION_RULES: dict[str, list[str]] = {
    # Burgers & fast food
    "burger":           ["Fries", "Cold Coffee"],
    "cheese burger":    ["Fries", "Cold Coffee"],
    "veg burger":       ["Fries", "Masala Chai"],
    "chicken burger":   ["Fries", "Cold Coffee"],
    "paneer burger":    ["Fries", "Iced Lemon Tea"],
    # South Indian
    "dosa":             ["Filter Coffee"],
    "masala dosa":      ["Filter Coffee", "Vada"],
    "plain dosa":       ["Filter Coffee", "Sambar Vada"],
    "idli":             ["Filter Coffee", "Vada"],
    "uttapam":          ["Filter Coffee"],
    "vada":             ["Filter Coffee", "Sambar"],
    # Italian
    "pasta":            ["Garlic Bread"],
    "white sauce pasta":["Garlic Bread", "Cold Coffee"],
    "red sauce pasta":  ["Garlic Bread", "Iced Tea"],
    "penne pasta":      ["Garlic Bread"],
    "pizza":            ["Garlic Bread", "Cold Coffee"],
    # Indian mains
    "biryani":          ["Raita", "Mirchi Ka Salan"],
    "chicken biryani":  ["Raita", "Cold Drink"],
    "veg biryani":      ["Raita", "Papad"],
    "paneer biryani":   ["Raita", "Lassi"],
    "thali":            ["Lassi", "Papad"],
    "paneer butter masala": ["Butter Naan", "Jeera Rice"],
    "dal makhani":      ["Butter Naan", "Jeera Rice"],
    "chole bhature":    ["Lassi"],
    "rajma chawal":     ["Raita", "Papad"],
    # Snacks
    "samosa":           ["Masala Chai", "Green Chutney"],
    "samosa (2 pcs)":   ["Masala Chai"],
    "veg frankie":      ["Cold Coffee"],
    "spring roll":      ["Sweet Chilli Sauce", "Iced Tea"],
    "fries":            ["Cold Coffee", "Cheese Dip"],
    "garlic bread":     ["Cold Coffee"],
    # Beverages pair-backs
    "cold coffee":      ["Samosa (2 pcs)", "Fries"],
    "masala chai":      ["Samosa (2 pcs)", "Veg Puff"],
    "filter coffee":    ["Dosa", "Vada"],
    "iced lemon tea":   ["Spring Roll"],
    # Wraps / rolls
    "chicken roll":     ["Cold Coffee", "Fries"],
    "paneer roll":      ["Masala Chai"],
    "egg roll":         ["Cold Coffee"],
    # Chinese
    "noodles":          ["Manchurian", "Spring Roll"],
    "fried rice":       ["Manchurian", "Sweet Corn Soup"],
    "manchurian":       ["Fried Rice"],
}


def _normalise(name: str) -> str:
    """Lowercase + strip for matching."""
    return (name or "").lower().strip()


class RecommendationEngine:
    """Stateless engine — instantiate with a DB session, call `recommend()`."""

    def __init__(self, db: Session):
        self._db = db

    # ── public API ────────────────────────────────────────────────────────

    def recommend(self, user_id: int, limit: int = 8) -> dict[str, Any]:
        """Return the full recommendation payload for one user."""
        history_items = self._user_order_history(user_id)
        trending = self._trending_items(days=7, limit=limit)
        popular = self._popular_items(days=30, limit=limit)
        personalised = self._personalised_items(user_id, history_items, limit=limit)
        top = self._top_recommended(user_id, history_items, trending, personalised, limit=limit)

        # When all layers are empty (fresh DB), surface demo recommendations
        # so the frontend always has something to render.
        if not top and not trending and not personalised:
            top, trending, personalised = self._demo_recommendations()
            popular = trending  # reuse trending as popular in demo mode

        return {
            "user_id": user_id,
            # Primary keys (required by API contract)
            "recommended_items": top,
            "trending_items": trending,
            "popular_items": popular,
            # Backward-compatible aliases
            "top_recommended": top,
            "personalized_items": personalised,
        }

    # ── demo / cold-start fallback (no DB data at all) ────────────────────

    @staticmethod
    def _demo_recommendations() -> tuple[list[dict], list[dict], list[dict]]:
        """Hard-coded recs so the endpoint is never empty on a fresh install."""
        _demo = [
              {"id": None, "name": "Chicken Biryani", "price": 120, "image_url": menu_image_for("Chicken Biryani"), "vendor_id": None,
             "reason": "Campus bestseller", "score": 0.95, "is_available": True,
             "pairs_with": ["Raita", "Mirchi Ka Salan"]},
              {"id": None, "name": "Masala Chai", "price": 15, "image_url": menu_image_for("Masala Chai"), "vendor_id": None,
             "reason": "Morning favourite", "score": 0.92, "is_available": True,
             "pairs_with": ["Samosa (2 pcs)", "Veg Puff"]},
              {"id": None, "name": "Burger", "price": 80, "image_url": menu_image_for("Burger"), "vendor_id": None,
             "reason": "Pairs great with Fries + Cold Coffee", "score": 0.90, "is_available": True,
             "pairs_with": ["Fries", "Cold Coffee"]},
              {"id": None, "name": "Dosa", "price": 50, "image_url": menu_image_for("Dosa"), "vendor_id": None,
             "reason": "Pairs with Filter Coffee", "score": 0.88, "is_available": True,
             "pairs_with": ["Filter Coffee"]},
              {"id": None, "name": "Pasta", "price": 90, "image_url": menu_image_for("Pasta"), "vendor_id": None,
             "reason": "Pairs with Garlic Bread", "score": 0.85, "is_available": True,
             "pairs_with": ["Garlic Bread"]},
              {"id": None, "name": "Cold Coffee", "price": 60, "image_url": menu_image_for("Cold Coffee"), "vendor_id": None,
             "reason": "Trending on campus", "score": 0.83, "is_available": True,
             "pairs_with": ["Samosa (2 pcs)", "Fries"]},
              {"id": None, "name": "Veg Frankie", "price": 45, "image_url": menu_image_for("Veg Frankie"), "vendor_id": None,
             "reason": "Quick grab-n-go", "score": 0.80, "is_available": True,
             "pairs_with": ["Cold Coffee"]},
              {"id": None, "name": "Paneer Butter Masala", "price": 110, "image_url": menu_image_for("Paneer Butter Masala"), "vendor_id": None,
             "reason": "Comfort food favourite", "score": 0.78, "is_available": True,
             "pairs_with": ["Butter Naan", "Jeera Rice"]},
        ]
        top = _demo[:5]
        trending = _demo[:6]
        personalised = _demo[2:7]
        return top, trending, personalised

    # ── Layer 1: association rules ────────────────────────────────────────

    def _apply_rules(self, item_names: list[str]) -> list[dict[str, Any]]:
        """Given names the user bought, return associated suggestions."""
        suggested_names: list[str] = []
        seen: set[str] = set()
        for name in item_names:
            for rule_name in ASSOCIATION_RULES.get(_normalise(name), []):
                key = _normalise(rule_name)
                if key not in seen:
                    seen.add(key)
                    suggested_names.append(rule_name)

        # Try to look up real menu items with those names
        if not suggested_names:
            return []

        items = (
            self._db.query(MenuItem)
            .filter(
                func.lower(MenuItem.name).in_([_normalise(n) for n in suggested_names]),
                MenuItem.is_available == True,
            )
            .all()
        )

        # Build lookup for DB items
        db_map: dict[str, MenuItem] = {_normalise(i.name): i for i in items}
        results: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        for sname in suggested_names:
            mi = db_map.get(_normalise(sname))
            if mi and mi.id not in seen_ids:
                seen_ids.add(mi.id)
                results.append(self._item_to_dict(mi, reason="Pairs well with your order"))
            elif not mi:
                # Still surface the suggestion even if not in current menu
                pairs = ASSOCIATION_RULES.get(_normalise(sname), [])
                results.append({
                    "id": None,
                    "name": sname,
                    "price": None,
                    "image_url": None,
                    "vendor_id": None,
                    "vendor_name": None,
                    "reason": "Pairs well with your order",
                    "score": 0.7,
                    "pairs_with": pairs if pairs else None,
                })
        return results

    # ── Layer 2: trending / popular ───────────────────────────────────────

    def _popular_items(self, days: int = 30, limit: int = 8) -> list[dict[str, Any]]:
        """Top-ordered available menu items in the last `days` days (broader window than trending)."""
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            self._db.query(
                OrderItem.menu_item_id,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.count(OrderItem.id).label("order_count"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.created_at >= since)
            .group_by(OrderItem.menu_item_id)
            .order_by(desc("total_qty"))
            .limit(limit * 2)
            .all()
        )

        if not rows:
            return self._fallback_popular(limit)

        item_ids = [r[0] for r in rows]
        items_by_id = {
            mi.id: mi
            for mi in self._db.query(MenuItem)
            .filter(MenuItem.id.in_(item_ids), MenuItem.is_available == True)
            .all()
        }

        results: list[dict[str, Any]] = []
        for menu_item_id, total_qty, order_count in rows:
            mi = items_by_id.get(menu_item_id)
            if mi:
                d = self._item_to_dict(mi, reason="Popular on campus")
                d["order_count"] = int(order_count)
                d["score"] = round(min(1.0, int(total_qty) / 80), 2)
                results.append(d)
            if len(results) >= limit:
                break

        return results if results else self._fallback_popular(limit)

    def _trending_items(self, days: int = 7, limit: int = 8) -> list[dict[str, Any]]:
        """Top-ordered available menu items in the last `days` days."""
        since = datetime.utcnow() - timedelta(days=days)

        rows = (
            self._db.query(
                OrderItem.menu_item_id,
                func.sum(OrderItem.quantity).label("total_qty"),
                func.count(OrderItem.id).label("order_count"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.created_at >= since)
            .group_by(OrderItem.menu_item_id)
            .order_by(desc("total_qty"))
            .limit(limit * 2)  # over-fetch to filter out unavailable
            .all()
        )

        if not rows:
            return self._fallback_popular(limit)

        item_ids = [r[0] for r in rows]
        items_by_id = {
            mi.id: mi
            for mi in self._db.query(MenuItem)
            .filter(MenuItem.id.in_(item_ids), MenuItem.is_available == True)
            .all()
        }

        results: list[dict[str, Any]] = []
        for menu_item_id, total_qty, order_count in rows:
            mi = items_by_id.get(menu_item_id)
            if mi:
                d = self._item_to_dict(mi, reason="Trending on campus")
                d["order_count"] = int(order_count)
                d["score"] = round(min(1.0, int(total_qty) / 50), 2)
                results.append(d)
            if len(results) >= limit:
                break

        return results if results else self._fallback_popular(limit)

    def _fallback_popular(self, limit: int) -> list[dict[str, Any]]:
        """If no recent orders, return the first available menu items."""
        items = (
            self._db.query(MenuItem)
            .filter(MenuItem.is_available == True)
            .order_by(MenuItem.id)
            .limit(limit)
            .all()
        )
        return [self._item_to_dict(mi, reason="Popular on campus") for mi in items]

    # ── Layer 3: personalised ─────────────────────────────────────────────

    def _personalised_items(
        self, user_id: int, history_items: list[dict[str, Any]], limit: int = 8,
    ) -> list[dict[str, Any]]:
        """Items this user ordered most, plus rule-based pairings."""
        if not history_items:
            # Cold start – return association-based recs from most popular items
            return self._cold_start_recs(limit)

        # Frequency map
        freq: Counter[int] = Counter()
        name_map: dict[int, str] = {}
        for h in history_items:
            freq[h["menu_item_id"]] += h["quantity"]
            name_map[h["menu_item_id"]] = h["name"]

        top_ids = [mid for mid, _ in freq.most_common(limit)]
        items_by_id = {
            mi.id: mi
            for mi in self._db.query(MenuItem)
            .filter(MenuItem.id.in_(top_ids), MenuItem.is_available == True)
            .all()
        }

        results: list[dict[str, Any]] = []
        seen_ids: set[int] = set()

        # Add the user's favourites
        for mid in top_ids:
            mi = items_by_id.get(mid)
            if mi and mi.id not in seen_ids:
                seen_ids.add(mi.id)
                d = self._item_to_dict(mi, reason="You order this often")
                d["times_ordered"] = freq[mid]
                d["score"] = round(min(1.0, freq[mid] / 10), 2)
                results.append(d)

        # Inject association-rule pairings from user's history items
        ordered_names = [name_map[mid] for mid in top_ids if mid in name_map]
        assoc = self._apply_rules(ordered_names)
        for a in assoc:
            aid = a.get("id")
            if aid and aid not in seen_ids:
                seen_ids.add(aid)
                results.append(a)
            elif not aid:
                results.append(a)
            if len(results) >= limit:
                break

        return results[:limit]

    def _cold_start_recs(self, limit: int) -> list[dict[str, Any]]:
        """For new users with zero history: serve popular + rule pairings."""
        popular = self._fallback_popular(limit)
        names = [p["name"] for p in popular if p.get("name")]
        assoc = self._apply_rules(names)
        # De-dup
        seen: set[str] = {_normalise(p["name"]) for p in popular}
        for a in assoc:
            if _normalise(a["name"]) not in seen:
                seen.add(_normalise(a["name"]))
                popular.append(a)
            if len(popular) >= limit:
                break
        return popular[:limit]

    # ── Top recommended (merge all layers) ────────────────────────────────

    def _top_recommended(
        self,
        user_id: int,
        history_items: list[dict[str, Any]],
        trending: list[dict[str, Any]],
        personalised: list[dict[str, Any]],
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        """Merge personalised, association, and trending into one ranked list."""
        scored: dict[str, dict[str, Any]] = {}

        # Personalised gets highest base weight
        for idx, item in enumerate(personalised):
            key = _normalise(item["name"])
            score = item.get("score", 0.5) + 0.3 - (idx * 0.02)
            if key not in scored or score > scored[key].get("_merge_score", 0):
                item["_merge_score"] = score
                scored[key] = item

        # Association rules from purchase history
        ordered_names = [h["name"] for h in history_items]
        for item in self._apply_rules(ordered_names):
            key = _normalise(item["name"])
            score = item.get("score", 0.7) + 0.2
            if key not in scored or score > scored[key].get("_merge_score", 0):
                item["_merge_score"] = score
                item["reason"] = "Recommended for you"
                scored[key] = item

        # Trending gets a modest boost
        for idx, item in enumerate(trending):
            key = _normalise(item["name"])
            score = item.get("score", 0.5) + 0.1 - (idx * 0.01)
            if key not in scored or score > scored[key].get("_merge_score", 0):
                item["_merge_score"] = score
                item["reason"] = "Trending + recommended"
                scored[key] = item

        # Sort by merged score, strip internal key
        ranked = sorted(scored.values(), key=lambda d: d.get("_merge_score", 0), reverse=True)
        for r in ranked:
            r.pop("_merge_score", None)
            r["score"] = round(r.get("score", 0.5), 2)

        return ranked[:limit]

    # ── helpers ───────────────────────────────────────────────────────────

    def _user_order_history(self, user_id: int, days: int = 90) -> list[dict[str, Any]]:
        """Flat list of {menu_item_id, name, quantity, ordered_at} for user."""
        since = datetime.utcnow() - timedelta(days=days)
        rows = (
            self._db.query(
                OrderItem.menu_item_id,
                MenuItem.name,
                OrderItem.quantity,
                Order.created_at,
            )
            .join(Order, Order.id == OrderItem.order_id)
            .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
            .filter(
                Order.user_id == user_id,
                Order.created_at >= since,
                Order.status.notin_([OrderStatus.CANCELLED]),
            )
            .order_by(desc(Order.created_at))
            .all()
        )
        return [
            {
                "menu_item_id": r[0],
                "name": r[1],
                "quantity": r[2],
                "ordered_at": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ]

    def _item_to_dict(self, mi: MenuItem, reason: str = "") -> dict[str, Any]:
        """Serialise a MenuItem row into a recommendation dict."""
        pairs = ASSOCIATION_RULES.get(_normalise(mi.name), [])
        return {
            "id": mi.id,
            "name": mi.name,
            "description": mi.description or f"Delicious {mi.name}",
            "price": mi.price,
            "image_url": mi.image_url or menu_image_for(mi.name),
            "vendor_id": mi.vendor_id,
            "is_available": mi.is_available,
            "reason": reason,
            "score": 0.5,
            "pairs_with": pairs if pairs else None,
        }
