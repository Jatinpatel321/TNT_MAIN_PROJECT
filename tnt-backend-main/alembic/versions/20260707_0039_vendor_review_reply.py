"""Add vendor reply columns to vendor_reviews

Revision ID: 20260707_0039
Revises: 20260706_0038
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_0039"
down_revision: Union[str, None] = "20260706_0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_column("vendor_reviews", "vendor_reply"):
        op.add_column("vendor_reviews", sa.Column("vendor_reply", sa.Text(), nullable=True))
    if not _has_column("vendor_reviews", "vendor_reply_at"):
        op.add_column("vendor_reviews", sa.Column("vendor_reply_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if _has_column("vendor_reviews", "vendor_reply_at"):
        op.drop_column("vendor_reviews", "vendor_reply_at")
    if _has_column("vendor_reviews", "vendor_reply"):
        op.drop_column("vendor_reviews", "vendor_reply")
