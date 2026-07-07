"""Backfill missing vendor/menu images with Unsplash placeholders.

Run:
    python scripts/fill_missing_images.py

This is idempotent: only updates records whose image_url is null/empty.
"""
from __future__ import annotations

from typing import Optional

from app.database.session import SessionLocal
from app.modules.menu.model import MenuItem
from app.modules.stationery.service_model import StationeryService

# Importing group_cart models ensures the SQLAlchemy registry knows about Group/GroupMember
# relationships referenced from User before we touch the ORM. This avoids mapper resolution
# errors when running the script standalone.
from app.modules.group_cart import model as _group_models  # noqa: F401

FOOD_IMAGES = [
    ("burger", "https://source.unsplash.com/600x400/?burger"),
    ("pizza", "https://source.unsplash.com/600x400/?pizza"),
    ("fries", "https://source.unsplash.com/600x400/?fries"),
    ("sandwich", "https://source.unsplash.com/600x400/?sandwich"),
    ("wrap", "https://source.unsplash.com/600x400/?wrap"),
    ("dosa", "https://source.unsplash.com/600x400/?dosa"),
    ("idli", "https://source.unsplash.com/600x400/?idli"),
    ("rice", "https://source.unsplash.com/600x400/?rice"),
    ("pasta", "https://source.unsplash.com/600x400/?pasta"),
    ("noodles", "https://source.unsplash.com/600x400/?noodles"),
    ("coffee", "https://source.unsplash.com/600x400/?coffee"),
    ("chai", "https://source.unsplash.com/600x400/?tea"),
    ("shake", "https://source.unsplash.com/600x400/?milkshake"),
    ("juice", "https://source.unsplash.com/600x400/?juice"),
    ("salad", "https://source.unsplash.com/600x400/?salad"),
    ("bowl", "https://source.unsplash.com/600x400/?bowl"),
    ("muffin", "https://source.unsplash.com/600x400/?muffin"),
    ("cake", "https://source.unsplash.com/600x400/?cake"),
    ("biryani", "https://source.unsplash.com/600x400/?biryani"),
]

STATIONERY_IMAGES = [
    ("print", "https://source.unsplash.com/600x400/?printing"),
    ("xerox", "https://source.unsplash.com/600x400/?xerox"),
    ("copy", "https://source.unsplash.com/600x400/?copy-shop"),
    ("poster", "https://source.unsplash.com/600x400/?poster-printing"),
    ("banner", "https://source.unsplash.com/600x400/?banner-print"),
    ("binding", "https://source.unsplash.com/600x400/?book-binding"),
    ("notebook", "https://source.unsplash.com/600x400/?notebook"),
    ("pen", "https://source.unsplash.com/600x400/?pen"),
    ("stapler", "https://source.unsplash.com/600x400/?stationery"),
]

FALLBACK_FOOD = "https://source.unsplash.com/600x400/?food"
FALLBACK_STATIONERY = "https://source.unsplash.com/600x400/?stationery"


def pick_image(name: str, is_stationery: bool) -> str:
    """Return a best-effort image URL based on keywords."""
    lowered = name.lower()
    choices = STATIONERY_IMAGES if is_stationery else FOOD_IMAGES
    for keyword, url in choices:
        if keyword in lowered:
            return url
    return FALLBACK_STATIONERY if is_stationery else FALLBACK_FOOD


def vendor_is_stationery(db, vendor_id: int) -> bool:
    return db.query(StationeryService).filter(StationeryService.vendor_id == vendor_id).first() is not None


def backfill_menu_images(db) -> int:
    rows = (
        db.query(MenuItem)
        .filter((MenuItem.image_url == None) | (MenuItem.image_url == ""))  # noqa: E711
        .all()
    )
    updated = 0
    for item in rows:
        is_stationery = vendor_is_stationery(db, item.vendor_id)
        item.image_url = pick_image(item.name, is_stationery)
        updated += 1
    if updated:
        db.commit()
    return updated


def main():
    db = SessionLocal()
    try:
        menu_updates = backfill_menu_images(db)
        print(f"Menu items updated: {menu_updates}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
