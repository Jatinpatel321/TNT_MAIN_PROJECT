"""Convert core money columns paise(int) -> rupees Numeric(10,2)

Amounts are now stored as rupees (Decimal). Paise only survives at the Razorpay
boundary. This converts the CORE payment-path columns and divides existing data
by 100. Peripheral tables (stationery, rewards vouchers, group splits) are
handled in follow-up revisions.

Revision ID: 20260707_0041
Revises: 20260707_0040
Create Date: 2026-07-07 02:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_0041"
down_revision: Union[str, None] = "20260707_0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, column)
CORE_COLS = [
    ("menu_items", "price"),
    ("orders", "total_amount"),
    ("order_items", "price_at_time"),
    ("payments", "amount"),
    ("refund_requests", "amount"),
    ("group_cart_items", "price_at_time"),
    ("ledger", "amount"),
]


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        # SQLite (tests) builds tables from the models directly (already Numeric);
        # no in-place type/data conversion needed.
        return
    for table, col in CORE_COLS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN {col} TYPE NUMERIC(10,2) '
                f'USING ROUND({col}::numeric / 100.0, 2)'
            )
        )


def downgrade() -> None:
    if not _is_postgres():
        return
    for table, col in CORE_COLS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN {col} TYPE INTEGER '
                f'USING ROUND({col} * 100)'
            )
        )
