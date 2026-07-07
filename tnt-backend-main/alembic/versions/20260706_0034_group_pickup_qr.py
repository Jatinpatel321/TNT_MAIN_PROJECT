"""Add combined-pickup qr_code column to groups

Revision ID: 20260706_0034
Revises: 20260706_0033
Create Date: 2026-07-06 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260706_0034"
down_revision: Union[str, None] = "20260706_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("groups", sa.Column("qr_code", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_groups_qr_code", "groups", ["qr_code"])


def downgrade() -> None:
    op.drop_constraint("uq_groups_qr_code", "groups", type_="unique")
    op.drop_column("groups", "qr_code")
