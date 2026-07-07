"""Vendor Inventory Automation Service.

Handles:
- Auto stock deduction on order completion
- Low-stock detection
- Out-of-stock detection
- Auto disable unavailable products
- Auto re-enable workflow
- Inventory alert notifications
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.time_utils import utcnow_naive
from app.modules.menu.model import MenuItem, Inventory
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.notifications.model import NotificationType
from app.modules.notifications.service import notify_user
from app.modules.users.model import User


class VendorInventoryService:
    """Inventory automation and stock management for vendors."""

    def __init__(self, db: Session):
        self.db = db

    # ── Auto Stock Deduction ──────────────────────────────────────────────────

    def auto_deduct_stock(self, order_id: int) -> Dict[str, Any]:
        """Automatically deduct stock when an order is completed or prepared.
        
        Called when order status transitions to PREPARING or PICKED.
        Deducts `quantity` from `available_quantity` on MenuItem,
        and from `current_stock` on the associated Inventory record.
        """
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return {"success": False, "error": "Order not found"}

        order_items = self.db.query(OrderItem).filter(
            OrderItem.order_id == order_id
        ).all()

        deductions = []
        for oi in order_items:
            menu_item = self.db.query(MenuItem).filter(
                MenuItem.id == oi.menu_item_id
            ).first()
            if not menu_item:
                continue

            # Deduct from MenuItem.available_quantity
            if menu_item.available_quantity is not None and menu_item.available_quantity > 0:
                menu_item.available_quantity = max(0, menu_item.available_quantity - oi.quantity)

            # Deduct from Inventory.current_stock
            inventory = self.db.query(Inventory).filter(
                Inventory.menu_item_id == oi.menu_item_id
            ).first()
            if inventory and inventory.current_stock > 0:
                inventory.current_stock = max(0, inventory.current_stock - oi.quantity)
                inventory.updated_at = utcnow_naive()

            deductions.append({
                "item_id": oi.menu_item_id,
                "quantity_deducted": oi.quantity,
                "remaining_stock": menu_item.available_quantity if menu_item else 0,
                "remaining_inventory": inventory.current_stock if inventory else 0,
            })

        self.db.flush()

        # Check for low-stock / out-of-stock after deduction
        alerts = []
        for d in deductions:
            menu_item = self.db.query(MenuItem).filter(
                MenuItem.id == d["item_id"]
            ).first()
            inventory = self.db.query(Inventory).filter(
                Inventory.menu_item_id == d["item_id"]
            ).first()
            
            # Low stock check
            if inventory and inventory.current_stock <= inventory.low_stock_threshold:
                alert = self._check_low_stock(menu_item, inventory)
                if alert:
                    alerts.append(alert)

            # Out of stock check → auto disable
            available = menu_item.available_quantity if menu_item else 0
            inv_stock = inventory.current_stock if inventory else 0
            if available <= 0 or inv_stock <= 0:
                self._auto_disable_item(menu_item, inventory)
                alerts.append({
                    "type": "out_of_stock",
                    "item_id": d["item_id"],
                    "item_name": menu_item.name if menu_item else "Unknown",
                    "action_taken": "Item auto-disabled",
                })

        self.db.commit()

        return {
            "success": True,
            "order_id": order_id,
            "deductions": deductions,
            "alerts": alerts,
        }

    def deduct_stock_on_prepare(self, order_id: int) -> Dict[str, Any]:
        """Deduct stock when vendor starts preparing the order (CONFIRMED -> PREPARING)."""
        return self.auto_deduct_stock(order_id)

    # ── Low-Stock Detection ───────────────────────────────────────────────────

    def detect_low_stock_items(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Find all items with stock below their low-stock threshold."""
        low_stock = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.available_quantity,
            Inventory.current_stock,
            Inventory.low_stock_threshold,
        ).outerjoin(
            Inventory, Inventory.menu_item_id == MenuItem.id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_available == True,
        ).all()

        alerts = []
        for item in low_stock:
            available = item.available_quantity or 0
            inv_stock = item.current_stock if item.current_stock is not None else available
            threshold = item.low_stock_threshold if item.low_stock_threshold is not None else 10

            if 0 < inv_stock <= threshold:
                alerts.append({
                    "item_id": item.id,
                    "item_name": item.name,
                    "current_stock": inv_stock,
                    "threshold": threshold,
                    "severity": "low_stock",
                    "message": f"'{item.name}' is running low ({inv_stock} remaining, threshold: {threshold})",
                })

        return alerts

    def _check_low_stock(self, menu_item: MenuItem, inventory: Inventory) -> Optional[Dict[str, Any]]:
        """Check if item is low on stock and return alert."""
        if not menu_item or not inventory:
            return None
        if inventory.current_stock <= inventory.low_stock_threshold < 999:
            return {
                "type": "low_stock",
                "item_id": menu_item.id,
                "item_name": menu_item.name,
                "current_stock": inventory.current_stock,
                "threshold": inventory.low_stock_threshold,
                "action_needed": "Restock soon",
            }
        return None

    # ── Out-of-Stock Detection & Auto-Disable ─────────────────────────────────

    def detect_out_of_stock_items(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Find all items that are out of stock and auto-disable them."""
        out_of_stock = self.db.query(
            MenuItem, Inventory
        ).outerjoin(
            Inventory, Inventory.menu_item_id == MenuItem.id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_available == True,
        ).all()

        alerts = []
        for menu_item, inventory in out_of_stock:
            available = menu_item.available_quantity or 0
            inv_stock = inventory.current_stock if inventory else available

            if inv_stock <= 0:
                self._auto_disable_item(menu_item, inventory)
                alerts.append({
                    "item_id": menu_item.id,
                    "item_name": menu_item.name,
                    "severity": "out_of_stock",
                    "action_taken": "Auto-disabled",
                    "message": f"'{menu_item.name}' is out of stock and has been disabled",
                })

        return alerts

    def _auto_disable_item(self, menu_item: MenuItem, inventory: Inventory = None) -> None:
        """Automatically disable a menu item when out of stock."""
        if not menu_item:
            return
        # Only auto-disable if the feature is enabled (default: True)
        if inventory and inventory.auto_disable is False:
            return
        menu_item.is_available = False

    # ── Auto Re-enable Workflow ─────────────────────────────────────────────

    def auto_enable_items(self, vendor_id: int) -> List[Dict[str, Any]]:
        """Re-enable items that have been restocked above threshold."""
        restocked = self.db.query(
            MenuItem, Inventory
        ).outerjoin(
            Inventory, Inventory.menu_item_id == MenuItem.id
        ).filter(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_available == False,
        ).all()

        reenabled = []
        for menu_item, inventory in restocked:
            available = menu_item.available_quantity or 0
            inv_stock = inventory.current_stock if inventory else available
            threshold = inventory.low_stock_threshold if inventory else 10

            if inv_stock > threshold:
                menu_item.is_available = True
                if inventory:
                    inventory.updated_at = utcnow_naive()
                reenabled.append({
                    "item_id": menu_item.id,
                    "item_name": menu_item.name,
                    "current_stock": inv_stock,
                    "threshold": threshold,
                    "message": f"'{menu_item.name}' has been re-enabled (stock: {inv_stock})",
                })

        if reenabled:
            self.db.flush()

        return reenabled

    # ── Inventory Alert Notifications ────────────────────────────────────────

    def send_inventory_alerts(self, vendor_id: int) -> Dict[str, Any]:
        """Send inventory alert notifications to vendor."""
        low_stock = self.detect_low_stock_items(vendor_id)
        out_of_stock = self.detect_out_of_stock_items(vendor_id)

        # Find vendor owner for notification
        vendor_user = self.db.query(User).filter(User.id == vendor_id).first()
        if not vendor_user:
            return {"success": False, "error": "Vendor not found"}

        notifications_sent = 0
        alerts = low_stock + out_of_stock

        for alert in alerts:
            try:
                notify_user(
                    user_id=vendor_id,
                    phone=vendor_user.phone,
                    title="Inventory Alert",
                    message=alert["message"],
                    db=self.db,
                    send_sms_flag=False,
                    notification_type=NotificationType.ALERT,
                    reference_id=alert["item_id"],
                )
                notifications_sent += 1
            except Exception:
                pass

        return {
            "success": True,
            "notifications_sent": notifications_sent,
            "low_stock_alerts": len(low_stock),
            "out_of_stock_alerts": len(out_of_stock),
            "alerts": alerts,
        }

    # ── Full Inventory Dashboard ─────────────────────────────────────────────

    def get_inventory_dashboard(self, vendor_id: int) -> Dict[str, Any]:
        """Get complete inventory status dashboard."""
        items = self.db.query(
            MenuItem.id,
            MenuItem.name,
            MenuItem.price,
            MenuItem.is_available,
            MenuItem.available_quantity,
            Inventory.current_stock,
            Inventory.low_stock_threshold,
            Inventory.last_restocked_at,
            Inventory.auto_disable,
        ).outerjoin(
            Inventory, Inventory.menu_item_id == MenuItem.id
        ).filter(
            MenuItem.vendor_id == vendor_id,
        ).order_by(MenuItem.name).all()

        item_list = []
        low_stock_count = 0
        out_of_stock_count = 0
        in_stock_count = 0
        disabled_count = 0

        for item in items:
            available = item.available_quantity or 0
            inv_stock = item.current_stock if item.current_stock is not None else available
            threshold = item.low_stock_threshold if item.low_stock_threshold is not None else 10
            is_available = item.is_available

            status = "in_stock"
            if not is_available and inv_stock > 0:
                status = "manually_disabled"
                disabled_count += 1
            elif not is_available and inv_stock <= 0:
                status = "out_of_stock"
                out_of_stock_count += 1
            elif inv_stock <= 0:
                status = "out_of_stock"
                out_of_stock_count += 1
            elif inv_stock <= threshold:
                status = "low_stock"
                low_stock_count += 1
            else:
                in_stock_count += 1

            item_list.append({
                "item_id": item.id,
                "name": item.name,
                "price": float(item.price) if item.price else 0,
                "is_available": is_available,
                "available_quantity": available,
                "current_stock": inv_stock,
                "low_stock_threshold": threshold,
                "last_restocked_at": item.last_restocked_at.isoformat() if item.last_restocked_at else None,
                "auto_disable": item.auto_disable if item.auto_disable is not None else True,
                "status": status,
            })

        return {
            "vendor_id": vendor_id,
            "total_items": len(item_list),
            "in_stock": in_stock_count,
            "low_stock": low_stock_count,
            "out_of_stock": out_of_stock_count,
            "manually_disabled": disabled_count,
            "items": item_list,
            "stock_summary": {
                "total_stock_available": sum(
                    i["current_stock"] for i in item_list if i["status"] == "in_stock"
                ),
                "items_needing_attention": low_stock_count + out_of_stock_count,
            },
        }

    # ── Restock Item ─────────────────────────────────────────────────────────

    def restock_item(self, vendor_id: int, item_id: int, quantity: int) -> Dict[str, Any]:
        """Restock a menu item by adding quantity."""
        menu_item = self.db.query(MenuItem).filter(
            MenuItem.id == item_id,
            MenuItem.vendor_id == vendor_id,
        ).first()
        if not menu_item:
            return {"success": False, "error": "Item not found"}

        inventory = self.db.query(Inventory).filter(
            Inventory.menu_item_id == item_id
        ).first()

        if inventory:
            inventory.current_stock += quantity
            inventory.last_restocked_at = utcnow_naive()
            inventory.updated_at = utcnow_naive()
        else:
            inventory = Inventory(
                menu_item_id=item_id,
                current_stock=quantity,
                low_stock_threshold=10,
                last_restocked_at=utcnow_naive(),
            )
            self.db.add(inventory)

        if menu_item.available_quantity is not None:
            menu_item.available_quantity += quantity

        self.db.flush()

        # Auto re-enable if was disabled and now restocked
        reenabled = self.auto_enable_items(vendor_id)

        self.db.commit()

        return {
            "success": True,
            "item_id": item_id,
            "item_name": menu_item.name,
            "quantity_added": quantity,
            "new_stock": inventory.current_stock,
            "item_reenabled": any(r["item_id"] == item_id for r in reenabled),
        }