"""orders_state_machine_enum

Adds the three canonical PROMPT-11 order states:
  placed, ready, picked

For SQLite (tests): no-op — enum values are stored as plain strings and the
column has no DB-enforced CHECK constraint in our setup.

For PostgreSQL (production): ALTERs the enum type.  The guard makes the
migration idempotent so repeated runs are safe.

Revision ID: 20260226_0011
Revises: 20260226_0010
Create Date: 2026-02-26
"""
from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers
revision = "20260226_0011"
down_revision = "20260226_0010"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

NEW_ENUM_VALUES = ("placed", "ready", "picked")


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
        # SQLite / other dialects: enum is just a VARCHAR — nothing to do.
        logger.info("Non-PostgreSQL dialect; skipping enum ALTER for orderstatus")
        return

    bind = op.get_bind()
    # Check if orderstatus type exists, if not create it
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'orderstatus'")
    ).fetchone()
    if result is None:
        bind.execute(
            sa.text(
                "CREATE TYPE orderstatus AS ENUM "
                "('placed', 'confirmed', 'preparing', 'ready', 'picked', 'cancelled', "
                "'pending', 'ready_for_pickup', 'completed')"
            )
        )
        logger.info("Created orderstatus enum type")

    for value in NEW_ENUM_VALUES:
        if not _pg_enum_has_value(bind, "orderstatus", value):
            op.execute(
                sa.text(f"ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS '{value}'")
            )
            logger.info("Added '%s' to orderstatus enum", value)
        else:
            logger.info("'%s' already present in orderstatus enum — skipped", value)


def downgrade() -> None:
    # PostgreSQL does not support DROP VALUE from an enum without recreating the
    # type, which would require migrating the column too.  Downgrade is
    # intentionally left as a no-op (the new values simply become unused).
    logger.warning(
        "Downgrade of 20260226_0011 is a no-op: "
        "PostgreSQL enum values cannot be removed without full type recreation."
    )
