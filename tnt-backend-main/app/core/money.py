"""Money helpers.

Amounts are stored and moved through the application as **Indian rupees** using
``Decimal`` (SQLAlchemy ``Numeric(10, 2)`` columns). Paise only exists at the
Razorpay boundary, because the gateway API transacts in integer paise.

Use :func:`to_paise` when sending an amount TO Razorpay and :func:`from_paise`
when reading an amount back FROM Razorpay (or a Razorpay webhook).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

TWO_PLACES = Decimal("0.01")


def as_rupees(value: Any) -> Decimal:
    """Coerce any numeric/str/Decimal to a 2-dp rupee ``Decimal``."""
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_paise(rupees: Any) -> int:
    """Rupees → integer paise (for the Razorpay API boundary only)."""
    return int((Decimal(str(rupees or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_paise(paise: Any) -> Decimal:
    """Integer paise (from Razorpay) → rupee ``Decimal``."""
    return (Decimal(str(paise or 0)) / 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def json_default(o: Any):
    """``json.dumps(default=...)`` helper so Decimal money serializes as a number.

    Used by the Redis pub/sub publishers whose payloads now carry Decimal
    amounts (``Numeric`` columns).
    """
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
