"""
Seed Realistic Recommendation Data
==================================

Populates user_behaviour and user_preference_snapshots with realistic data
based on existing orders, users, and menu items.

Usage:
    python -m scripts.seed_recommendations

This script:
    1. Analyses existing orders to generate behaviour events
    2. Computes preference snapshots for each user
    3. Provides a realistic dataset for testing the recommendation engine

Run this after the initial seed data has been loaded.
"""

from __future__ import annotations

import logging
import random
import sys
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add parent to path
sys.path.insert(0, ".")

from app.core.time_utils import utcnow_naive
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.menu.model import MenuItem
from app.modules.users.model import User
from app.modules.recommendations.models import UserBehaviour, UserPreferenceSnapshot
from app.modules.recommendations.behaviour_service import BehaviourService

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed_recs")


EVENT_TYPES = ["page_view", "item_click", "search", "order_placed", "category_view", "favourite"]
SOURCE_SCREENS = ["home", "menu", "search", "recommendations", "vendor_detail", "checkout"]
SEARCH_QUERIES = [
    "biryani", "pizza", "burger", "coffee", "chai", "pasta",
    "dosa", "idli", "samosa", "cold coffee", "fries", "thali",
    "paneer", "noodles", "manchurian", "print", "xerox", "stationery",
    "photocopy", "binding", "spiral binding", "color print", "laminated",
]
CATEGORIES = [
    "food", "stationery", "indian", "chinese", "italian", "snacks", 
    "beverages", "south indian", "print", "xerox", "binding", "lamination"
]
STATIONERY_KEYWORDS = ["print", "xerox", "photocopy", "binding", "spiral", "lamination", "color print"]


