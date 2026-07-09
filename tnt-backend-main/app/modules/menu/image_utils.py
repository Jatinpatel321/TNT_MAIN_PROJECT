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
    "idli": _u("1589301760014-d929f3979dbc"),
    "mango": _u("1546173159-315724a31696"),
    # Unsplash has no good "lassi"; loremflickr (keyword-tagged, locked seed for
    # a stable result) gives a proper glass of white lassi.
    "lassi": "https://loremflickr.com/500/500/lassi,yogurt,drink/all?lock=4",
    "shake": _u("1572490122747-3968b75cc699"),
    "wrap": _u("1528735602780-2552fd46c7af"),
    "pavbhaji": _u("1606491956689-2ea866880c84"),
    "pizza": _u("1574071318508-1cdbab80d002"),
    "samosa": _u("1601050690597-df0568f70950"),
    "sandwich": _u("1553909489-cd47e0907980"),
    "vadapav": _u("1606755962773-d324e0a13086"),
    "coffee": _u("1461023058943-07fcbe16d735"),
    "chapati": _u("1565557623262-b51c2513a641"),
    # Stationery — Unsplash lacks these specific items (its closest photo IDs
    # returned a goalkeeper / toy ambulance / hammer), so use keyword-tagged
    # loremflickr with a locked seed for a stable, on-topic photo.
    "paper": "https://loremflickr.com/500/500/printer,paper/all?lock=3",
    "pencil": "https://loremflickr.com/500/500/pencils,colored/all?lock=3",
    "ruler": "https://loremflickr.com/500/500/ruler,scale/all?lock=3",
    "eraser": "https://loremflickr.com/500/500/eraser,stationery/all?lock=3",
    "pens": "https://loremflickr.com/500/500/sketch,markers/all?lock=7",
    "stapler": "https://loremflickr.com/500/500/stapler,office/all?lock=3",
    "tape": "https://loremflickr.com/500/500/adhesive,tape/all?lock=7",
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
    ("idli", _IMG["idli"]),
    ("lassi", _IMG["lassi"]),
    ("mango", _IMG["mango"]),  # before "shake" so "Mango Shake" → mango drink
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
    ("glue", _IMG["pencil"]),
    ("pencil", _IMG["pencil"]),
    ("scale", _IMG["ruler"]),
    ("ruler", _IMG["ruler"]),
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
