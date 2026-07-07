"""add stationery jobs payment columns

Revision ID: 20260214_0002
Revises: 20260214_0001
Create Date: 2026-02-14 00:05:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0002"
down_revision = "20260214_0001"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _column_names("stationery_jobs")
    if not existing:
        return

    with op.batch_alter_table("stationery_jobs") as batch_op:
        if "amount" not in existing:
            batch_op.add_column(sa.Column("amount", sa.Integer(), nullable=False, server_default="0"))
        if "is_paid" not in existing:
            batch_op.add_column(sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()))
        if "razorpay_order_id" not in existing:
            batch_op.add_column(sa.Column("razorpay_order_id", sa.String(), nullable=True))
        if "razorpay_payment_id" not in existing:
            batch_op.add_column(sa.Column("razorpay_payment_id", sa.String(), nullable=True))
        if "razorpay_signature" not in existing:
            batch_op.add_column(sa.Column("razorpay_signature", sa.String(), nullable=True))


def downgrade() -> None:
    existing = _column_names("stationery_jobs")
    if not existing:
        return

    with op.batch_alter_table("stationery_jobs") as batch_op:
        if "razorpay_signature" in existing:
            batch_op.drop_column("razorpay_signature")
        if "razorpay_payment_id" in existing:
            batch_op.drop_column("razorpay_payment_id")
        if "razorpay_order_id" in existing:
            batch_op.drop_column("razorpay_order_id")
        if "is_paid" in existing:
            batch_op.drop_column("is_paid")
        if "amount" in existing:
            batch_op.drop_column("amount")
