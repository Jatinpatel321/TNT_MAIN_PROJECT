"""Create drift_reports table

Revision ID: 20260729_0049
Revises: 20260729_0048
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = "20260729_0049"
down_revision: Union[str, None] = "20260729_0048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drift_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_type", sa.String(length=100), nullable=False),
        sa.Column("check_type", sa.String(length=50), nullable=False),
        sa.Column("has_drift", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("report_data", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drift_reports_id", "drift_reports", ["id"])
    op.create_index("ix_drift_reports_model_type", "drift_reports", ["model_type"])
    op.create_index("ix_drift_reports_check_type", "drift_reports", ["check_type"])
    op.create_index("ix_drift_reports_created_at", "drift_reports", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_drift_reports_created_at", table_name="drift_reports")
    op.drop_index("ix_drift_reports_check_type", table_name="drift_reports")
    op.drop_index("ix_drift_reports_model_type", table_name="drift_reports")
    op.drop_index("ix_drift_reports_id", table_name="drift_reports")
    op.drop_table("drift_reports")
