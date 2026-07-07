"""add_preparing_status

Adds the PREPARING canonical order status between CONFIRMED and READY.

For SQLite (tests): no-op — enum values are stored as plain strings and the
column has no DB-enforced CHECK constraint in our setup.

For PostgreSQL (production): ALTERs the enum type.  The guard makes the
migration idempotent so repeated runs are safe.

Revision ID: 20260615_0019
Revises: 20260614_0018
Create Date: 2026-06-15
"""
from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "20260615_0019"
down_revision = "20260614_0018"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

NEW_ENUM_VALUE = "preparing"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def _pg_enum_has_value(bind, type_name: str, value: str) -> bool:
    """Return True if the PostgreSQL enum type already contains *value*."""
    result = bind.execute(
        sa.text(
            "SELECT 1 FROM pg_enum e "
            "JOIN pg_type t ON t.oid = e.enumtypid "
            "WHERE t.typname = :tname AND e.enumlabel = :val"
        ),
        {"tname": type_name, "val": value},
    ).fetchone()
    return result is not None


def upgrade() -> None:
    if not _is_postgres():
        logger.info("Non-PostgreSQL dialect; skipping enum ALTER for orderstatus")
        return

    bind = op.get_bind()
    if not _pg_enum_has_value(bind, "orderstatus", NEW_ENUM_VALUE):
        op.execute(
            sa.text(f"ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS '{NEW_ENUM_VALUE}'")
        )
        logger.info("Added '%s' to orderstatus enum", NEW_ENUM_VALUE)
    else:
        logger.info("'%s' already present in orderstatus enum — skipped", NEW_ENUM_VALUE)


def downgrade() -> None:
    logger.warning(
        "Downgrade of 20260615_0019 is a no-op: "
        "PostgreSQL enum values cannot be removed without full type recreation."
    )
