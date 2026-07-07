"""users_created_at

Adds a ``created_at`` timestamp column to the ``users`` table so that the
admin analytics endpoint can report new-user signups by day without
relying on the ``hasattr`` guard that previously short-circuited the query.

The column is nullable so that existing rows are not broken; the application
default (``utcnow_naive``) ensures all new rows get a timestamp automatically.

Revision ID: 20260227_0013
Revises: 20260226_0012
Create Date: 2026-02-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260227_0013"
down_revision = "20260226_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "created_at" not in columns:
        with op.batch_alter_table("users") as batch_op:
            batch_op.add_column(
                sa.Column("created_at", sa.DateTime(), nullable=True)
            )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("created_at")
