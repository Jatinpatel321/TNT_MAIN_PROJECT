import logging
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger("tnt.orders.checkout")

from app.core.db_transaction import transactional
from app.core.faculty_policy import is_slot_in_faculty_priority_window
from app.core.time_utils import utcnow_naive
from app.core.university_policy import get_university_policy, is_hour_in_break_window
from app.modules.orders.item_schemas import OrderItemCreate
from app.modules.orders.item_service import add_items_to_order
from app.modules.orders.model import Order, OrderStatus
from app.modules.orders.service import create_order
from app.modules.slots.model import Slot
from app.modules.slots.service import reserve_slot_for_order
from app.modules.users.model import User


def _aggregate_item_quantities(items: list[OrderItemCreate]) -> dict[int, int]:
    quantities: dict[int, int] = {}
    for item in items:
        if item.quantity <= 0:
            raise HTTPException(status_code=400, detail="Item quantity must be positive")
        quantities[item.menu_item_id] = quantities.get(item.menu_item_id, 0) + item.quantity
    return quantities


def _validate_order_items_for_vendor(
    vendor_id: int,
    requested_quantities: dict[int, int],
    db: Session,
) -> None:
    from app.modules.menu.model import Inventory, MenuItem

    for menu_item_id, quantity in requested_quantities.items():
        menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=400, detail=f"Menu item {menu_item_id} not found")
        if menu_item.vendor_id != vendor_id:
            raise HTTPException(status_code=400, detail="Cannot order items from a different vendor")
        if not menu_item.is_available:
            raise HTTPException(status_code=400, detail=f"Menu item {menu_item_id} not available")
        if menu_item.available_quantity is not None and menu_item.available_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {menu_item.name}")

        inventory = db.query(Inventory).filter(Inventory.menu_item_id == menu_item_id).first()
        if inventory and inventory.current_stock < quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient inventory for {menu_item.name}")


def _deduct_inventory_for_order(item_quantities: dict[int, int], db: Session) -> None:
    from app.modules.menu.model import Inventory, MenuItem

    for menu_item_id, quantity in item_quantities.items():
        menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
        if not menu_item:
            continue

        if menu_item.available_quantity is not None:
            menu_item.available_quantity = max(0, menu_item.available_quantity - quantity)

        inventory = db.query(Inventory).filter(Inventory.menu_item_id == menu_item_id).first()
        if inventory:
            inventory.current_stock = max(0, inventory.current_stock - quantity)
            inventory.updated_at = utcnow_naive()
            if inventory.auto_disable and inventory.current_stock <= 0:
                menu_item.is_available = False
        elif menu_item.available_quantity is not None and menu_item.available_quantity <= 0:
            menu_item.is_available = False


@transactional
def checkout_order_for_user(
    db_user: User,
    slot_id: int,
    items: list[OrderItemCreate],
    db: Session,
):
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    vendor = db.query(User).filter(User.id == slot.vendor_id).first()
    if not vendor or not vendor.is_active or not vendor.is_approved:
        raise HTTPException(status_code=400, detail="Vendor is not available")

    from app.modules.vendors.business_hours_service import check_business_hours

    is_open, reason = check_business_hours(slot.vendor_id, db)
    if not is_open:
        raise HTTPException(status_code=400, detail=f"Cannot place order: {reason}")

    role = (db_user.role.value or "").lower()
    if is_slot_in_faculty_priority_window(slot.start_time.hour) and role not in {"faculty", "admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="This slot is reserved for faculty during priority window")

    policy = get_university_policy()
    if policy.get("enabled", False):
        if not is_hour_in_break_window(
            slot.start_time.hour,
            int(policy.get("break_start_hour", 12)),
            int(policy.get("break_end_hour", 14)),
        ):
            raise HTTPException(status_code=400, detail="Orders are allowed only during university break window")

        now = utcnow_naive()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        existing_orders = (
            db.query(Order)
            .filter(
                Order.user_id == db_user.id,
                Order.created_at >= day_start,
                Order.created_at < day_end,
                Order.status != OrderStatus.CANCELLED,
            )
            .count()
        )
        if existing_orders >= int(policy.get("max_orders_per_user", 3)):
            raise HTTPException(status_code=400, detail="Maximum orders per user reached for this day")

    item_quantities = _aggregate_item_quantities(items)
    if item_quantities:
        _validate_order_items_for_vendor(slot.vendor_id, item_quantities, db)

    slot = reserve_slot_for_order(slot_id, db_user.id, db)

    order = create_order(
        user_id=db_user.id,
        slot_id=slot_id,
        db=db,
    )

    total_amount = add_items_to_order(order, items, db)
    order.total_amount = total_amount

    # Decrement stock: deduct inventory & auto-disable when exhausted
    _deduct_inventory_for_order(item_quantities, db)

    # ── Automated fraud detection ──────────────────────────────────────
    from app.modules.fraud.fraud_rules import run_fraud_checks
    from app.modules.fraud.fraud_detection_service import FraudDetectionService
    from app.core.time_utils import utcnow_naive as _utcnow

    fraud_reason = run_fraud_checks(order, db)
    if fraud_reason:
        order.fraud_flag = True
        order.fraud_reason = fraud_reason
        order.flagged_at = _utcnow()
        logger.info("auto_fraud_flag order_id=%s reason=%s", order.id, fraud_reason)

    # Run complete fraud detection service to log structured database alerts
    try:
        db.flush()
        FraudDetectionService.run_all_detectors_for_order(db, order)
    except Exception as e:
        logger.error("checkout_fraud_service_error order_id=%s err=%s", order.id, str(e))
    # ───────────────────────────────────────────────────────────────────

    congestion_factor = slot.congestion_level if hasattr(slot, "congestion_level") else 0

    base_eta = 15
    eta_minutes = base_eta + int(congestion_factor / 10)
    order.eta_minutes = eta_minutes

    return order, slot, total_amount, eta_minutes
