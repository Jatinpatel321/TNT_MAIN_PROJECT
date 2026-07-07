from __future__ import annotations

import re
from typing import Dict


# Curated Unsplash links for known seeded menu items so the UI is deterministic.
_CURATED_MENU_IMAGES: Dict[str, str] = {
    "veg burger": "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=500&q=70",
    "classic veg burger": "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=500&q=70",
    "cheese burst burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500&q=70",
    "spicy paneer burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=500&q=70",
    "cold coffee": "https://images.unsplash.com/photo-1517701604599-bb29b5c7355c?auto=format&fit=crop&w=500&q=70",
    "masala chai latte": "https://images.unsplash.com/photo-1561336313-0bd5e0b27ec8?auto=format&fit=crop&w=500&q=70",
    "belgian chocolate shake": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=500&q=70",
    "oreo shake": "https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=500&q=70",
    "lemon iced tea": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=500&q=70",
    "detox green juice": "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=500&q=70",
    "power smoothie": "https://images.unsplash.com/photo-1623065422902-30500797343d?auto=format&fit=crop&w=500&q=70",
    "filter coffee": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=500&q=70",
    "margherita pizza": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=500&q=70",
    "farmhouse pizza": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=500&q=70",
    "tandoori paneer pizza": "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=500&q=70",
    "veggie loaded pizza": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=500&q=70",
    "pasta alfredo": "https://images.unsplash.com/photo-1612874742237-6526221588e3?auto=format&fit=crop&w=500&q=70",
    "pasta arrabiata": "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?auto=format&fit=crop&w=500&q=70",
    "garlic breadsticks": "https://images.unsplash.com/photo-1573145417855-6674cd739343?auto=format&fit=crop&w=500&q=70",
    "chilli cheese toast": "https://images.unsplash.com/photo-1542385151-efd9000785a0?auto=format&fit=crop&w=500&q=70",
    "garlic toastie": "https://images.unsplash.com/photo-1542385151-efd9000785a0?auto=format&fit=crop&w=500&q=70",
    "pesto cottage sandwich": "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=500&q=70",
    "paneer wrap": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=500&q=70",
    "hummus wrap": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=500&q=70",
    "blueberry muffin": "https://images.unsplash.com/photo-1558401391-7899b4bd5bbf?auto=format&fit=crop&w=500&q=70",
    "avocado toast": "https://images.unsplash.com/photo-1588137372308-15f75323ca8f?auto=format&fit=crop&w=500&q=70",
    "masala dosa": "https://images.unsplash.com/photo-1668236543090-d2f896914365?auto=format&fit=crop&w=500&q=70",
    "mysore masala dosa": "https://images.unsplash.com/photo-1668236543090-d2f896914365?auto=format&fit=crop&w=500&q=70",
    "idli sambar": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=500&q=70",
    "medu vada plate": "https://images.unsplash.com/photo-1630395822970-4b1d6cb5eb80?auto=format&fit=crop&w=500&q=70",
    "veg upma bowl": "https://images.unsplash.com/photo-1546833999-b9f58161460e?auto=format&fit=crop&w=500&q=70",
    "lemon rice": "https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=500&q=70",
    "chole bhature": "https://images.unsplash.com/photo-1626132978626-4b6c95c922af?auto=format&fit=crop&w=500&q=70",
    "loaded fries": "https://images.unsplash.com/photo-1630384060421-a4323ceca041?auto=format&fit=crop&w=500&q=70",
    "peri peri fries": "https://images.unsplash.com/photo-1630384060421-a4323ceca041?auto=format&fit=crop&w=500&q=70",
    "crispy corn pops": "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=500&q=70",
    "quinoa rainbow salad": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=500&q=70",
    "buddha bowl": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=500&q=70",
    "greek salad": "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=500&q=70",
    "falafel power bowl": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=500&q=70",
}


def _normalise(name: str | None) -> str:
    return (name or "").lower().strip()


def _query_from_name(name: str | None) -> str:
    # Convert a menu item name into a comma-separated Unsplash query.
    base = re.sub(r"[^a-z0-9]+", "+", _normalise(name)) or "campus"
    return base


def menu_image_for(name: str | None, category: str = "food") -> str:
    """Return a deterministic image URL for the menu item name.

    Uses a curated map first; otherwise falls back to an Unsplash query that
    matches the item name with a category hint (food / stationery).
    """

    key = _normalise(name)
    curated = _CURATED_MENU_IMAGES.get(key)
    if curated:
        return curated

    hint = "stationery,printing" if category == "stationery" else "food,cafe"
    query = f"{hint},{_query_from_name(name)}"
    return f"https://source.unsplash.com/600x400/?{query}"
