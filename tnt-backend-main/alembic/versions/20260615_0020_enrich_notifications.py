"""enrich_notifications

Adds notification_type (enum) and reference_id (integer) columns to the
notifications table.  Both columns are nullable-friendly so existing rows
keep working: notification_type defaults to 'system' and reference_id
defaults to NULL.

For PostgreSQL (production): creates a new notificationtype enum before
adding the column.

For SQLite (tests): no-op for the enum — SQLAlchemy stores Enum columns
as plain strings in SQLite.

Revision ID: 20260615_0020
Revises: 20260615_0019
Create Date: 2026-06-15
"""
from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260615_0020"
down_revision = "20260615_0019"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

NOTIFICATION_TYPE_ENUM = "notificationtype"
NOTIFICATION_TYPE_VALUES = [
    "order_accepted",
    "order_preparing",
    "order_ready",
    "pickup_reminder",
    "delay_alert",
    "order_cancelled",
    "order_placed",
    "promo",
    "system",
]


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgres():
        op.execute(
            sa.text(
                f"CREATE TYPE {NOTIFICATION_TYPE_ENUM} AS ENUM ("
                + ", ".join(f"'{v}'" for v in NOTIFICATION_TYPE_VALUES)
                + ")"
            )
        )
        op.add_column(
            "notifications",
            sa.Column(
                "notification_type",
                sa.Enum(name=NOTIFICATION_TYPE_ENUM),
                server_default="system",
                nullable=False,
            ),
        )
    else:
        op.add_column(
            "notifications",
            sa.Column(
                "notification_type",
                sa.String(),
                server_default="system",
                nullable=False,
            ),
        )

    op.add_column(
        "notifications",
        sa.Column("reference_id", sa.Integer(), nullable=True),
    )

    logger.info("Added notification_type and reference_id to notifications table")


def downgrade() -> None:
    op.drop_column("notifications", "reference_id")
    op.drop_column("notifications", "notification_type")

    if _is_postgres():
        op.execute(sa.text(f"DROP TYPE IF EXISTS {NOTIFICATION_TYPE_ENUM}"))

    logger.info("Removed notification_type and reference_id from notifications table")
