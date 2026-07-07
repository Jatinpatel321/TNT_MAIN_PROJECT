"""Create backup_records table

Revision ID: 20260626_0030
Revises: 20260701_0029
Create Date: 2026-06-26 05:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260626_0030"
down_revision: Union[str, None] = "20260701_0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types via raw SQL with duplicate-safe DO blocks
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE backup_type_enum AS ENUM ('manual', 'daily', 'weekly');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE backup_status_enum AS ENUM ('success', 'failed', 'in_progress', 'deleted');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Use String columns referencing the already-created enums (avoid SA auto-create)
    op.create_table(
        "backup_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("backup_type", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("database_name", sa.String(128), nullable=True),
        sa.Column("tables_count", sa.Integer(), nullable=True),
        sa.Column("rows_exported", sa.BigInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add check constraints for enum values
    op.execute(
        "ALTER TABLE backup_records ADD CONSTRAINT chk_backup_type "
        "CHECK (backup_type IN ('manual', 'daily', 'weekly'))"
    )
    op.execute(
        "ALTER TABLE backup_records ADD CONSTRAINT chk_backup_status "
        "CHECK (status IN ('success', 'failed', 'in_progress', 'deleted'))"
    )

    op.create_index("ix_backup_records_id", "backup_records", ["id"])
    op.create_index("ix_backup_records_filename", "backup_records", ["filename"], unique=True)
    op.create_index("ix_backup_records_created_at", "backup_records", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_backup_records_created_at", table_name="backup_records")
    op.drop_index("ix_backup_records_filename", table_name="backup_records")
    op.drop_index("ix_backup_records_id", table_name="backup_records")
    op.drop_table("backup_records")
    op.execute("DROP TYPE IF EXISTS backup_status_enum")
    op.execute("DROP TYPE IF EXISTS backup_type_enum")
