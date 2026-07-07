from datetime import datetime

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.faculty_policy import is_slot_in_faculty_priority_window
from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.core.rate_limit import check_rate_limit
from app.core.security import get_current_user, require_role
from app.core.university_policy import get_university_policy
from app.modules.orders.model import Order
from app.modules.slots.model import Slot, SlotBooking, SlotStatus, BookingStatus
from app.modules.slots.schemas import (
    BulkSlotCreate,
    SlotBookRequest,
    SlotBookingResponse,
    SlotCancelResponse,
    SlotCreate,
    SlotLockResponse,
    SlotRecommendationResponse,
    SlotResponse,
    SlotStatus as SlotStatusSchema,
    SlotUpdate,
    SlotCapacityRuleCreate,
    SlotCapacityRuleUpdate,
    SlotCapacityRuleResponse,
    SlotRuleCreate,
    SlotRuleUpdate,
    SlotRuleResponse,
    SlotAnalyticsResponse,
)
from app.modules.slots.service import (
    book_slot,
    cancel_slot_booking,
    generate_stationery_slots,
    get_user_bookings,
    lock_slot,
    recommend_best_slot,
    unlock_slot,
    create_slot_capacity_rule,
    get_slot_capacity_rules,
    update_slot_capacity_rule,
    delete_slot_capacity_rule,
    create_slot_rule,
    get_slot_rules,
    update_slot_rule,
    delete_slot_rule,
    get_slot_analytics,
    bulk_create_slots,
    update_slot,
    delete_slot,
)
from app.modules.slots.schemas import (
    CombinedBookingRequest,
    CombinedBookingResponse,
)
from app.modules.slots.combined_service import create_combined_booking
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User

router = APIRouter(prefix="/slots", tags=["Slots"])


def _slot_to_response(s: Slot, db: Session, is_ai_recommended: bool = False) -> SlotResponse:
    available = max(s.max_orders - s.current_orders, 0)
    queue_size = s.current_orders
    prep_time = 3  # default minutes per order
    estimated_wait = queue_size * prep_time

    # Check faculty priority
    faculty_priority = is_slot_in_faculty_priority_window(s.start_time.hour)

    # Compute queue size from actual orders
    order_count = db.query(Order).filter(Order.slot_id == s.id).count()
    if order_count > 0:
        queue_size = order_count

    return SlotResponse(
        id=s.id,
        vendor_id=s.vendor_id,
        start_time=s.start_time,
        end_time=s.end_time,
        max_orders=s.max_orders,
        current_orders=s.current_orders,
        status=s.status.value if hasattr(s.status, "value") else s.status,
        load_label=get_load_label(s.current_orders, s.max_orders),
        express_pickup_eligible=is_express_pickup_eligible(s.current_orders, s.max_orders),
        is_locked=s.is_locked if hasattr(s, "is_locked") else False,
        available_capacity=available,
        faculty_priority=faculty_priority,
        queue_size=queue_size,
        estimated_wait=estimated_wait,
        is_ai_recommended=is_ai_recommended,
    )


