"""create feedback table

Revision ID: 20260214_0005
Revises: 20260214_0004
Create Date: 2026-02-14 19:30:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0005"
down_revision = "20260214_0004"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = _table_names()
    if "feedback" in tables:
        return

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("quality_rating", sa.Integer(), nullable=False),
        sa.Column("time_rating", sa.Integer(), nullable=False),
        sa.Column("behavior_rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_feedback_id", "feedback", ["id"], unique=False)


def downgrade() -> None:
    tables = _table_names()
    if "feedback" not in tables:
        return

    op.drop_index("ix_feedback_id", table_name="feedback")
    op.drop_table("feedback")
