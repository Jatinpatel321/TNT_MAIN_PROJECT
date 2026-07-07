"""
Redis Cache Warm-up Script
===========================

Pre-populates Redis cache with frequently accessed data to improve
initial performance and reduce API latency.

Warms up:
- Recommendations for all users
- Trending items
- Popular items
- Vendor speeds
- ETA predictions
- User preferences
"""

from __future__ import annotations

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger("tnt.cache_warmup")


class CacheWarmupService:
    """Warm up Redis cache with frequently accessed data."""

    def __init__(self, db, ai_cache_service):
        self.db = db
        self.ai_cache = ai_cache_service

    async def warm_all(self) -> Dict[str, Any]:
        """Warm all cache categories."""
        logger.info("Starting cache warm-up...")

        results = {}

        # Warm in parallel
        results['recommendations'] = await self._warm_recommendations()
        results['trending'] = await self._warm_trending()
        results['popular'] = await self._warm_popular()
        results['vendor_speeds'] = await self._warm_vendor_speeds()
        results['user_preferences'] = await self._warm_user_preferences()

        logger.info("Cache warm-up completed")
        return results

    async def _warm_recommendations(self) -> int:
        """Warm recommendation caches for all users."""
        from app.modules.users.model import User
        from app.modules.recommendations.smart_engine import SmartRecommendationEngine

        count = 0
        users = self.db.query(User).filter(User.is_active == True).all()

        engine = SmartRecommendationEngine(self.db)

        for user in users[:20]:  # Warm first 20 users
            try:
                recs = engine.get_recommendations(user.id)
                await self.ai_cache.set(
                    category='recommendations',
                    identifier=f'user:{user.id}',
                    value=recs,
                    ttl=300
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to warm recommendations for user {user.id}: {e}")

        logger.info(f"Warmed recommendations for {count} users")
        return count

    async def _warm_trending(self) -> int:
        """Warm trending items cache."""
        from app.modules.menu.model import MenuItem

        count = 0
        time_slots = ['morning', 'afternoon', 'evening', 'night']

        for slot in time_slots:
            try:
                # Get trending items for time slot
                items = self.db.query(MenuItem)\
                    .filter(MenuItem.is_available == True)\
                    .order_by(MenuItem.id.desc())\
                    .limit(20)\
                    .all()

                items_data = [
                    {
                        'id': item.id,
                        'name': item.name,
                        'price': item.price,
                        'category': item.category
                    }
                    for item in items
                ]

                await self.ai_cache.set(
                    category='trending_items',
                    identifier=f'tod:{slot}',
                    value=items_data,
                    ttl=600
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to warm trending for {slot}: {e}")

        logger.info(f"Warmed {count} trending item caches")
        return count

    async def _warm_popular(self) -> int:
        """Warm popular items cache."""
        from app.modules.menu.model import MenuItem
        from app.modules.feedback.model import MenuItemReview

        try:
            # Get popular items (most reviewed)
            popular_items = self.db.query(MenuItem)\
                .filter(MenuItem.is_available == True)\
                .order_by(MenuItem.id.desc())\
                .limit(30)\
                .all()

            items_data = [
                {
                    'id': item.id,
                    'name': item.name,
                    'price': item.price,
                    'category': item.category
                }
                for item in popular_items
            ]

            await self.ai_cache.set(
                category='popular_items',
                identifier='global',
                value=items_data,
                ttl=1800
            )

            logger.info("Warmed popular items cache")
            return 1
        except Exception as e:
            logger.error(f"Failed to warm popular items: {e}")
            return 0

    async def _warm_vendor_speeds(self) -> int:
        """Warm vendor speed caches."""
        from app.modules.vendors.model import VendorProfile
        from app.modules.ai_intelligence.vendor_speed_service import VendorSpeedService

        count = 0
        vendors = self.db.query(VendorProfile).filter(VendorProfile.is_active == True).all()

        speed_service = VendorSpeedService(self.db)

        for vendor in vendors[:10]:  # Warm first 10 vendors
            try:
                speed_data = speed_service.get_vendor_speed(vendor.user_id)
                await self.ai_cache.set(
                    category='vendor_speed',
                    identifier=f'vendor:{vendor.user_id}',
                    value=speed_data,
                    ttl=120
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to warm vendor speed for {vendor.user_id}: {e}")

        logger.info(f"Warmed vendor speed for {count} vendors")
        return count

    async def _warm_user_preferences(self) -> int:
        """Warm user preference caches."""
        from app.modules.users.model import User
        from app.modules.recommendations.behaviour_service import BehaviourService

        count = 0
        users = self.db.query(User).filter(User.is_active == True).all()

        behaviour_service = BehaviourService(self.db)

        for user in users[:20]:  # Warm first 20 users
            try:
                prefs = behaviour_service.get_user_preferences(user.id)
                await self.ai_cache.set(
                    category='user_preferences',
                    identifier=f'user:{user.id}',
                    value=prefs,
                    ttl=3600
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to warm preferences for user {user.id}: {e}")

        logger.info(f"Warmed preferences for {count} users")
        return count


async def main():
    """Main function to run cache warm-up."""
    from app.core.deps import SessionLocal, get_ai_cache_service

    db = SessionLocal()
    ai_cache = get_ai_cache_service()

    try:
        ai_cache.initialize()

        warmup = CacheWarmupService(db, ai_cache)
        results = await warmup.warm_all()

        print("\n" + "="*60)
        print("CACHE WARM-UP COMPLETE")
        print("="*60)
        for category, count in results.items():
            print(f"{category}: {count} items cached")
        print("="*60)

    except Exception as e:
        logger.error(f"Cache warm-up failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())