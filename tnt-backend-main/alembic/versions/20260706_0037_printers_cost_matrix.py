"""Printer monitoring + print cost matrix

Revision ID: 20260706_0037
Revises: 20260706_0036
Create Date: 2026-07-06 05:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260706_0037"
down_revision: Union[str, None] = "20260706_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRINTER_STATUS_ENUM = "printerstatus"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # Drop stray objects a startup create_all may have made, then create cleanly.
    if _is_postgres():
        op.execute(sa.text("DROP TABLE IF EXISTS printers CASCADE"))
        op.execute(sa.text("DROP TABLE IF EXISTS print_cost_matrix CASCADE"))
        op.execute(sa.text(f"DROP TYPE IF EXISTS {PRINTER_STATUS_ENUM}"))
        status_type = sa.Enum("online", "offline", "maintenance", "error", name=PRINTER_STATUS_ENUM)
    else:
        status_type = sa.String()

    op.create_table(
        "printers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("status", status_type, server_default="online", nullable=False),
        sa.Column("queue_depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ink_level_pct", sa.Integer(), server_default="100", nullable=False),
        sa.Column("paper_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("capacity_pages_per_hour", sa.Integer(), server_default="600", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "print_cost_matrix",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("print_type", sa.String(length=20), nullable=False),
        sa.Column("paper_size", sa.String(length=20), nullable=False),
        sa.Column("duplex", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("price_per_page_paise", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("vendor_id", "print_type", "paper_size", "duplex", name="uq_print_cost_combo"),
    )


def downgrade() -> None:
    op.drop_table("print_cost_matrix")
    op.drop_table("printers")
    if _is_postgres():
        op.execute(sa.text(f"DROP TYPE IF EXISTS {PRINTER_STATUS_ENUM}"))