@router.get("/", response_model=List[SlotResponse], summary="List available slots")
def list_slots(
    vendor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Return available slots; optionally filter by vendor."""
    query = db.query(Slot)
    if vendor_id is not None:
        is_stationery = db.query(StationeryService).filter(StationeryService.vendor_id == vendor_id).first() is not None
        if is_stationery:
            generate_stationery_slots(vendor_id, db)
        query = query.filter(Slot.vendor_id == vendor_id)

    slots = query.order_by(Slot.start_time).all()
    return [_slot_to_response(s, db) for s in slots]


@router.get(
    "/recommend/{vendor_id}",
    response_model=SlotRecommendationResponse,
    summary="AI powered best slot suggestion",
)
def recommend_slot(
    vendor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    is_stationery = db.query(StationeryService).filter(StationeryService.vendor_id == vendor_id).first() is not None
    if is_stationery:
        generate_stationery_slots(vendor_id, db)
    return recommend_best_slot(vendor_id, db)


@router.get("/my-bookings", response_model=List[SlotBookingResponse], summary="Get user's slot bookings")
def my_bookings(
    active_only: bool = True,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    bookings = get_user_bookings(db_user.id, db, active_only=active_only)
    return bookings


@router.post("/", response_model=SlotResponse)
def create_slot(
    slot: SlotCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    if slot.end_time <= slot.start_time:
        raise HTTPException(status_code=400, detail="Invalid slot timing")

    policy = get_university_policy()
    if policy.get("enabled", False):
        duration_minutes = int((slot.end_time - slot.start_time).total_seconds() // 60)
        if duration_minutes < int(policy.get("min_slot_duration_minutes", 15)):
            raise HTTPException(status_code=400, detail="Slot duration violates university policy")

    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not db_user.is_approved:
        raise HTTPException(status_code=403, detail="Vendor not approved")

    new_slot = Slot(
        vendor_id=db_user.id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        max_orders=slot.max_orders,
        current_orders=0,
        status=SlotStatus.AVAILABLE,
    )

    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)

    return _slot_to_response(new_slot, db)


@router.post("/{slot_id}/book", summary="Book a slot")
def book(
    slot_id: int,
    payload: SlotBookRequest | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    # Faculty priority check
    role = (db_user.role.value or "").lower()
    if is_slot_in_faculty_priority_window(slot.start_time.hour) and role not in {"faculty", "admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="This slot is reserved for faculty during priority window")

    # Rate limit: 5 booking attempts per 60 seconds per user
    check_rate_limit(
        key=f"slot_book:user:{user['id']}",
        limit=5,
        window_seconds=60,
    )

    # Slot lock check
    if hasattr(slot, "is_locked") and slot.is_locked:
        raise HTTPException(status_code=423, detail="Slot is currently locked by vendor")

    order_id = payload.order_id if payload else None
    slot, booking = book_slot(slot_id, db_user.id, db, order_id=order_id)

    return {
        "message": "Slot booked successfully",
        "slot_id": slot.id,
        "booking_id": booking.id,
        "current_orders": slot.current_orders,
        "available_capacity": max(slot.max_orders - slot.current_orders, 0),
        "status": slot.status.value if hasattr(slot.status, "value") else slot.status,
        "load_label": get_load_label(slot.current_orders, slot.max_orders),
        "express_pickup_eligible": is_express_pickup_eligible(slot.current_orders, slot.max_orders),
    }


@router.post("/{slot_id}/cancel", summary="Cancel a slot booking")
def cancel_booking(
    slot_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Find the user's active booking for this slot
    booking = db.query(SlotBooking).filter(
        SlotBooking.slot_id == slot_id,
        SlotBooking.user_id == db_user.id,
        SlotBooking.status == BookingStatus.CONFIRMED,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="No active booking found for this slot")

    slot, booking = cancel_slot_booking(booking.id, db_user.id, db)

    return SlotCancelResponse(
        message="Booking cancelled successfully",
        slot_id=slot.id,
        booking_id=booking.id,
        current_orders=slot.current_orders,
        status=slot.status.value if hasattr(slot.status, "value") else slot.status,
    )


@router.post("/{slot_id}/lock", response_model=SlotLockResponse, summary="Lock a slot (vendor only)")
def lock_slot_endpoint(
    slot_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.vendor_id != db_user.id:
        raise HTTPException(status_code=403, detail="Cannot lock another vendor's slot")

    slot = lock_slot(slot_id, db, locked_by=f"vendor:{db_user.id}")
    return SlotLockResponse(message="Slot locked", slot_id=slot.id, is_locked=True)


@router.post("/{slot_id}/unlock", response_model=SlotLockResponse, summary="Unlock a slot (vendor only)")
def unlock_slot_endpoint(
    slot_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.vendor_id != db_user.id:
        raise HTTPException(status_code=403, detail="Cannot unlock another vendor's slot")

    slot = unlock_slot(slot_id, db)
    return SlotLockResponse(message="Slot unlocked", slot_id=slot.id, is_locked=False)


# ── Advanced Slot Management Endpoints ─────────────────────────────────────


@router.put("/{slot_id}", response_model=SlotResponse, summary="Update a slot (vendor only)")
def update_slot_endpoint(
    slot_id: int,
    slot_update: SlotUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = slot_update.model_dump(exclude_unset=True)
    slot = update_slot(slot_id, db_user.id, update_data, db)
    return _slot_to_response(slot, db)


@router.delete("/{slot_id}", summary="Delete a slot (vendor only)")
def delete_slot_endpoint(
    slot_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    delete_slot(slot_id, db_user.id, db)
    return {"message": "Slot deleted successfully"}


@router.post("/bulk-create", response_model=List[SlotResponse], summary="Bulk create slots (vendor only)")
def bulk_create_slots_endpoint(
    bulk_data: BulkSlotCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    slot_data = bulk_data.model_dump()
    slot_data["vendor_id"] = db_user.id
    slots = bulk_create_slots(db_user.id, slot_data, db)
    return [_slot_to_response(s, db) for s in slots]


@router.get("/analytics", response_model=SlotAnalyticsResponse, summary="Get slot analytics (vendor only)")
def get_slot_analytics_endpoint(
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    analytics = get_slot_analytics(db_user.id, db)
    return SlotAnalyticsResponse(**analytics)


# ── Slot Capacity Rules Endpoints ──────────────────────────────────────────


@router.post("/capacity-rules", response_model=SlotCapacityRuleResponse, summary="Create capacity rule (vendor only)")
def create_capacity_rule(
    rule: SlotCapacityRuleCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    rule_data = rule.model_dump()
    new_rule = create_slot_capacity_rule(db_user.id, rule_data, db)
    return SlotCapacityRuleResponse.model_validate(new_rule.__dict__)


@router.get("/capacity-rules", response_model=List[SlotCapacityRuleResponse], summary="Get capacity rules (vendor only)")
def get_capacity_rules(
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    rules = get_slot_capacity_rules(db_user.id, db)
    return [SlotCapacityRuleResponse.model_validate(r.__dict__) for r in rules]


@router.put("/capacity-rules/{rule_id}", response_model=SlotCapacityRuleResponse, summary="Update capacity rule (vendor only)")
def update_capacity_rule(
    rule_id: int,
    rule_update: SlotCapacityRuleUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = rule_update.model_dump(exclude_unset=True)
    rule = update_slot_capacity_rule(rule_id, db_user.id, update_data, db)
    return SlotCapacityRuleResponse.model_validate(rule.__dict__)


@router.delete("/capacity-rules/{rule_id}", summary="Delete capacity rule (vendor only)")
def delete_capacity_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    delete_slot_capacity_rule(rule_id, db_user.id, db)
    return {"message": "Capacity rule deleted successfully"}


# ── Slot Rules Endpoints ────────────────────────────────────────────────────


@router.post("/rules", response_model=SlotRuleResponse, summary="Create slot rule (vendor only)")
def create_rule(
    rule: SlotRuleCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    rule_data = rule.model_dump()
    new_rule = create_slot_rule(db_user.id, rule_data, db)
    return SlotRuleResponse(
        id=new_rule.id,
        vendor_id=new_rule.vendor_id,
        rule_type=new_rule.rule_type,
        rule_config=json.loads(new_rule.rule_config) if isinstance(new_rule.rule_config, str) else new_rule.rule_config,
        is_enabled=new_rule.is_enabled,
        priority=new_rule.priority,
        created_at=new_rule.created_at,
        updated_at=new_rule.updated_at,
    )


@router.get("/rules", response_model=List[SlotRuleResponse], summary="Get slot rules (vendor only)")
def get_rules(
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    rules = get_slot_rules(db_user.id, db)
    return [
        SlotRuleResponse(
            id=r.id,
            vendor_id=r.vendor_id,
            rule_type=r.rule_type,
            rule_config=json.loads(r.rule_config) if isinstance(r.rule_config, str) else r.rule_config,
            is_enabled=r.is_enabled,
            priority=r.priority,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.put("/rules/{rule_id}", response_model=SlotRuleResponse, summary="Update slot rule (vendor only)")
def update_rule(
    rule_id: int,
    rule_update: SlotRuleUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = rule_update.model_dump(exclude_unset=True)
    rule = update_slot_rule(rule_id, db_user.id, update_data, db)
    return SlotRuleResponse(
        id=rule.id,
        vendor_id=rule.vendor_id,
        rule_type=rule.rule_type,
        rule_config=json.loads(rule.rule_config) if isinstance(rule.rule_config, str) else rule.rule_config,
        is_enabled=rule.is_enabled,
        priority=rule.priority,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/rules/{rule_id}", summary="Delete slot rule (vendor only)")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("vendor")),
):
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    delete_slot_rule(rule_id, db_user.id, db)
    return {"message": "Rule deleted successfully"}


# ── Combined Booking Endpoint ──────────────────────────────────────────────


@router.post(
    "/combined-booking",
    response_model=CombinedBookingResponse,
    summary="Book food + stationery together against the same slot window",
)
def combined_booking(
    payload: CombinedBookingRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Accept a food order AND a stationery job payload and book both against
    the SAME slot window.  Validates capacity for both sub-orders before
    committing, then returns a single order that covers both.

    Existing independent food-only and stationery-only flows remain untouched.
    """
    db_user = db.query(User).filter(User.phone == user["phone"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # At least one of food or stationery must be present
    if not payload.food_items and not payload.stationery_items:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one food item or one stationery item",
        )

    # Faculty priority check
    slot = db.query(Slot).filter(Slot.id == payload.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    role = (db_user.role.value or "").lower()
    if is_slot_in_faculty_priority_window(slot.start_time.hour) and role not in {"faculty", "admin", "super_admin"}:
        raise HTTPException(status_code=403, detail="This slot is reserved for faculty during priority window")

    # Build dict payloads for the service layer
    food_items = [{"menu_item_id": fi.menu_item_id, "quantity": fi.quantity} for fi in payload.food_items]
    stationery_items = [
        {
            "service_id": si.service_id,
            "quantity": si.quantity,
            "file_url": si.file_url,
        }
        for si in payload.stationery_items
    ]

    result = create_combined_booking(
        user_id=db_user.id,
        slot_id=payload.slot_id,
        food_items=food_items,
        stationery_items=stationery_items,
        db=db,
    )

    return CombinedBookingResponse(**result)
