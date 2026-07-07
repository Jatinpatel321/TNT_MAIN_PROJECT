"""Vouchers + print cost matrix: paise -> rupees Numeric(10,2), rename _paise columns

- vouchers.min_order_amount_paise  -> min_order_amount  (/100)
- vouchers.max_discount_amount_paise -> max_discount_amount (/100)
- vouchers.discount_value: /100 ONLY for FIXED vouchers (percentage vouchers keep
  their percent value), type Float -> Numeric(10,2)
- voucher_redemptions.discount_amount_paise -> discount_amount (/100)
- print_cost_matrix.price_per_page_paise -> price_per_page (/100)

Revision ID: 20260707_0043
Revises: 20260707_0042
Create Date: 2026-07-07 04:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260707_0043"
down_revision: Union[str, None] = "20260707_0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    # vouchers
    op.alter_column("vouchers", "min_order_amount_paise", new_column_name="min_order_amount")
    op.alter_column("vouchers", "max_discount_amount_paise", new_column_name="max_discount_amount")
    op.execute(sa.text(
        "ALTER TABLE vouchers ALTER COLUMN min_order_amount TYPE NUMERIC(10,2) "
        "USING ROUND(min_order_amount::numeric / 100.0, 2)"
    ))
    op.execute(sa.text(
        "ALTER TABLE vouchers ALTER COLUMN max_discount_amount TYPE NUMERIC(10,2) "
        "USING ROUND(max_discount_amount::numeric / 100.0, 2)"
    ))
    op.execute(sa.text(
        "ALTER TABLE vouchers ALTER COLUMN discount_value TYPE NUMERIC(10,2) "
        "USING CASE WHEN discount_type = 'fixed' "
        "THEN ROUND(discount_value::numeric / 100.0, 2) "
        "ELSE ROUND(discount_value::numeric, 2) END"
    ))

    # voucher_redemptions
    op.alter_column("voucher_redemptions", "discount_amount_paise", new_column_name="discount_amount")
    op.execute(sa.text(
        "ALTER TABLE voucher_redemptions ALTER COLUMN discount_amount TYPE NUMERIC(10,2) "
        "USING ROUND(discount_amount::numeric / 100.0, 2)"
    ))

    # print_cost_matrix
    op.alter_column("print_cost_matrix", "price_per_page_paise", new_column_name="price_per_page")
    op.execute(sa.text(
        "ALTER TABLE print_cost_matrix ALTER COLUMN price_per_page TYPE NUMERIC(10,2) "
        "USING ROUND(price_per_page::numeric / 100.0, 2)"
    ))


def downgrade() -> None:
    if not _is_postgres():
        return

    op.execute(sa.text(
        "ALTER TABLE print_cost_matrix ALTER COLUMN price_per_page TYPE INTEGER "
        "USING ROUND(price_per_page * 100)"
    ))
    op.alter_column("print_cost_matrix", "price_per_page", new_column_name="price_per_page_paise")

    op.execute(sa.text(
        "ALTER TABLE voucher_redemptions ALTER COLUMN discount_amount TYPE INTEGER "
        "USING ROUND(discount_amount * 100)"
    ))
    op.alter_column("voucher_redemptions", "discount_amount", new_column_name="discount_amount_paise")

    op.execute(sa.text(
        "ALTER TABLE vouchers ALTER COLUMN discount_value TYPE DOUBLE PRECISION "
        "USING CASE WHEN discount_type = 'fixed' "
        "THEN discount_value * 100 ELSE discount_value END"
    ))
    op.execute(sa.text(
        "ALTER TABLE vouchers ALTER COLUMN max_discount_amount TYPE INTEGER "
        "USING ROUND(max_discount_amount * 100)"
    ))
    op.execute(sa.text(
        "ALTER TABLE vouchers ALTER COLUMN min_order_amount TYPE INTEGER "
        "USING ROUND(min_order_amount * 100)"
    ))
    op.alter_column("vouchers", "max_discount_amount", new_column_name="max_discount_amount_paise")
    op.alter_column("vouchers", "min_order_amount", new_column_name="min_order_amount_paise")
