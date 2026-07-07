"""Add device_token and push_enabled to users, create system_config table

Revision ID: 20260624_0022
Revises: 20260617_0021
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260624_0022"
down_revision = "20260617_0021"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "device_token" not in columns:
        op.add_column("users", sa.Column("device_token", sa.String(512), nullable=True))
    if "push_enabled" not in columns:
        op.add_column("users", sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="1"))

    tables = inspector.get_table_names()
    if "system_config" not in tables:
        op.create_table(
            "system_config",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("value", sa.String(500), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )
        op.create_index(op.f("ix_system_config_key"), "system_config", ["key"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_system_config_key"), table_name="system_config")
    op.drop_table("system_config")
    op.drop_column("users", "push_enabled")
    op.drop_column("users", "device_token")