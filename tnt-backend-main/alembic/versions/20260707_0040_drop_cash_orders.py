"""Drop cash_orders from vendor_settlements (online-prepaid only; no cash feature)

Revision ID: 20260707_0040
Revises: 20260707_0039
Create Date: 2026-07-07 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_0040"
down_revision: Union[str, None] = "20260707_0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if _has_column("vendor_settlements", "cash_orders"):
        op.drop_column("vendor_settlements", "cash_orders")


def downgrade() -> None:
    if not _has_column("vendor_settlements", "cash_orders"):
        op.add_column(
            "vendor_settlements",
            sa.Column("cash_orders", sa.Float(), nullable=True, server_default="0"),
        )
