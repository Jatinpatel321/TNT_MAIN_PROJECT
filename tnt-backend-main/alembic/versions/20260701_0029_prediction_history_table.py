"""Create prediction_history table

Revision ID: 20260701_0029
Revises: 20260625_0028
Create Date: 2026-07-01 10:00:00.000000

Stores prediction history for ML learning and accuracy tracking.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = "20260701_0029"
down_revision: Union[str, None] = "20260625_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prediction_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("prediction_type", sa.String(50), nullable=False, index=True),
        sa.Column("predicted_vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("predicted_menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=True),
        sa.Column("predicted_hour", sa.Integer(), nullable=True),
        sa.Column("predicted_day_of_week", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("prediction_data", JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("actual_vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actual_menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=True),
        sa.Column("actual_order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
        sa.Column("actual_hour", sa.Integer(), nullable=True),
        sa.Column("was_correct", sa.Integer(), nullable=True),
        sa.Column("predicted_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()"), index=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_prediction_user_type", "prediction_history", ["user_id", "prediction_type"])
    op.create_index("ix_prediction_user_created", "prediction_history", ["user_id", "predicted_at"])


def downgrade() -> None:
    op.drop_table("prediction_history")
