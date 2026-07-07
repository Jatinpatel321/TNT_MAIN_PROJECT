"""Add fraud_reason text column to orders table

Revision ID: 0027
Revises: 20260624_0026
Create Date: 2026-06-24 23:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0027"
down_revision: Union[str, None] = "20260624_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("fraud_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "fraud_reason")
