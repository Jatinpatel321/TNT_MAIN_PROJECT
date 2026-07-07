"""Convert peripheral money columns paise -> rupees Numeric(10,2)

Stationery (job amount, service prices) and group custom-split amounts.

Revision ID: 20260707_0042
Revises: 20260707_0041
Create Date: 2026-07-07 03:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_0042"
down_revision: Union[str, None] = "20260707_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLS = [
    ("stationery_jobs", "amount"),
    ("stationery_services", "price_per_page"),
    ("stationery_services", "price_per_unit"),
    ("group_payment_splits", "amount"),
]


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return
    for table, col in COLS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN {col} TYPE NUMERIC(10,2) '
                f'USING ROUND({col}::numeric / 100.0, 2)'
            )
        )


def downgrade() -> None:
    if not _is_postgres():
        return
    for table, col in COLS:
        op.execute(
            sa.text(
                f'ALTER TABLE {table} ALTER COLUMN {col} TYPE INTEGER '
                f'USING ROUND({col} * 100)'
            )
        )
