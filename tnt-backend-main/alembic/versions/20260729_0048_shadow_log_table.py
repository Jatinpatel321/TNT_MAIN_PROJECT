"""Create shadow_log table

Revision ID: 20260729_0048
Revises: 20260710_0047
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_0048"
down_revision: Union[str, None] = "20260710_0047"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shadow_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("predicted_model", sa.Float(), nullable=True),
        sa.Column("predicted_heuristic", sa.Float(), nullable=True),
        sa.Column("actual_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_log_id", "shadow_log", ["id"])
    op.create_index("ix_shadow_log_model_type", "shadow_log", ["model_type"])
    op.create_index("ix_shadow_log_entity_id", "shadow_log", ["entity_id"])
    op.create_index("ix_shadow_log_created_at", "shadow_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_shadow_log_created_at", table_name="shadow_log")
    op.drop_index("ix_shadow_log_entity_id", table_name="shadow_log")
    op.drop_index("ix_shadow_log_model_type", table_name="shadow_log")
    op.drop_index("ix_shadow_log_id", table_name="shadow_log")
    op.drop_table("shadow_log")
