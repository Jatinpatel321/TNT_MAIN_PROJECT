import json
import secrets
import string
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.redis import redis_client
from app.core.security import get_current_user
from app.modules.menu.model import MenuItem
from app.modules.notifications.model import Notification
from app.modules.orders.checkout_service import checkout_order_for_user
from app.modules.orders.item_schemas import OrderItemCreate
from app.modules.payments.service import initiate_payment
from app.modules.slots.model import Slot, SlotStatus
from app.modules.users.model import User, UserRole

router = APIRouter(prefix="/cart", tags=["Cart"])
checkout_router = APIRouter(tags=["Checkout"])


class SoloCartItemRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(default=1, gt=0)


class CartUpdateRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, description="New absolute quantity for the item")


class CartRemoveRequest(BaseModel):
    menu_item_id: int


class CheckoutRequest(BaseModel):
    slot_id: int | None = Field(
        default=None,
        description="Slot to book. If omitted the first AVAILABLE slot for the vendor is chosen automatically.",
    )
    payment_method: str | None = Field(
        default="UPI",
        description="Payment method: UPI, CARD, WALLET, etc.",
    )
    pickup_time: str | None = Field(
        default=None,
        description="Desired pickup time (informational, stored on the order).",
    )
    voucher_code: str | None = Field(
        default=None,
        description="Optional voucher code to apply discount at checkout.",
    )
    points_to_redeem: float | None = Field(
        default=None,
        description="Optional rewards points to redeem at checkout.",
    )


def _generate_pickup_token() -> str:
    """Generate a short, unique alphanumeric pickup token like 'TNT-A3X9'."""
    chars = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(chars) for _ in range(4))
    return f"TNT-{suffix}"


