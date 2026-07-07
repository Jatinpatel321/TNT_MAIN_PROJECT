"""create complaints table

Revision ID: 20260214_0006
Revises: 20260214_0005
Create Date: 2026-02-14 19:50:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0006"
down_revision = "20260214_0005"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    tables = _table_names()
    if "complaints" in tables:
        return

    complaint_category = sa.Enum("LATE_ORDER", "WRONG_ITEM", "QUALITY_ISSUE", "OTHER", name="complaintcategory")
    complaint_status = sa.Enum("OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED", "ESCALATED", name="complaintstatus")

    # Let op.create_table handle enum type creation to avoid duplicates


    op.create_table(
        "complaints",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("assigned_to_vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("category", complaint_category, nullable=False),
        sa.Column("status", complaint_status, nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_complaints_id", "complaints", ["id"], unique=False)


def downgrade() -> None:
    tables = _table_names()
    if "complaints" not in tables:
        return

    op.drop_index("ix_complaints_id", table_name="complaints")
    op.drop_table("complaints")

    complaint_status = sa.Enum("OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "REJECTED", "ESCALATED", name="complaintstatus")
    complaint_category = sa.Enum("LATE_ORDER", "WRONG_ITEM", "QUALITY_ISSUE", "OTHER", name="complaintcategory")

    complaint_status.drop(op.get_bind(), checkfirst=True)
    complaint_category.drop(op.get_bind(), checkfirst=True)
