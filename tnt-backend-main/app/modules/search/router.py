"""Unified search & filter system.

GET /search
    Search across vendors, menu items, and stationery services with filters
    and sorting.

Query params
------------
q : str              Free-text search across vendor/item names
type : str           "all" | "food" | "stationery"   (default "all")
category : str       Vendor category filter (e.g. "cafe", "fast food")
price_min : int      Minimum price in paise
price_max : int      Maximum price in paise
min_rating : float   Minimum vendor rating
availability : bool  Only show available items / open vendors
prep_time_max : int  Max estimated prep time in minutes (food only)
sort : str           "popular" | "price_low" | "price_high" | "fastest" | "rating"
page : int           Page number (1-based)
page_size : int      Items per page (max 50)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, func, and_
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.load_insights import get_load_label, is_express_pickup_eligible
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole
from app.modules.search.schemas import SearchItemResult, SearchVendorResult, SearchResponse

router = APIRouter(prefix="/search", tags=["Search"])

VALID_SORTS = {"popular", "price_low", "price_high", "fastest", "rating"}
VALID_TYPES = {"all", "food", "stationery"}


def _vendor_profile(vendor_id: int, db: Session) -> dict[str, Any]:
    try:
        from sqlalchemy import text
        row = db.execute(
            text("SELECT category, description, rating, location FROM vendor_profiles WHERE vendor_id = :vid"),
            {"vid": vendor_id},
        ).fetchone()
        if row:
            return {"category": row[0], "description": row[1], "rating": float(row[2]), "location": row[3]}
    except Exception:
        pass
    return {"category": None, "description": None, "rating": 4.5, "location": None}


def _vendor_load_summary(vendor_id: int, db: Session) -> tuple[str, bool]:
    slots = db.query(Slot).filter(Slot.vendor_id == vendor_id).all()
    if not slots:
        return "LOW", False
    total_capacity = sum(s.max_orders for s in slots)
    total_orders = sum(s.current_orders for s in slots)
    return get_load_label(total_orders, total_capacity), is_express_pickup_eligible(total_orders, total_capacity)


def _vendor_images(name: str | None, vendor_type: str = "food") -> dict[str, str | None]:
    key = (name or "").lower().strip()
    _IMAGES: dict[str, dict[str, str]] = {
        "campus cafe": {"logo": "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?auto=format&fit=crop&w=400&q=70"},
        "burger hub": {"logo": "https://images.unsplash.com/photo-1586190848861-99c8a3da726c?auto=format&fit=crop&w=400&q=70"},
        "pizza station": {"logo": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=400&q=70"},
        "spice corner": {"logo": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=400&q=70"},
        "green bowl": {"logo": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=400&q=70"},
        "xerox point": {"logo": "https://images.unsplash.com/photo-1563321703-a12f71694f42?auto=format&fit=crop&w=400&q=70"},
        "print hub": {"logo": "https://images.unsplash.com/photo-1562564055-71e051d33c19?auto=format&fit=crop&w=400&q=70"},
        "campus stationery": {"logo": "https://images.unsplash.com/photo-1585336261022-680e295ce3fe?auto=format&fit=crop&w=400&q=70"},
    }
    imgs = _IMAGES.get(key, {})
    return {"logo_url": imgs.get("logo")}


def _search_vendors(
    q: str | None,
    search_type: str,
    category: str | None,
    min_rating: float | None,
    availability: bool | None,
    sort: str,
    db: Session,
) -> list[SearchVendorResult]:
    """Search vendors by name with filters."""
    base = db.query(User).filter(
        User.role == UserRole.VENDOR,
        User.is_approved == True,
        User.is_active == True,
    )

    if q:
        term = f"%{q}%"
        base = base.filter(User.name.ilike(term))

    if search_type == "food":
        food_ids = db.query(MenuItem.vendor_id).filter(MenuItem.is_available == True).distinct()
        base = base.filter(User.id.in_(food_ids))
    elif search_type == "stationery":
        stat_ids = db.query(StationeryService.vendor_id).filter(StationeryService.is_available == True).distinct()
        base = base.filter(User.id.in_(stat_ids))

    vendors = base.all()
    results: list[SearchVendorResult] = []

    for v in vendors:
        profile = _vendor_profile(v.id, db)

        if category and (profile.get("category") or "").lower() != category.lower():
            continue
        if min_rating is not None and profile.get("rating", 0) < min_rating:
            continue

        load_label, express = _vendor_load_summary(v.id, db)
        imgs = _vendor_images(v.name, v.vendor_type or search_type)

        if availability is not None and availability:
            if load_label == "FULL":
                continue

        results.append(SearchVendorResult(
            id=v.id,
            name=v.name,
            vendor_type=search_type if search_type != "all" else (v.vendor_type or "food"),
            description=profile.get("description"),
            rating=profile.get("rating", 4.5),
            category=profile.get("category"),
            location=profile.get("location"),
            logo_url=imgs.get("logo_url"),
            is_open=True,
            live_load_label=load_label,
            express_pickup_eligible=express,
        ))

    if sort == "rating":
        results.sort(key=lambda r: r.rating, reverse=True)
    elif sort == "popular":
        results.sort(key=lambda r: r.rating, reverse=True)

    return results


def _search_items(
    q: str | None,
    search_type: str,
    category: str | None,
    price_min: int | None,
    price_max: int | None,
    is_veg: bool | None,
    min_rating: float | None,
    availability: bool | None,
    sort: str,
    db: Session,
) -> list[SearchItemResult]:
    """Search menu items and stationery services."""
    results: list[SearchItemResult] = []

    if search_type in ("all", "food"):
        food_q = db.query(MenuItem).filter(MenuItem.is_available == True)
        if q:
            term = f"%{q}%"
            food_q = food_q.filter(MenuItem.name.ilike(term))

        if price_min is not None:
            food_q = food_q.filter(MenuItem.price >= price_min)
        if price_max is not None:
            food_q = food_q.filter(MenuItem.price <= price_max)
        if is_veg is not None:
            food_q = food_q.filter(MenuItem.is_veg == is_veg)
        if availability is not None and not availability:
            food_q = db.query(MenuItem).filter(MenuItem.is_available == False)
            if q:
                term = f"%{q}%"
                food_q = food_q.filter(MenuItem.name.ilike(term))

        for item in food_q.all():
            vendor = db.query(User).filter(User.id == item.vendor_id).first()
            if not vendor or not vendor.is_approved or not vendor.is_active:
                continue
            profile = _vendor_profile(vendor.id, db)
            if category and (profile.get("category") or "").lower() != category.lower():
                continue
            if min_rating is not None and profile.get("rating", 0) < min_rating:
                continue
            if availability is not None and availability and not item.is_available:
                continue

            results.append(SearchItemResult(
                id=item.id,
                vendor_id=item.vendor_id,
                name=item.name,
                description=item.description,
                price=item.price,
                item_type="food",
                is_available=item.is_available,
                image_url=item.image_url,
                vendor_name=vendor.name,
                vendor_rating=profile.get("rating", 4.5),
                vendor_category=profile.get("category"),
            ))

    if search_type in ("all", "stationery"):
        stat_q = db.query(StationeryService)
        if q:
            term = f"%{q}%"
            stat_q = stat_q.filter(StationeryService.name.ilike(term))

        if price_min is not None:
            stat_q = stat_q.filter(StationeryService.price_per_unit >= price_min)
        if price_max is not None:
            stat_q = stat_q.filter(StationeryService.price_per_unit <= price_max)

        for svc in stat_q.all():
            vendor = db.query(User).filter(User.id == svc.vendor_id).first()
            if not vendor or not vendor.is_approved or not vendor.is_active:
                continue
            profile = _vendor_profile(vendor.id, db)
            if category and (profile.get("category") or "").lower() != category.lower():
                continue
            if min_rating is not None and profile.get("rating", 0) < min_rating:
                continue
            if availability is not None and availability and not svc.is_available:
                continue

            results.append(SearchItemResult(
                id=svc.id,
                vendor_id=svc.vendor_id,
                name=svc.name,
                price=svc.price_per_unit,
                item_type="stationery",
                is_available=svc.is_available,
                unit=svc.unit,
                vendor_name=vendor.name,
                vendor_rating=profile.get("rating", 4.5),
                vendor_category=profile.get("category"),
            ))

    if sort == "price_low":
        results.sort(key=lambda r: r.price)
    elif sort == "price_high":
        results.sort(key=lambda r: r.price, reverse=True)
    elif sort == "rating":
        results.sort(key=lambda r: r.vendor_rating, reverse=True)
    elif sort == "popular":
        results.sort(key=lambda r: r.vendor_rating, reverse=True)
    elif sort == "fastest":
        # Stationery items generally faster; put them first, then food by rating
        results.sort(key=lambda r: (0 if r.item_type == "stationery" else 1, -r.vendor_rating))

    return results


@router.get("/", response_model=SearchResponse)
def search(
    q: str | None = Query(None, description="Search query"),
    type: str = Query("all", description="Filter: all, food, stationery"),
    category: str | None = Query(None, description="Vendor category"),
    price_min: int | None = Query(None, description="Min price (paise)"),
    price_max: int | None = Query(None, description="Max price (paise)"),
    is_veg: bool | None = Query(None, description="Filter by vegetarian items (food only)"),
    min_rating: float | None = Query(None, ge=0, le=5, description="Min vendor rating"),
    availability: bool | None = Query(None, description="Only available items/vendors"),
    prep_time_max: int | None = Query(None, description="Max prep time (minutes, food only)"),
    sort: str = Query("popular", description="Sort: popular, price_low, price_high, fastest, rating"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    if sort not in VALID_SORTS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid sort. Use one of: {', '.join(sorted(VALID_SORTS))}")
    if type not in VALID_TYPES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid type. Use one of: {', '.join(sorted(VALID_TYPES))}")

    vendors = _search_vendors(q, type, category, min_rating, availability, sort, db)
    items = _search_items(q, type, category, price_min, price_max, is_veg, min_rating, availability, sort, db)

    # Apply prep_time_max filter: estimate food prep ~3 min/order from slot queue
    if prep_time_max is not None:
        filtered_items = []
        for item in items:
            if item.item_type == "food":
                from app.modules.orders.model import Order
                slots = db.query(Slot).filter(Slot.vendor_id == item.vendor_id).all()
                queue = sum(s.current_orders for s in slots) if slots else 0
                est_prep = queue * 3
                if est_prep <= prep_time_max:
                    filtered_items.append(item)
            else:
                filtered_items.append(item)
        items = filtered_items

    # Pagination
    v_start = (page - 1) * page_size
    i_start = (page - 1) * page_size
    paginated_vendors = vendors[v_start : v_start + page_size]
    paginated_items = items[i_start : i_start + page_size]

    return SearchResponse(
        vendors=paginated_vendors,
        items=paginated_items,
        total_vendors=len(vendors),
        total_items=len(items),
    )


@router.get("/suggestions", response_model=list[str])
def search_suggestions(
    q: str = Query(..., min_length=1, description="Partial search term"),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Return autocomplete suggestions for a partial query."""
    term = f"%{q}%"
    suggestions: list[str] = []

    vendor_names = (
        db.query(User.name)
        .filter(User.role == UserRole.VENDOR, User.is_approved == True, User.name.ilike(term))
        .limit(limit)
        .all()
    )
    suggestions.extend(v[0] for v in vendor_names if v[0])

    remaining = limit - len(suggestions)
    if remaining > 0:
        menu_names = (
            db.query(MenuItem.name)
            .filter(MenuItem.name.ilike(term))
            .limit(remaining)
            .all()
        )
        suggestions.extend(m[0] for m in menu_names if m[0])

    remaining = limit - len(suggestions)
    if remaining > 0:
        svc_names = (
            db.query(StationeryService.name)
            .filter(StationeryService.name.ilike(term))
            .limit(remaining)
            .all()
        )
        suggestions.extend(s[0] for s in svc_names if s[0])

    return suggestions[:limit]
