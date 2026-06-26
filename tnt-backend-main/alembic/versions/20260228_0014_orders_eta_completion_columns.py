"""Add eta_minutes and actual_completion_minutes to orders

Revision ID: 20260228_0014
Revises: 20260227_0013
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260228_0014"
down_revision = "20260227_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("orders")}
    with op.batch_alter_table("orders", schema=None) as batch_op:
        if "eta_minutes" not in columns:
            batch_op.add_column(sa.Column("eta_minutes", sa.Integer(), nullable=True))
        if "actual_completion_minutes" not in columns:
            batch_op.add_column(sa.Column("actual_completion_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_column("actual_completion_minutes")
        batch_op.drop_column("eta_minutes")
