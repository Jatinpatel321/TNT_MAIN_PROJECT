"""add fraud_flag and flagged_at to orders table

Revision ID: 20260226_0010
Revises: 20260226_0009
Create Date: 2026-02-26 00:00:00

Context
-------
The admin endpoint ``POST /admin/orders/{order_id}/fraud`` previously used
``hasattr(order, 'fraud_flag')`` to guard the write.  Because the column
did not exist on the model, ``hasattr`` always returned False and the fraud
flag was silently never persisted.

This migration adds the two columns that enforce the strict schema:

  orders.fraud_flag  — BOOLEAN NOT NULL DEFAULT FALSE
                       Replaces the fragile hasattr guard; the column is
                       always present so ORM access is always safe.

  orders.flagged_at  — DATETIME NULL
                       Audit timestamp set when fraud_flag flips to True.

Both columns are idempotent (uses _column_exists guard) so the migration is
safe to re-run.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260226_0010"
down_revision = "20260226_0009"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if not _column_exists("orders", "fraud_flag"):
        op.add_column(
            "orders",
            sa.Column(
                "fraud_flag",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    if not _column_exists("orders", "flagged_at"):
        op.add_column(
            "orders",
            sa.Column("flagged_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("orders", "flagged_at"):
        op.drop_column("orders", "flagged_at")

    if _column_exists("orders", "fraud_flag"):
        op.drop_column("orders", "fraud_flag")
