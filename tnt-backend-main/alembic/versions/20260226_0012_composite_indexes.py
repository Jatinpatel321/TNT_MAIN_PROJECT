"""composite_indexes

Adds targeted composite indexes on the highest-traffic column pairs to
accelerate the most common query patterns observed in the application:

  orders (vendor_id, status, created_at)
    → vendor dashboard: filter by vendor + state, ordered by time.

  orders (user_id, created_at)
    → student "my orders": filter by user, ordered by recency.

  order_items (order_id)
    → join from orders → order_items in placement / analytics queries.

  order_history (order_id)
    → timeline endpoint reads all history rows for a given order.

  payments (order_id, status)
    → payment lookup by order, filtered to specific payment statuses.

  notifications (user_id, is_read)
    → unread notification fetch per user.

  feedback (vendor_id, created_at)
    → vendor feedback summary aggregations.

All indexes are created with an existence-guard so the migration is
idempotent and safe to re-run in any environment (SQLite for tests,
PostgreSQL for production).

Revision ID: 20260226_0012
Revises: 20260226_0011
Create Date: 2026-02-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260226_0012"
down_revision = "20260226_0011"
branch_labels = None
depends_on = None


def _index_exists(index_name: str) -> bool:
    """Return True if an index with this name already exists in the DB."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    # Inspector.get_indexes is per-table; we use dialect-agnostic reflection.
    for table_name in inspector.get_table_names():
        for idx in inspector.get_indexes(table_name):
            if idx["name"] == index_name:
                return True
    return False


def _create_index(name: str, table: str, columns: list[str]) -> None:
    """Create index only when it does not already exist."""
    if not _index_exists(name):
        op.create_index(name, table, columns)


def upgrade() -> None:
    # ── orders ────────────────────────────────────────────────────────────
    _create_index(
        "ix_orders_vendor_status_created",
        "orders",
        ["vendor_id", "status", "created_at"],
    )
    _create_index(
        "ix_orders_user_created",
        "orders",
        ["user_id", "created_at"],
    )

    # ── order_items ────────────────────────────────────────────────────────
    _create_index(
        "ix_order_items_order_id",
        "order_items",
        ["order_id"],
    )

    # ── order_history ──────────────────────────────────────────────────────
    _create_index(
        "ix_order_history_order_id",
        "order_history",
        ["order_id"],
    )

    # ── payments ───────────────────────────────────────────────────────────
    _create_index(
        "ix_payments_order_status",
        "payments",
        ["order_id", "status"],
    )

    # ── notifications ──────────────────────────────────────────────────────
    _create_index(
        "ix_notifications_user_read",
        "notifications",
        ["user_id", "is_read"],
    )

    # ── feedback ───────────────────────────────────────────────────────────
    _create_index(
        "ix_feedback_vendor_created",
        "feedback",
        ["vendor_id", "created_at"],
    )


def downgrade() -> None:
    for name in [
        "ix_feedback_vendor_created",
        "ix_notifications_user_read",
        "ix_payments_order_status",
        "ix_order_history_order_id",
        "ix_order_items_order_id",
        "ix_orders_user_created",
        "ix_orders_vendor_status_created",
    ]:
        try:
            op.drop_index(name)
        except Exception:
            pass
