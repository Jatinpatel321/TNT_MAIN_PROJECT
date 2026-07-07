"""add stationery_job_id to payments; make order_id nullable

Revision ID: 20260226_0009
Revises: 20260226_0008
Create Date: 2026-02-26 00:00:00

Extends the payments table so that stationery jobs are fully traceable
through the central Payment audit trail.

Changes
-------
* payments.order_id   — relaxed from NOT NULL → nullable (stationery
  payments have no campus food order).
* payments.stationery_job_id — new nullable FK → stationery_jobs.id,
  with an index for fast look-ups.

Invariant enforced at the application layer: exactly one of
(order_id, stationery_job_id) is non-NULL for every payment row.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260226_0009"
down_revision = "20260226_0008"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Make order_id nullable.
    #    SQLite does not support ALTER COLUMN; we rely on the fact that SQLite
    #    treats all columns as nullable unless an explicit NOT NULL constraint
    #    is defined.  The column was created with nullable=False in the baseline
    #    migration, so we need to recreate the table for SQLite; for PostgreSQL
    #    we use ALTER TABLE … ALTER COLUMN.
    if bind.dialect.name == "sqlite":
        # SQLite: batch mode recreates the table transparently.
        with op.batch_alter_table("payments") as batch_op:
            batch_op.alter_column("order_id", existing_type=sa.Integer(), nullable=True)
    else:
        op.alter_column("payments", "order_id", existing_type=sa.Integer(), nullable=True)

    # 2. Add stationery_job_id column (idempotent).
    if not _column_exists("payments", "stationery_job_id"):
        op.add_column(
            "payments",
            sa.Column(
                "stationery_job_id",
                sa.Integer(),
                sa.ForeignKey("stationery_jobs.id"),
                nullable=True,
            ),
        )

    # 3. Add index on stationery_job_id for fast look-ups.
    if bind.dialect.name == "sqlite":
        bind.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_payments_stationery_job_id "
                "ON payments (stationery_job_id)"
            )
        )
    else:
        op.create_index(
            "ix_payments_stationery_job_id",
            "payments",
            ["stationery_job_id"],
            unique=False,
            if_not_exists=True,
        )


def downgrade() -> None:
    bind = op.get_bind()

    # Drop stationery_job_id index.
    if bind.dialect.name == "sqlite":
        bind.execute(
            sa.text("DROP INDEX IF EXISTS ix_payments_stationery_job_id")
        )
    else:
        try:
            op.drop_index("ix_payments_stationery_job_id", table_name="payments")
        except Exception:
            pass

    # Drop stationery_job_id column.
    if _column_exists("payments", "stationery_job_id"):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("payments") as batch_op:
                batch_op.drop_column("stationery_job_id")
        else:
            op.drop_column("payments", "stationery_job_id")

    # Restore order_id NOT NULL constraint.
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("payments") as batch_op:
            batch_op.alter_column("order_id", existing_type=sa.Integer(), nullable=False)
    else:
        op.alter_column("payments", "order_id", existing_type=sa.Integer(), nullable=False)
