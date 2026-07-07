"""Add print option columns to stationery_jobs

Revision ID: 20260706_0032
Revises: 20260706_0031
Create Date: 2026-07-06 00:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260706_0032"
down_revision: Union[str, None] = "20260706_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRINT_TYPE_ENUM = "printtype"
PAPER_SIZE_ENUM = "papersize"


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if _is_postgres():
        op.execute(sa.text(f"CREATE TYPE {PRINT_TYPE_ENUM} AS ENUM ('bw', 'color')"))
        op.execute(sa.text(f"CREATE TYPE {PAPER_SIZE_ENUM} AS ENUM ('A4', 'A3')"))
        print_type_col = sa.Column(
            "print_type", sa.Enum(name=PRINT_TYPE_ENUM), server_default="bw", nullable=False
        )
        paper_size_col = sa.Column(
            "paper_size", sa.Enum(name=PAPER_SIZE_ENUM), server_default="A4", nullable=False
        )
    else:
        print_type_col = sa.Column("print_type", sa.String(), server_default="bw", nullable=False)
        paper_size_col = sa.Column("paper_size", sa.String(), server_default="A4", nullable=False)

    op.add_column("stationery_jobs", print_type_col)
    op.add_column("stationery_jobs", paper_size_col)
    op.add_column(
        "stationery_jobs",
        sa.Column("duplex", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("stationery_jobs", sa.Column("page_range", sa.String(50), nullable=True))
    op.add_column("stationery_jobs", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("stationery_jobs", "notes")
    op.drop_column("stationery_jobs", "page_range")
    op.drop_column("stationery_jobs", "duplex")
    op.drop_column("stationery_jobs", "paper_size")
    op.drop_column("stationery_jobs", "print_type")

    if _is_postgres():
        op.execute(sa.text(f"DROP TYPE IF EXISTS {PAPER_SIZE_ENUM}"))
        op.execute(sa.text(f"DROP TYPE IF EXISTS {PRINT_TYPE_ENUM}"))
