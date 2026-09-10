"""Add payment tracking columns to group_payment_splits table

Revision ID: 20260729_0051
Revises: 20260729_0050
Create Date: 2026-09-10
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "20260729_0051"
down_revision: Union[str, None] = "20260729_0050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("group_payment_splits", sa.Column("amount_paid", sa.Numeric(10, 2), nullable=True, server_default="0.00"))
    op.add_column("group_payment_splits", sa.Column("payment_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("group_payment_splits", sa.Column("payment_method", sa.String(length=30), nullable=True))
    op.add_column("group_payment_splits", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("group_payment_splits", sa.Column("razorpay_order_id", sa.String(length=100), nullable=True))
    op.add_column("group_payment_splits", sa.Column("razorpay_payment_id", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("group_payment_splits", "razorpay_payment_id")
    op.drop_column("group_payment_splits", "razorpay_order_id")
    op.drop_column("group_payment_splits", "paid_at")
    op.drop_column("group_payment_splits", "payment_method")
    op.drop_column("group_payment_splits", "payment_status")
    op.drop_column("group_payment_splits", "amount_paid")
