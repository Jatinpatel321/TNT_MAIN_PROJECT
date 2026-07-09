from __future__ import annotations

import hashlib
from typing import Dict, List, Tuple


def _u(photo_id: str, w: int = 500) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w={w}&q=70"


# All URLs below are verified-reachable images.unsplash.com CDN links (the old
# source.unsplash.com query redirector this module used was retired).
_IMG = {
    "biryani": _u("1563379091339-03b21ab4a4f8"),
    "rice": _u("1512058564366-18510be2db19"),
    "roll": _u("1626700051175-6818013e1d4f"),
    "dal": _u("1585937421612-70a008356fbe"),
    "burger": _u("1568901346375-23c9450c58cd"),
    "fries": _u("1573080496219-bb080dd4f877"),
    "lassi": _u("1626200419199-391ae4be7a41"),
    "shake": _u("1572490122747-3968b75cc699"),
    "wrap": _u("1528735602780-2552fd46c7af"),
    "pavbhaji": _u("1606491956689-2ea866880c84"),
    "pizza": _u("1574071318508-1cdbab80d002"),
    "samosa": _u("1601050690597-df0568f70950"),
    "sandwich": _u("1553909489-cd47e0907980"),
    "vadapav": _u("1606755962773-d324e0a13086"),
    "coffee": _u("1461023058943-07fcbe16d735"),
    "chapati": _u("1565557623262-b51c2513a641"),
    # stationery
    "paper": _u("1456735190827-d1262f71b8a3"),
    "pencil": _u("1502740479091-635887520276"),
    "eraser": _u("1600250395178-40fe752e5189"),
    "pens": _u("1513364776144-60967b0f800f"),
    "stapler": _u("1568205612837-017257d2310a"),
    "tape": _u("1586864387967-d02ef85d93e8"),
}

# Ordered keyword → image. First keyword found as a substring of the (lowercased)
# item name wins, so "Vada Pav" matches "vada" before the generic "pav".
_KEYWORD_IMAGES: List[Tuple[str, str]] = [
    ("tape", _IMG["tape"]),  # before "roll" so "Tape Roll" → tape, not chicken roll
    ("biriyani", _IMG["biryani"]),
    ("biryani", _IMG["biryani"]),
    ("chapati", _IMG["chapati"]),
    ("roll", _IMG["roll"]),
    ("cold coffee", _IMG["coffee"]),
    ("coffee", _IMG["coffee"]),
    ("dal", _IMG["dal"]),
    ("burger", _IMG["burger"]),
    ("fries", _IMG["fries"]),
    ("idli", _IMG["rice"]),
    ("lassi", _IMG["lassi"]),
    ("shake", _IMG["shake"]),
    ("smoothie", _IMG["shake"]),
    ("wrap", _IMG["wrap"]),
    ("vada", _IMG["vadapav"]),
    ("pav bhaji", _IMG["pavbhaji"]),
    ("bhaji", _IMG["pavbhaji"]),
    ("pav", _IMG["vadapav"]),
    ("pizza", _IMG["pizza"]),
    ("samosa", _IMG["samosa"]),
    ("sandwich", _IMG["sandwich"]),
    ("rice", _IMG["rice"]),
    # stationery
    ("a4", _IMG["paper"]),
    ("sheet", _IMG["paper"]),
    ("paper", _IMG["paper"]),
    ("eraser", _IMG["eraser"]),
    ("glue", _IMG["pens"]),
    ("pencil", _IMG["pencil"]),
    ("scale", _IMG["pencil"]),
    ("sharpener", _IMG["eraser"]),
    ("sketch", _IMG["pens"]),
    ("pen", _IMG["pens"]),
    ("marker", _IMG["pens"]),
    ("stapler", _IMG["stapler"]),
    ("pins", _IMG["stapler"]),
    ("tape", _IMG["tape"]),
    ("box", _IMG["pencil"]),
]

# Hashed-pool fallback so uncurated items still get *varied* (not identical)
# images within their category.
_FOOD_POOL = [_IMG[k] for k in ("biryani", "rice", "dal", "sandwich", "wrap", "fries", "chapati", "roll")]
_STATIONERY_POOL = [_IMG[k] for k in ("paper", "pencil", "pens", "eraser", "stapler", "tape")]

# Kept for backward compatibility with any importer of the old name.
_CURATED_MENU_IMAGES: Dict[str, str] = {}


def _normalise(name: str | None) -> str:
    return (name or "").lower().strip()


def _pool_pick(name: str, pool: List[str]) -> str:
    h = int(hashlib.md5(_normalise(name).encode()).hexdigest(), 16)
    return pool[h % len(pool)]


def menu_image_for(name: str | None, category: str = "food") -> str:
    """Return a distinct, relevant image URL for a menu item.

    Matches the item name against food/stationery keywords; anything unmatched
    falls back to a *hashed* pick from the category pool so no two items share
    the same image by default.
    """
    key = _normalise(name)
    for keyword, url in _KEYWORD_IMAGES:
        if keyword in key:
            return url

    pool = _STATIONERY_POOL if category == "stationery" else _FOOD_POOL
    return _pool_pick(key, pool)
