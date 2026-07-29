"""Create ml_retraining_logs table

Revision ID: 20260729_0050
Revises: 20260729_0049
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260729_0050"
down_revision: Union[str, None] = "20260729_0049"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ml_retraining_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_type", sa.String(length=100), nullable=False),
        sa.Column("triggered_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("version_id", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ml_retraining_logs_id", "ml_retraining_logs", ["id"])
    op.create_index("ix_ml_retraining_logs_model_type", "ml_retraining_logs", ["model_type"])
    op.create_index("ix_ml_retraining_logs_created_at", "ml_retraining_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ml_retraining_logs_created_at", table_name="ml_retraining_logs")
    op.drop_index("ix_ml_retraining_logs_model_type", table_name="ml_retraining_logs")
    op.drop_index("ix_ml_retraining_logs_id", table_name="ml_retraining_logs")
    op.drop_table("ml_retraining_logs")
