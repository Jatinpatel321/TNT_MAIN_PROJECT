"""Lightweight order lifecycle simulator.

This background task advances non-terminal orders through the canonical
states on a fixed cadence and emits user notifications so flows work even
without manual vendor actions.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.database.session import SessionLocal
from app.modules.notifications.model import NotificationType
from app.modules.notifications.service import notify_user
from app.modules.orders.history_model import OrderHistory
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.service import update_order_status
from app.modules.users.model import User

logger = logging.getLogger("tnt.order_simulator")


TERMINAL_STATES = {
    OrderStatus.PICKED,
    OrderStatus.COMPLETED,
    OrderStatus.CANCELLED,
}


class OrderLifecycleSimulator:
    """Advance orders through PLACED → CONFIRMED → READY → PICKED.

    The simulator is intentionally conservative:
    - Only touches non-terminal orders.
    - Only transitions when the last state change is at least
      ``interval_seconds`` ago.
    - Uses the existing state machine and history tracking.
    - Sends best-effort in-app notifications (SMS disabled by default to
      avoid local dev failures).
    """

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = interval_seconds
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task is None:
            self._stop_event.clear()
            self._task = asyncio.create_task(
                self._run(), name="order-lifecycle-simulator"
            )

    async def stop(self) -> None:
        if self._task:
            self._stop_event.set()
            self._task.cancel()
            with suppress(Exception):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self.tick()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def tick(self) -> None:
        if self._lock.locked():
            return

        async with self._lock:
            db: Session = SessionLocal()
            try:
                now = utcnow_naive()
                open_orders = (
                    db.query(Order)
                    .filter(~Order.status.in_(TERMINAL_STATES))
                    .all()
                )

                for order in open_orders:
                    last_changed = self._last_changed_at(order, db) or order.created_at or now
                    if (now - last_changed) < timedelta(seconds=self.interval_seconds):
                        continue

                    next_status, notification = self._next_status(order.status)
                    if not next_status:
                        continue

                    try:
                        update_order_status(order, next_status, "system", db)
                        if notification:
                            self._notify_student(order, notification, db)
                        db.commit()
                        db.refresh(order)
                    except Exception:
                        db.rollback()
                        logger.exception("order_lifecycle_tick_failed order_id=%s", order.id)
            finally:
                db.close()

    def _last_changed_at(self, order: Order, db: Session):
        history = (
            db.query(OrderHistory)
            .filter(OrderHistory.order_id == order.id)
            .order_by(OrderHistory.changed_at.desc())
            .first()
        )
        return history.changed_at if history and history.changed_at else None

    def _next_status(self, status: OrderStatus):
        # PLACED/PENDING → CONFIRMED (accepted)
        if status in {OrderStatus.PLACED, OrderStatus.PENDING}:
            return OrderStatus.CONFIRMED, {
                "title": "Order Accepted",
                "message": "Your order #{order_id} has been accepted",
                "type": NotificationType.ORDER_ACCEPTED,
            }

        # CONFIRMED → PREPARING (vendor started preparing)
        if status == OrderStatus.CONFIRMED:
            return OrderStatus.PREPARING, {
                "title": "Order Preparing",
                "message": "Your order #{order_id} is being prepared",
                "type": NotificationType.ORDER_PREPARING,
            }

        # PREPARING → READY (ready for pickup)
        if status == OrderStatus.PREPARING:
            return OrderStatus.READY, {
                "title": "Order Ready",
                "message": "Your order #{order_id} is ready for pickup",
                "type": NotificationType.ORDER_READY,
            }

        # READY/READY_FOR_PICKUP → PICKED (completed)
        if status in {OrderStatus.READY, OrderStatus.READY_FOR_PICKUP}:
            return OrderStatus.PICKED, None

        return None, None

    def _notify_student(self, order: Order, notification: dict, db: Session) -> None:
        user = db.query(User).filter(User.id == order.user_id).first()
        if not user:
            return

        notify_user(
            user_id=user.id,
            phone=user.phone,
            title=notification["title"],
            message=notification["message"].format(order_id=order.id),
            db=db,
            send_sms_flag=False,
            notification_type=notification.get("type", NotificationType.SYSTEM),
            reference_id=order.id,
        )


# Singleton instance used by application lifespan.
order_lifecycle_simulator = OrderLifecycleSimulator()
