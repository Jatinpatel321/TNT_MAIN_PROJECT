"""Add admin-managed vendor_meta JSON column to users

Revision ID: 20260706_0035
Revises: 20260706_0034
Create Date: 2026-07-06 03:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260706_0035"
down_revision: Union[str, None] = "20260706_0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("vendor_meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "vendor_meta")
