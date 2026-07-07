"""add orders total_amount column

Revision ID: 20260214_0003
Revises: 20260214_0002
Create Date: 2026-02-14 18:15:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0003"
down_revision = "20260214_0002"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _column_names("orders")
    if not existing:
        return

    if "total_amount" not in existing:
        with op.batch_alter_table("orders") as batch_op:
            batch_op.add_column(sa.Column("total_amount", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    existing = _column_names("orders")
    if not existing:
        return

    if "total_amount" in existing:
        with op.batch_alter_table("orders") as batch_op:
            batch_op.drop_column("total_amount")
