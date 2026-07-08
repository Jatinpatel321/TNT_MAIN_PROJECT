"""Vendor wallet/settlement/offer/reward money columns: Float -> Numeric(10,2)

Precision-only fix, NOT a unit/scale change: these columns were already
correctly rupee-scaled Floats, just architecturally risky (binary rounding
drift) for money that gets repeatedly summed/adjusted over time. No data
transform needed beyond the type cast itself.

- vendor_wallets: total_earned, total_pending, total_settled, total_refunded, balance
- vendor_transactions: amount, fee, net_amount
- vendor_settlements: total_amount, total_fees, net_amount, online_payments, refunds
- discount_campaigns: discount_value, min_order_amount, max_discount_amount, combo_price
- vendor_offers: discount_value, min_order_amount, max_discount_amount
- redemption_rules: max_discount_amount

Revision ID: 20260708_0044
Revises: 20260707_0043
Create Date: 2026-07-08 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260708_0044"
down_revision: Union[str, None] = "20260707_0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = [
    ("vendor_wallets", "total_earned"),
    ("vendor_wallets", "total_pending"),
    ("vendor_wallets", "total_settled"),
    ("vendor_wallets", "total_refunded"),
    ("vendor_wallets", "balance"),
    ("vendor_transactions", "amount"),
    ("vendor_transactions", "fee"),
    ("vendor_transactions", "net_amount"),
    ("vendor_settlements", "total_amount"),
    ("vendor_settlements", "total_fees"),
    ("vendor_settlements", "net_amount"),
    ("vendor_settlements", "online_payments"),
    ("vendor_settlements", "refunds"),
    ("discount_campaigns", "discount_value"),
    ("discount_campaigns", "min_order_amount"),
    ("discount_campaigns", "max_discount_amount"),
    ("discount_campaigns", "combo_price"),
    ("vendor_offers", "discount_value"),
    ("vendor_offers", "min_order_amount"),
    ("vendor_offers", "max_discount_amount"),
    ("redemption_rules", "max_discount_amount"),
]


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    for table, column in _COLUMNS:
        op.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE NUMERIC(10,2) "
            f"USING ROUND({column}::numeric, 2)"
        ))


def downgrade() -> None:
    if not _is_postgres():
        return

    for table, column in reversed(_COLUMNS):
        op.execute(sa.text(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE DOUBLE PRECISION "
            f"USING {column}::double precision"
        ))
