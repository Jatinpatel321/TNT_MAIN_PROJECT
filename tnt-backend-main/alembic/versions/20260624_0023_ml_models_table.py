from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260624_0023"
down_revision = "20260624_0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ml_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("trained_at", sa.DateTime(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("hyperparams_json", sa.Text(), nullable=True),
        sa.Column("features_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_ml_models_model_name", "ml_models", ["model_name"], unique=False)


def downgrade():
    op.drop_index("ix_ml_models_model_name", table_name="ml_models")
    op.drop_table("ml_models")

