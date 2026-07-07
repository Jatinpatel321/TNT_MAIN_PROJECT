"""add users vendor_type column

Revision ID: 20260214_0004
Revises: 20260214_0003
Create Date: 2026-02-14 19:10:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0004"
down_revision = "20260214_0003"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _column_names("users")
    if not existing:
        return

    if "vendor_type" not in existing:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(sa.Column("vendor_type", sa.String(), nullable=False, server_default="food"))


def downgrade() -> None:
    existing = _column_names("users")
    if not existing:
        return

    if "vendor_type" in existing:
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("vendor_type")
