"""Add calendar_events table

Revision ID: 0026
Revises: 20260624_0025
Create Date: 2026-06-24 23:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0026"
down_revision: Union[str, None] = "20260624_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False, server_default="holiday"),
        sa.Column("affects_ordering", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_calendar_events_id"), "calendar_events", ["id"], unique=False)
    op.create_index(op.f("ix_calendar_events_event_date"), "calendar_events", ["event_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_calendar_events_event_date"), table_name="calendar_events")
    op.drop_index(op.f("ix_calendar_events_id"), table_name="calendar_events")
    op.drop_table("calendar_events")