def seed_behaviour(db: Session) -> dict[str, int]:
    """Generate realistic behaviour events based on actual orders."""
    logger.info("Seeding user behaviour events...")

    existing = db.query(func.count(UserBehaviour.id)).scalar() or 0
    if existing > 1000:
        logger.info("user_behaviour already has %d rows — skipping", existing)
        return {"existing": existing, "created": 0}

    # Get all users with orders
    active_user_ids = [
        r[0] for r in db.query(Order.user_id).distinct().all()
    ]
    if not active_user_ids:
        logger.warning("No users with orders found")
        return {"existing": 0, "created": 0}

    # Get all menu items
    all_menu_items = db.query(MenuItem).all()
    menu_map = {mi.id: mi for mi in all_menu_items}
    vendor_ids_from_menu = list({mi.vendor_id for mi in all_menu_items})

    # Get user orders for realistic event generation
    user_orders: dict[int, list[Order]] = {}
    for uid in active_user_ids:
        user_orders[uid] = (
            db.query(Order)
            .filter(Order.user_id == uid)
            .order_by(Order.created_at.desc())
            .limit(20)
            .all()
        )

    created = 0
    now = utcnow_naive()

    for user_id in active_user_ids:
        orders = user_orders.get(user_id, [])

        # If user has orders, generate events based on them
        for order in orders:
            # Category view events leading to order
            for _ in range(random.randint(1, 3)):
                cat = random.choice(CATEGORIES)
                event = UserBehaviour(
                    user_id=user_id,
                    event_type="category_view",
                    category=cat,
                    source_screen="home",
                    weight=0.5,
                    created_at=order.created_at - timedelta(minutes=random.randint(5, 60)),
                )
                db.add(event)
                created += 1

            # Vendor page view
            event = UserBehaviour(
                user_id=user_id,
                event_type="page_view",
                vendor_id=order.vendor_id,
                source_screen=random.choice(["home", "recommendations", "search"]),
                weight=0.8,
                created_at=order.created_at - timedelta(minutes=random.randint(2, 30)),
            )
            db.add(event)
            created += 1

            # Menu item clicks (the actual items ordered)
            order_items = (
                db.query(OrderItem)
                .filter(OrderItem.order_id == order.id)
                .all()
            )
            for oi in order_items:
                event = UserBehaviour(
                    user_id=user_id,
                    event_type="item_click",
                    menu_item_id=oi.menu_item_id,
                    vendor_id=order.vendor_id,
                    source_screen="menu",
                    weight=0.6,
                    created_at=order.created_at - timedelta(minutes=random.randint(1, 15)),
                )
                db.add(event)
                created += 1

            # Order placed event
            event = UserBehaviour(
                user_id=user_id,
                event_type="order_placed",
                order_id=order.id,
                vendor_id=order.vendor_id,
                source_screen="checkout",
                weight=1.5,
                created_at=order.created_at,
            )
            db.add(event)
            created += 1

        # Additional random browse events
        browse_count = random.randint(3, 8)
        for _ in range(browse_count):
            event_time = now - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            event_type = random.choice(EVENT_TYPES)
            vendor_id = random.choice(vendor_ids_from_menu) if vendor_ids_from_menu else None
            mi = random.choice(all_menu_items) if all_menu_items else None

            # Match event type with proper payload
            kwargs: dict[str, Any] = {
                "user_id": user_id,
                "event_type": event_type,
                "source_screen": random.choice(SOURCE_SCREENS),
                "weight": random.uniform(0.3, 2.0),
                "created_at": event_time,
            }

            if event_type == "page_view" and vendor_id:
                kwargs["vendor_id"] = vendor_id
                # Add stationery-specific page views
                if random.random() < 0.2 and vendor_ids_from_menu:
                    kwargs["vendor_id"] = random.choice(vendor_ids_from_menu)
            elif event_type == "item_click" and mi:
                kwargs["menu_item_id"] = mi.id
                kwargs["vendor_id"] = mi.vendor_id
            elif event_type == "search":
                # Bias towards food in morning/evening, stationery in afternoon
                hour = event_time.hour
                if 10 <= hour <= 16:
                    # Afternoon: more stationery searches
                    query = random.choice(SEARCH_QUERIES)
                    if random.random() < 0.4:
                        query = random.choice(["print", "xerox", "stationery", "binding"])
                else:
                    # Morning/Evening: more food searches
                    query = random.choice(SEARCH_QUERIES[:14])  # Food items
                kwargs["search_query"] = query
                kwargs["search_results_count"] = random.randint(3, 20)
            elif event_type == "category_view":
                # Time-aware category views
                hour = event_time.hour
                if 10 <= hour <= 16:
                    cat = random.choice(["stationery", "print", "xerox", "food"])
                else:
                    cat = random.choice(CATEGORIES)
                kwargs["category"] = cat
            elif event_type == "favourite" and vendor_id:
                kwargs["vendor_id"] = vendor_id
                kwargs["weight"] = random.uniform(1.5, 2.5)
            elif event_type == "page_view":
                kwargs["category"] = random.choice(CATEGORIES)

            event = UserBehaviour(**kwargs)
            db.add(event)
            created += 1

        # Flush periodically
        if created % 50 == 0:
            db.flush()

    db.commit()
    logger.info("Created %d user behaviour events", created)
    
    # Log stationery-specific events
    stationery_events = db.query(func.count(UserBehaviour.id)).filter(
        UserBehaviour.search_query.in_(["print", "xerox", "stationery", "binding"])
    ).scalar() or 0
    logger.info("  Stationery-related events: %d", stationery_events)
    
    return {"existing": existing, "created": created}


def seed_preference_snapshots(db: Session) -> int:
    """Compute and store preference snapshots for all users."""
    logger.info("Computing preference snapshots...")

    existing = db.query(func.count(UserPreferenceSnapshot.id)).scalar() or 0
    if existing > 0:
        logger.info("user_preference_snapshots already has %d rows — skipping", existing)
        return existing

    active_user_ids = [
        r[0] for r in db.query(Order.user_id).distinct().all()
    ]

    if not active_user_ids:
        logger.warning("No users with orders found")
        return 0

    service = BehaviourService(db)
    for uid in active_user_ids:
        try:
            service.compute_preference_snapshot(uid)
            logger.info("Computed snapshot for user %d", uid)
        except Exception as e:
            logger.error("Failed to compute snapshot for user %d: %s", uid, e)

    total = db.query(func.count(UserPreferenceSnapshot.id)).scalar() or 0
    logger.info("Total preference snapshots: %d", total)
    return total


def main():
    """Main seed function."""
    # Try to get DB from environment
    import os
    from dotenv import load_dotenv
    load_dotenv()

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/tapntake",
    )
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("Seeding recommendation engine data")
        logger.info("=" * 60)

        # Step 1: Generate behaviour events
        behav_result = seed_behaviour(db)

        # Step 2: Compute preference snapshots
        snap_count = seed_preference_snapshots(db)

        logger.info("=" * 60)
        logger.info("Seed complete!")
        logger.info("  Behaviour events: %d", behav_result.get("created", 0))
        logger.info("  Preference snapshots: %d", snap_count)
        logger.info("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
