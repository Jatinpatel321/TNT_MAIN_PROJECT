"""User profile extensions: email, campus, residence_type, dietary_preference.

Additive, nullable columns only — no data migration required and no impact
on existing rows or queries.

Revision ID: 20260709_0045
Revises: 20260708_0044
Create Date: 2026-07-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260709_0045"
down_revision: Union[str, None] = "20260708_0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("campus", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("residence_type", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("dietary_preference", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "dietary_preference")
    op.drop_column("users", "residence_type")
    op.drop_column("users", "campus")
    op.drop_column("users", "email")
