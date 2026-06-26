"""add rewards vouchers and offpeak policy tables

Revision ID: 20260214_0007
Revises: 20260214_0006
Create Date: 2026-02-14 21:15:00

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0007"
down_revision = "20260214_0006"
branch_labels = None
depends_on = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _add_enum_value_if_missing(enum_name: str, enum_value: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_enum WHERE enumlabel = '{enum_value}' AND enumtypid = '{enum_name}'::regtype) "
            f"THEN ALTER TYPE {enum_name} ADD VALUE '{enum_value}'; END IF; END $$;"
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rewardtype') THEN "
                "CREATE TYPE rewardtype AS ENUM ('order_completion', 'referral', 'first_order', 'loyalty_milestone', 'off_peak_bonus', 'voucher_redemption'); "
                "END IF; "
                "END $$;"
            )
        )
        op.execute(
            sa.text(
                "DO $$ BEGIN "
                "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ledgersource') THEN "
                "CREATE TYPE ledgersource AS ENUM ('payment', 'refund', 'voucher'); "
                "END IF; "
                "END $$;"
            )
        )

    _add_enum_value_if_missing("rewardtype", "OFF_PEAK_BONUS")
    _add_enum_value_if_missing("rewardtype", "VOUCHER_REDEMPTION")
    _add_enum_value_if_missing("ledgersource", "VOUCHER")

    tables = _table_names()

    voucher_discount_type = sa.Enum("PERCENTAGE", "FIXED", name="voucherdiscounttype")
    voucher_discount_type.create(op.get_bind(), checkfirst=True)

    if "vouchers" not in tables:
        op.create_table(
            "vouchers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("discount_type", voucher_discount_type, nullable=False),
            sa.Column("discount_value", sa.Float(), nullable=False),
            sa.Column("min_order_amount_paise", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_discount_amount_paise", sa.Integer(), nullable=True),
            sa.Column("usage_limit", sa.Integer(), nullable=True),
            sa.Column("times_redeemed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_vouchers_id", "vouchers", ["id"], unique=False)
        op.create_index("ix_vouchers_code", "vouchers", ["code"], unique=True)

    if "voucher_redemptions" not in tables:
        op.create_table(
            "voucher_redemptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("voucher_id", sa.Integer(), sa.ForeignKey("vouchers.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("discount_amount_paise", sa.Integer(), nullable=False),
            sa.Column("redeemed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_voucher_redemptions_id", "voucher_redemptions", ["id"], unique=False)

    if "offpeak_reward_policies" not in tables:
        op.create_table(
            "offpeak_reward_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("enabled", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("start_hour", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("end_hour", sa.Integer(), nullable=False, server_default="17"),
            sa.Column("bonus_points_per_order", sa.Float(), nullable=False, server_default="10"),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_offpeak_reward_policies_id", "offpeak_reward_policies", ["id"], unique=False)

    if "offpeak_reward_policy_audit" not in tables:
        op.create_table(
            "offpeak_reward_policy_audit",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("enabled", sa.Integer(), nullable=False),
            sa.Column("start_hour", sa.Integer(), nullable=False),
            sa.Column("end_hour", sa.Integer(), nullable=False),
            sa.Column("bonus_points_per_order", sa.Float(), nullable=False),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("changed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_offpeak_reward_policy_audit_id", "offpeak_reward_policy_audit", ["id"], unique=False)


def downgrade() -> None:
    tables = _table_names()

    if "offpeak_reward_policy_audit" in tables:
        op.drop_index("ix_offpeak_reward_policy_audit_id", table_name="offpeak_reward_policy_audit")
        op.drop_table("offpeak_reward_policy_audit")

    if "offpeak_reward_policies" in tables:
        op.drop_index("ix_offpeak_reward_policies_id", table_name="offpeak_reward_policies")
        op.drop_table("offpeak_reward_policies")

    if "voucher_redemptions" in tables:
        op.drop_index("ix_voucher_redemptions_id", table_name="voucher_redemptions")
        op.drop_table("voucher_redemptions")

    if "vouchers" in tables:
        op.drop_index("ix_vouchers_code", table_name="vouchers")
        op.drop_index("ix_vouchers_id", table_name="vouchers")
        op.drop_table("vouchers")

    voucher_discount_type = sa.Enum("PERCENTAGE", "FIXED", name="voucherdiscounttype")
    voucher_discount_type.drop(op.get_bind(), checkfirst=True)
