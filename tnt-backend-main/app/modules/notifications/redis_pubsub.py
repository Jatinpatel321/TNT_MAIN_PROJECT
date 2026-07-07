"""Redis Pub/Sub Service - Distributed notification broadcasting."""

from __future__ import annotations

import json
import logging
from typing import Callable, Dict, Optional
import asyncio

logger = logging.getLogger("tnt.notifications.redis")


class RedisPubSubService:
    """Redis Pub/Sub service for distributed notifications."""

    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.subscriptions: Dict[str, Callable] = {}
        self.running = False

    def initialize(self):
        """Initialize Redis connection."""
        try:
            from app.core.redis import redis_client
            self.redis_client = redis_client
            self.pubsub = self.redis_client.pubsub()
            logger.info("redis_pubsub_initialized")
        except Exception as e:
            logger.error("redis_pubsub_init_failed error=%s", e)
            raise

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a Redis channel."""
        if not self.pubsub:
            self.initialize()

        self.pubsub.subscribe(channel)
        self.subscriptions[channel] = callback
        logger.info("redis_subscribed channel=%s", channel)

    def unsubscribe(self, channel: str):
        """Unsubscribe from a Redis channel."""
        if self.pubsub and channel in self.subscriptions:
            self.pubsub.unsubscribe(channel)
            del self.subscriptions[channel]
            logger.info("redis_unsubscribed channel=%s", channel)

    async def publish(self, channel: str, message: dict):
        """Publish message to Redis channel."""
        if not self.redis_client:
            logger.warning("redis_not_initialized")
            return

        try:
            payload = json.dumps(message)
            self.redis_client.publish(channel, payload)
            logger.info("redis_published channel=%s", channel)
        except Exception as e:
            logger.error("redis_publish_failed channel=%s error=%s", channel, e)

    async def listen(self):
        """Listen for messages from subscribed channels."""
        if not self.pubsub:
            self.initialize()

        self.running = True
        logger.info("redis_listener_started")

        while self.running:
            try:
                message = self.pubsub.get_message(ignore_binary=True, timeout=1.0)
                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    if channel in self.subscriptions:
                        callback = self.subscriptions[channel]
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)

            except Exception as e:
                logger.error("redis_listen_error error=%s", e)
                await asyncio.sleep(1)

    def stop(self):
        """Stop listening for messages."""
        self.running = False
        if self.pubsub:
            self.pubsub.close()
        logger.info("redis_listener_stopped")


# Global instance
redis_pubsub = RedisPubSubService()


# Channel definitions
class NotificationChannels:
    """Redis channel names for different notification types."""
    
    NEW_ORDER = "notifications:new_order"
    ORDER_ACCEPTED = "notifications:order_accepted"
    ORDER_READY = "notifications:order_ready"
    ORDER_COMPLETED = "notifications:order_completed"
    PROMOTION_CREATED = "notifications:promotion_created"
    SETTLEMENT_UPDATED = "notifications:settlement_updated"
    VENDOR_BROADCAST = "notifications:vendor_broadcast"


async def publish_notification(channel: str, data: dict):
    """Publish notification to Redis channel."""
    await redis_pubsub.publish(channel, data)


async def broadcast_to_vendors(vendor_ids: list[int], notification_data: dict):
    """Broadcast notification to multiple vendors via Redis."""
    await publish_notification(
        NotificationChannels.VENDOR_BROADCAST,
        {
            "vendor_ids": vendor_ids,
            "notification": notification_data,
        }
    )