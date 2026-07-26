"""Add composite index idx_orders_vendor_status on orders(vendor_id, status)

Revision ID: 20260710_0046
Revises: 20260709_0045
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260710_0046"
down_revision: Union[str, None] = "20260709_0045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_orders_vendor_status", "orders", ["vendor_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_orders_vendor_status", table_name="orders")