@checkout_router.post("/checkout", summary="Checkout cart")
def checkout_alias(
    payload: CheckoutRequest | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Alias for POST /cart/checkout (optionally with slot_id)."""
    return checkout_cart_simple(payload=payload, db=db, user=user)


def _cart_key(user_id: int) -> str:
    return f"tnt:cart:user:{user_id}"


def _get_cart(user_id: int) -> dict:
    raw = redis_client.get(_cart_key(user_id))
    if not raw:
        return {"vendor_id": None, "items": []}

    try:
        cart = json.loads(raw)
        if not isinstance(cart, dict):
            return {"vendor_id": None, "items": []}
        return {
            "vendor_id": cart.get("vendor_id"),
            "items": cart.get("items", []),
        }
    except Exception:
        return {"vendor_id": None, "items": []}


def _save_cart(user_id: int, cart: dict) -> None:
    redis_client.setex(_cart_key(user_id), 60 * 60 * 12, json.dumps(cart))


def _cart_response(cart: dict) -> dict:
    total_amount = sum(int(item["price"]) * int(item["quantity"]) for item in cart["items"])
    total_items = sum(int(item["quantity"]) for item in cart["items"])
    return {
        "vendor_id": cart.get("vendor_id"),
        "items": cart.get("items", []),
        "total_items": total_items,
        "total_amount": total_amount,
    }


def _checkout_order_from_cart(
    slot_id: int,
    db_user: User,
    db: Session,
    payment_method: str | None = None,
    pickup_time: str | None = None,
    voucher_code: str | None = None,
    points_to_redeem: float | None = None,
) -> tuple[dict, int]:
    cart = _get_cart(db_user.id)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")

    items = [
        OrderItemCreate(menu_item_id=int(item["menu_item_id"]), quantity=int(item["quantity"]))
        for item in cart["items"]
    ]
    order, slot, total_amount, eta_minutes = checkout_order_for_user(db_user, slot_id, items, db)

    # ── Apply voucher discount ───────────────────────────────────────
    discount_amount = 0
    if voucher_code:
        try:
            from app.modules.rewards.service import redeem_voucher
            result = redeem_voucher(
                code=voucher_code,
                user_id=db_user.id,
                order_id=order.id,
                db=db,
            )
            discount_amount = result.get("discount_amount_paise", 0)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Voucher error: {str(e)}")

    # ── Apply points discount ────────────────────────────────────────
    points_discount_amount = 0
    if points_to_redeem and points_to_redeem > 0:
        try:
            from app.modules.rewards.service import redeem_points_for_order
            res = redeem_points_for_order(
                user_id=db_user.id,
                order_id=order.id,
                points_to_redeem=points_to_redeem,
                db=db
            )
            points_discount_amount = res.get("discount_amount_paise", 0)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Rewards error: {str(e)}")

    # ── Generate pickup token and attach to order ─────────────────────
    pickup_token = _generate_pickup_token()
    order.qr_code = pickup_token
    db.commit()  # must commit — checkout_order_for_user already committed its own tx

    # ── Auto-create "Order Placed" notification ───────────────────────
    notification = Notification(
        user_id=db_user.id,
        title="Order Placed",
        message="Your order has been placed.",
    )
    db.add(notification)
    db.flush()

    # ── Clear Redis cart ──────────────────────────────────────────────
    redis_client.delete(_cart_key(db_user.id))

    return {
        "order_id": order.id,
        "pickup_token": pickup_token,
        "status": "Order placed",
        "total_amount": order.total_amount,
        "discount_amount": discount_amount + points_discount_amount,
        "eta_minutes": eta_minutes,
        "payment_method": payment_method or "UPI",
        "pickup_load_label": get_load_label(slot.current_orders, slot.max_orders),
        "express_pickup_eligible": is_express_pickup_eligible(slot.current_orders, slot.max_orders),
    }, order.id


@router.get("/", summary="Get current user's cart")
def get_cart(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = _get_cart(db_user.id)
    return _cart_response(cart)


@router.get("/{user_id}", summary="Get cart by user ID (own cart or admin)")
def get_cart_by_user_id(
    user_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Returns the cart for *user_id*. Students may only fetch their own cart; admins can query any user."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Authenticated user not found")
    if db_user.id != user_id and db_user.role.value not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Cannot view another user's cart")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    cart = _get_cart(user_id)
    return _cart_response(cart)


@router.post("/add", summary="Add item to cart (alias for POST /cart/items)")
def add_to_cart(
    payload: SoloCartItemRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Convenience alias — identical behaviour to POST /cart/items."""
    return add_cart_item(payload, db=db, user=user)


@router.post("/update", summary="Update cart item quantity")
def update_cart_item(
    payload: CartUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Set the quantity of an existing item in the cart. Use POST /cart/add to add new items."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = _get_cart(db_user.id)
    found = False
    for item in cart["items"]:
        if int(item["menu_item_id"]) == int(payload.menu_item_id):
            item["quantity"] = int(payload.quantity)
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Item not in cart — use POST /cart/add to add it first")

    _save_cart(db_user.id, cart)
    return _cart_response(cart)


@router.post("/remove", summary="Remove item from cart (POST alias for DELETE /cart/items/{id})")
def remove_cart_item_post(
    payload: CartRemoveRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Remove a single menu item from the cart by menu_item_id."""
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = _get_cart(db_user.id)
    before_count = len(cart["items"])
    cart["items"] = [item for item in cart["items"] if int(item["menu_item_id"]) != int(payload.menu_item_id)]
    if len(cart["items"]) == before_count:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if not cart["items"]:
        cart["vendor_id"] = None
    _save_cart(db_user.id, cart)
    return _cart_response(cart)


@router.post("/checkout", summary="Checkout cart (auto-picks slot if slot_id omitted)")
def checkout_cart_simple(
    payload: CheckoutRequest | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Checkout the active cart.

    * If **slot_id** is supplied in the request body, that slot is used.
    * If omitted, the first `AVAILABLE` slot for the vendor in the cart is
      automatically selected.

    Returns order details including pickup_token and ETA on success.
    """
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = _get_cart(db_user.id)
    if not cart["items"]:
        raise HTTPException(status_code=400, detail="Cart is empty")

    slot_id = (payload.slot_id if payload else None)
    payment_method = (payload.payment_method if payload else None)
    pickup_time = (payload.pickup_time if payload else None)
    voucher_code = (payload.voucher_code if payload else None)
    points_to_redeem = (payload.points_to_redeem if payload else None)

    if slot_id is None:
        vendor_id = cart.get("vendor_id")
        if not vendor_id:
            raise HTTPException(status_code=400, detail="Cart has no vendor — cannot auto-select slot")
        slot = (
            db.query(Slot)
            .filter(Slot.vendor_id == int(vendor_id), Slot.status == SlotStatus.AVAILABLE)
            .order_by(Slot.start_time)
            .first()
        )
        if not slot:
            raise HTTPException(status_code=400, detail="No available slots for this vendor — supply slot_id explicitly")
        slot_id = slot.id

    response, _ = _checkout_order_from_cart(slot_id, db_user, db, payment_method, pickup_time, voucher_code, points_to_redeem)
    return response


@router.post("/items")
def add_cart_item(
    payload: SoloCartItemRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    menu_item = db.query(MenuItem).filter(MenuItem.id == payload.menu_item_id).first()
    if not menu_item:
        raise HTTPException(status_code=400, detail="Menu item not found")
    if not menu_item.is_available:
        raise HTTPException(status_code=400, detail="Menu item not available")

    vendor = db.query(User).filter(User.id == menu_item.vendor_id).first()
    if not vendor or vendor.role != UserRole.VENDOR or not vendor.is_active or not vendor.is_approved:
        raise HTTPException(status_code=400, detail="Vendor is not available")

    cart = _get_cart(db_user.id)

    existing_vendor_id = cart.get("vendor_id")
    if existing_vendor_id is not None and int(existing_vendor_id) != int(menu_item.vendor_id):
        raise HTTPException(status_code=400, detail="Cannot add items from multiple vendors")

    updated = False
    for item in cart["items"]:
        if int(item["menu_item_id"]) == int(payload.menu_item_id):
            item["quantity"] = int(item["quantity"]) + int(payload.quantity)
            updated = True
            break

    if not updated:
        cart["items"].append(
            {
                "menu_item_id": menu_item.id,
                "name": menu_item.name,
                "price": int(menu_item.price),
                "quantity": int(payload.quantity),
            }
        )

    cart["vendor_id"] = int(menu_item.vendor_id)
    _save_cart(db_user.id, cart)

    return _cart_response(cart)


@router.delete("/items/{menu_item_id}")
def remove_cart_item(
    menu_item_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    cart = _get_cart(db_user.id)
    before_count = len(cart["items"])
    cart["items"] = [item for item in cart["items"] if int(item["menu_item_id"]) != int(menu_item_id)]
    if len(cart["items"]) == before_count:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if not cart["items"]:
        cart["vendor_id"] = None

    _save_cart(db_user.id, cart)
    return _cart_response(cart)


@router.delete("/")
def clear_cart(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    redis_client.delete(_cart_key(db_user.id))
    return {"message": "Cart cleared"}


@router.post("/checkout/{slot_id}")
def checkout_cart(
    slot_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    response, _ = _checkout_order_from_cart(slot_id, db_user, db)
    return response


@router.post("/checkout/{slot_id}/pay")
def checkout_and_initiate_payment(
    slot_id: int,
    checkout_idempotency_key: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    idempotency_cache_key = None
    if checkout_idempotency_key:
        idempotency_cache_key = f"tnt:checkout_pay:{db_user.id}:{checkout_idempotency_key}"
        cached = redis_client.get(idempotency_cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

    checkout_response, order_id = _checkout_order_from_cart(slot_id, db_user, db)

    response = {
        "order_created": True,
        "payment_initiated": False,
        "order": checkout_response,
        "payment": None,
        "payment_error": None,
    }

    try:
        payment_response = initiate_payment(order_id=order_id, user=user, db=db)
        response["payment_initiated"] = True
        response["payment"] = payment_response
    except HTTPException as exc:
        response["payment_error"] = {
            "status_code": exc.status_code,
            "detail": exc.detail,
        }
    except Exception as exc:
        response["payment_error"] = {
            "status_code": 500,
            "detail": str(exc),
        }

    if idempotency_cache_key:
        redis_client.setex(idempotency_cache_key, 3600, json.dumps(response))

    return response
