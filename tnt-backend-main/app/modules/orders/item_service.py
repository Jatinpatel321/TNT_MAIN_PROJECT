from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.menu.model import MenuItem
from app.modules.orders.model import OrderItem


def add_items_to_order(order, items, db: Session):
    total = 0

    for item in items:
        menu_item = db.query(MenuItem).filter(
            MenuItem.id == item.menu_item_id,
            MenuItem.is_available == True
        ).first()

        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        # 🔒 Vendor safety
        if menu_item.vendor_id != order.vendor_id:
            raise HTTPException(
                status_code=400,
                detail="Item does not belong to this vendor"
            )

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            quantity=item.quantity,
            price_at_time=menu_item.price
        )

        total += menu_item.price * item.quantity
        db.add(order_item)

    return total


def get_order_items(order_id: int, db: Session):
    return db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
