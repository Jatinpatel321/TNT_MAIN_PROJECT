"""Add overall_rating to feedback and create vendor_reviews table.

Revision ID: 20260617_0021
Revises: 20260615_0020
"""
from alembic import op
import sqlalchemy as sa

revision = "20260617_0021"
down_revision = "20260615_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("feedback")}
    if "overall_rating" not in columns:
        op.add_column("feedback", sa.Column("overall_rating", sa.Integer(), nullable=True))

    tables = inspector.get_table_names()
    if "vendor_reviews" not in tables:
        op.create_table(
            "vendor_reviews",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(200), nullable=True),
            sa.Column("review_text", sa.Text(), nullable=True),
            sa.Column("is_anonymous", sa.Boolean(), default=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("vendor_reviews")
    op.drop_column("feedback", "overall_rating")
