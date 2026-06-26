"""Order state machine — single source of truth for lifecycle transitions.

Canonical states
-----------------------------
PLACED    — order submitted by student (replaces PENDING for new orders)
CONFIRMED — vendor has accepted the order
PREPARING — vendor is preparing the order
READY     — vendor has prepared the order; QR pickup can be generated
PICKED    — student has collected the order (terminal)
CANCELLED — order cancelled by student, vendor, or admin (terminal)

Backward-compatible legacy states (kept for existing DB rows)
------------------------------------------------------------
PENDING         → equivalent to PLACED
READY_FOR_PICKUP → equivalent to READY
COMPLETED       → equivalent to PICKED

Allowed transitions (product-defined)
--------------------------------------
                       → CONFIRMED  PREPARING  READY  PICKED  CANCELLED
  PLACED / PENDING     :     ✓                           ✓
  CONFIRMED            :                ✓                 ✓
  PREPARING            :                          ✓      ✓
  READY /
  READY_FOR_PICKUP     :                                 ✓  ✓
  PICKED / COMPLETED   :  (terminal — no further transitions)
  CANCELLED            :  (terminal — no further transitions)

``validate_transition`` is called by ``update_order_status`` BEFORE any
role-specific logic, so an invalid transition is always rejected regardless
of who is requesting it.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.modules.orders.model import OrderStatus

# ---------------------------------------------------------------------------
# Allowed transitions table
# Each key maps to the set of states it may legally transition into.
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    # ── Canonical new states ──────────────────────────────────────────────
    OrderStatus.PLACED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.PICKED, OrderStatus.CANCELLED},
    OrderStatus.PICKED: set(),      # terminal
    OrderStatus.CANCELLED: set(),   # terminal
    # ── Legacy / backward-compat states ──────────────────────────────────
    # PENDING behaves identically to PLACED.
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    # READY_FOR_PICKUP behaves identically to READY.
    OrderStatus.READY_FOR_PICKUP: {
        OrderStatus.PICKED,
        OrderStatus.COMPLETED,   # old completion path still allowed
        OrderStatus.CANCELLED,
    },
    # COMPLETED behaves identically to PICKED — terminal.
    OrderStatus.COMPLETED: set(),
}


def validate_transition(old_status: OrderStatus, new_status: OrderStatus) -> None:
    """Raise ``HTTPException(422)`` if the transition is not permitted.

    Parameters
    ----------
    old_status:
        The order's *current* status before the update.
    new_status:
        The requested *target* status.

    Raises
    ------
    HTTPException(422)
        When the transition is not in ``ALLOWED_TRANSITIONS``.
    HTTPException(400)
        When ``old_status`` is a terminal state (PICKED / COMPLETED /
        CANCELLED) and any transition is attempted.
    """
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())

    if not allowed and old_status in ALLOWED_TRANSITIONS:
        # Terminal state — no outgoing transitions at all.
        raise HTTPException(
            status_code=400,
            detail=(
                f"Order is already in a terminal state ({old_status.value}) "
                "and cannot be transitioned further."
            ),
        )

    if new_status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid state transition: '{old_status.value}' → '{new_status.value}'. "
                f"Allowed next states: {sorted(s.value for s in allowed) or 'none (terminal)'}."
            ),
        )
