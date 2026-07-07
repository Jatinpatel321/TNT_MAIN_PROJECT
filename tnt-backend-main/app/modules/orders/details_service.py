from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem
from sqlalchemy.orm import Session

from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order


def get_vendor_order_details(order_id: int, vendor_id: int, db: Session):
    order = (
        db.query(Order)
        .filter(Order.id == order_id, Order.vendor_id == vendor_id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = (
        db.query(OrderItem, MenuItem)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .filter(OrderItem.order_id == order.id)
        .all()
    )

    item_list = []
    total = 0

    for order_item, menu_item in items:
        line_total = order_item.price_at_time * order_item.quantity
        total += line_total

        item_list.append({
            "name": menu_item.name,
            "image_url": menu_item.image_url,
            "quantity": order_item.quantity,
            "price_at_time": order_item.price_at_time,
            "line_total": line_total
        })

    return {
        "order_id": order.id,
        "status": order.status,
        "created_at": order.created_at,
        "items": item_list,
        "total_amount": total
    }
