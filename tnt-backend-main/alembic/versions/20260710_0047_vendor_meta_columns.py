"""Add explicit vendor metadata columns (vendor_stall, vendor_location, vendor_business_name, vendor_operating_hours) and backfill from vendor_meta JSON.

Revision ID: 20260710_0047
Revises: 20260710_0046
Create Date: 2026-07-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision: str = "20260710_0047"
down_revision: Union[str, None] = "20260710_0046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("vendor_stall", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("vendor_location", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("vendor_business_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("vendor_operating_hours", JSON, nullable=True))

    # Backfill explicit columns from vendor_meta JSON
    op.execute("""
        UPDATE users
        SET
          vendor_stall = vendor_meta->>'stall',
          vendor_location = vendor_meta->>'location',
          vendor_business_name = vendor_meta->>'business_name',
          vendor_operating_hours = vendor_meta->'operating_hours'
        WHERE vendor_meta IS NOT NULL;
    """)


def downgrade() -> None:
    op.drop_column("users", "vendor_operating_hours")
    op.drop_column("users", "vendor_business_name")
    op.drop_column("users", "vendor_location")
    op.drop_column("users", "vendor_stall")
