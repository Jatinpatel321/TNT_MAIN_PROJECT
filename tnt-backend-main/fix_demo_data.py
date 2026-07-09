"""One-off: repair demo image URLs and seed the empty stationery / profile tables.

- Rewrites every menu_items.image_url to a reliable images.unsplash.com link
  (the seed had left placehold.co / dead source.unsplash.com URLs).
- Seeds stationery_services for the three stationery stalls (was empty).
- Seeds vendor_profiles (location + hours) for all stalls (was empty).

Idempotent: safe to run more than once.
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:5461@localhost:5432/tnt")

from sqlalchemy import text

import app.database.init_db  # noqa: F401  — registers every ORM model
from app.database.session import SessionLocal
from app.modules.menu.image_utils import menu_image_for
from app.modules.menu.model import MenuItem
from app.modules.stationery.service_model import StationeryService
from app.modules.users.model import User, UserRole


BUSINESS_HOURS = {d: {"open": "09:00", "close": "21:00"} for d in
                  ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]}
BUSINESS_HOURS["sunday"] = {"open": "10:00", "close": "18:00"}

LOCATIONS = {
    "Campus Cafe": "Main Building, Ground Floor",
    "Parul Mess": "Hostel Block C, Mess Hall",
    "Juice Junction": "Sports Complex, Near Gate 2",
    "Stationery Shop": "Academic Block A, Room 12",
    "Book Nook": "Central Library, Level 1",
    "Tandoor Express": "Food Court, Stall 4",
    "Pizza Hub": "Food Court, Stall 7",
    "Art & Craft": "Design Block, Ground Floor",
}

STATIONERY_SERVICES = {
    # vendor user name -> list of (name, service_type, price_per_page, desc, unit)
    "Stationery Shop": [
        ("Black & White Print", "bw_print", 2, "Crisp A4 laser prints", "page"),
        ("Colour Print", "color_print", 8, "Vivid colour A4 prints", "page"),
        ("Photocopy / Xerox", "xerox", 1, "Fast bulk photocopying", "page"),
        ("Spiral Binding", "binding", 30, "Up to 200 pages", "book"),
    ],
    "Book Nook": [
        ("B&W Print", "bw_print", 2, "Standard document printing", "page"),
        ("Colour Print", "color_print", 9, "Photo-quality colour", "page"),
        ("Lamination (A4)", "lamination", 15, "Protect your documents", "sheet"),
    ],
    "Art & Craft": [
        ("Poster Print (A3)", "color_print", 25, "Large-format colour posters", "sheet"),
        ("Photo Print (4x6)", "color_print", 12, "Glossy photo prints", "photo"),
        ("Xerox", "xerox", 1, "Quick photocopies", "page"),
    ],
}


def fix_menu_images(db) -> int:
    n = 0
    for item in db.query(MenuItem).all():
        url = menu_image_for(item.name, item.category or "food")
        if item.image_url != url:
            item.image_url = url
            n += 1
    db.commit()
    return n


def seed_stationery(db) -> int:
    n = 0
    for vendor_name, services in STATIONERY_SERVICES.items():
        owner = (
            db.query(User)
            .filter(User.name == vendor_name, User.role == UserRole.VENDOR)
            .first()
        )
        if not owner:
            print(f"  ! vendor not found: {vendor_name}")
            continue
        for name, stype, ppp, desc, unit in services:
            exists = (
                db.query(StationeryService)
                .filter(StationeryService.vendor_id == owner.id, StationeryService.name == name)
                .first()
            )
            if exists:
                continue
            db.add(StationeryService(
                vendor_id=owner.id,
                name=name,
                service_type=stype,
                description=desc,
                price_per_page=ppp,
                price_per_unit=ppp,
                unit=unit,
                max_capacity=1000,
                current_load=0,
                is_available=True,
            ))
            n += 1
    db.commit()
    return n


def seed_vendor_profiles(db) -> int:
    n = 0
    rows = db.execute(text("SELECT vendor_id, owner_id, vendor_name, category FROM vendors")).fetchall()
    for vendor_id, owner_id, vendor_name, category in rows:
        exists = db.execute(
            text("SELECT 1 FROM vendor_profiles WHERE vendor_id = :vid"), {"vid": vendor_id}
        ).fetchone()
        if exists:
            continue
        import json
        db.execute(text("""
            INSERT INTO vendor_profiles
                (vendor_id, business_name, category, description, location, rating,
                 business_hours, pickup_instructions, holidays)
            VALUES
                (:vid, :bn, :cat, :desc, :loc, :rating, :hours, :pickup, :holidays)
        """), {
            "vid": vendor_id,
            "bn": vendor_name,
            "cat": category,
            "desc": f"{vendor_name} — your campus {category} stop.",
            "loc": LOCATIONS.get(vendor_name, "Campus"),
            "rating": 4.5,
            "hours": json.dumps(BUSINESS_HOURS),
            "pickup": "Show your pickup QR at the counter.",
            "holidays": json.dumps([]),
        })
        n += 1
    db.commit()
    return n


def main() -> None:
    db = SessionLocal()
    try:
        print("menu images updated:", fix_menu_images(db))
        print("stationery services added:", seed_stationery(db))
        print("vendor profiles added:", seed_vendor_profiles(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
