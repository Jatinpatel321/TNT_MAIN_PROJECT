"""Create user_behaviour and user_preference_snapshots tables

Revision ID: 20260625_0028
Revises: 20260624_0027
Create Date: 2026-06-25 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = "20260625_0028"
down_revision: Union[str, None] = "20260624_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── user_behaviour: append-only interaction log ──────────────────
    op.create_table(
        "user_behaviour",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("search_query", sa.String(500), nullable=True),
        sa.Column("search_results_count", sa.Integer(), nullable=True),
        sa.Column("source_screen", sa.String(100), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("referrer", sa.String(100), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for user_behaviour
    op.create_index("ix_user_behaviour_user_event", "user_behaviour", ["user_id", "event_type"])
    op.create_index("ix_user_behaviour_user_created", "user_behaviour", ["user_id", "created_at"])

    # ── user_preference_snapshots: materialised preference view ──────
    op.create_table(
        "user_preference_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True, index=True),
        sa.Column("favourite_vendors", JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("favourite_menu_items", JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("favourite_categories", JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("preferred_timings", JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("preferred_vendor_types", JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("avg_order_frequency_days", sa.Float(), nullable=True),
        sa.Column("total_orders", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_veg_preferred", sa.Integer(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("user_preference_snapshots")
    op.drop_table("user_behaviour")
