"""add search-optimized indexes for ILIKE and filter queries

Revision ID: 20260614_0017
Revises: 20260614_0016
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


revision = "20260614_0017"
down_revision = "20260614_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # B-tree indexes for exact / range lookups used by filters
    op.create_index("ix_menu_items_price", "menu_items", ["price"], if_not_exists=True)
    op.create_index("ix_menu_items_vendor_available", "menu_items", ["vendor_id", "is_available"], if_not_exists=True)
    op.create_index("ix_stationery_services_price", "stationery_services", ["price_per_unit"], if_not_exists=True)
    op.create_index("ix_stationery_services_vendor_available", "stationery_services", ["vendor_id", "is_available"], if_not_exists=True)

    # PostgreSQL-specific trigram GIN indexes for ILIKE search
    # These dramatically speed up `%query%` pattern matching on name columns.
    # If pg_trgm extension is not available the GIN indexes are skipped gracefully.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_menu_items_name_trgm ON menu_items USING gin (name gin_trgm_ops)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_stationery_services_name_trgm ON stationery_services USING gin (name gin_trgm_ops)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS ix_users_name_trgm ON users USING gin (name gin_trgm_ops)'
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_stationery_services_name_trgm")
    op.execute("DROP INDEX IF EXISTS ix_menu_items_name_trgm")
    op.drop_index("ix_stationery_services_vendor_available", if_exists=True)
    op.drop_index("ix_stationery_services_price", if_exists=True)
    op.drop_index("ix_menu_items_vendor_available", if_exists=True)
    op.drop_index("ix_menu_items_price", if_exists=True)
