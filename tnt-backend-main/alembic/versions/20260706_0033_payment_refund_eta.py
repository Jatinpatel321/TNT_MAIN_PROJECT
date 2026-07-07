"""Add refund ETA columns to payments

Revision ID: 20260706_0033
Revises: 20260706_0032
Create Date: 2026-07-06 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260706_0033"
down_revision: Union[str, None] = "20260706_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("refund_status", sa.String(), nullable=True))
    op.add_column("payments", sa.Column("estimated_refund_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "estimated_refund_at")
    op.drop_column("payments", "refund_status")
