"""Finance admin: ledger adjustments + refund requests

Revision ID: 20260706_0036
Revises: 20260706_0035
Create Date: 2026-07-06 04:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260706_0036"
down_revision: Union[str, None] = "20260706_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REFUND_REQ_ENUM = "refundrequeststatus"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # 1. Manual ledger adjustments — relax order_id, add attribution, new source value.
    op.alter_column("ledger", "order_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("ledger", sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))

    if _is_postgres():
        # PostgreSQL 12+ allows ADD VALUE inside a transaction (value not used here).
        op.execute(sa.text("ALTER TYPE ledgersource ADD VALUE IF NOT EXISTS 'adjustment'"))

    # 2. Refund requests (admin approval workflow).
    # Drop any stray objects a stray create_all may have left, then create cleanly.
    if _is_postgres():
        op.execute(sa.text("DROP TABLE IF EXISTS refund_requests CASCADE"))
        op.execute(sa.text(f"DROP TYPE IF EXISTS {REFUND_REQ_ENUM}"))
        status_type = sa.Enum("pending", "approved", "rejected", name=REFUND_REQ_ENUM)
    else:
        status_type = sa.String()

    op.create_table(
        "refund_requests",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, index=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("status", status_type, server_default="pending", nullable=False),
        sa.Column("decision_note", sa.String(), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("refund_requests")
    if _is_postgres():
        op.execute(sa.text(f"DROP TYPE IF EXISTS {REFUND_REQ_ENUM}"))
    op.drop_column("ledger", "created_by")
    op.alter_column("ledger", "order_id", existing_type=sa.Integer(), nullable=False)
    # Note: Postgres cannot easily drop a single enum value; 'adjustment' is left in place.
