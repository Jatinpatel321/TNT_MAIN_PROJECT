"""add full_name, department, semester, profile_image to users

Revision ID: 20260614_0016
Revises: 20260305_0015
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260614_0016"
down_revision = "20260305_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "full_name" not in columns:
        op.add_column("users", sa.Column("full_name", sa.String(), nullable=True))
    if "department" not in columns:
        op.add_column("users", sa.Column("department", sa.String(), nullable=True))
    if "semester" not in columns:
        op.add_column("users", sa.Column("semester", sa.Integer(), nullable=True))
    if "profile_image" not in columns:
        op.add_column("users", sa.Column("profile_image", sa.String(), nullable=True))

    # Backfill full_name from name where full_name is null
    op.execute("UPDATE users SET full_name = name WHERE full_name IS NULL AND name IS NOT NULL")


def downgrade() -> None:
    op.drop_column("users", "profile_image")
    op.drop_column("users", "semester")
    op.drop_column("users", "department")
    op.drop_column("users", "full_name")
