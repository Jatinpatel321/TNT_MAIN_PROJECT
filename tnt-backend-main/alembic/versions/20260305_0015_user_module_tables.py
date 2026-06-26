"""add user module supporting tables

Revision ID: 20260305_0015
Revises: 20260228_0014
Create Date: 2026-03-05
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260305_0015"
down_revision = "20260228_0014"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _ensure_enums():
    bind = op.get_bind()
    enums = [
        sa.Enum("student", "faculty", name="userrole"),
        sa.Enum("OPEN", "CLOSED", "FULL", name="slotstatus"),
        sa.Enum(
            "PENDING",
            "CONFIRMED",
            "READY",
            "COMPLETED",
            "CANCELLED",
            "FAILED",
            name="orderstatus",
        ),
        sa.Enum("INITIATED", "SUCCESS", "FAILED", "REFUNDED", name="paymentstatus"),
        sa.Enum("OPEN", "LOCKED", "ORDERED", name="groupcartstatus"),
        sa.Enum("OWNER", "MEMBER", name="groupcartrole"),
    ]
    for enum in enums:
        enum.create(bind, checkfirst=True)


def upgrade() -> None:
    existing = _tables()
    _ensure_enums()

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("phone", sa.String(length=32), nullable=False, unique=True),
            sa.Column("university_id", sa.String(length=64), nullable=True),
            sa.Column("role", sa.Enum(name="userrole", create_type=False), nullable=False, server_default="student"),
            sa.Column("department", sa.String(length=255), nullable=True),
            sa.Column("preferred_vendors", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if "vendors" not in existing:
        op.create_table(
            "vendors",
            sa.Column("vendor_id", sa.Integer(), primary_key=True),
            sa.Column("vendor_name", sa.String(length=255), nullable=False),
            sa.Column("vendor_type", sa.String(length=64), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("logo_url", sa.String(length=512), nullable=True),
            sa.Column("rating", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if "menu_items" not in existing:
        op.create_table(
            "menu_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.vendor_id"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price_paise", sa.Integer(), nullable=False),
            sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("image_url", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_menu_items_vendor_id", "menu_items", ["vendor_id"])

    if "slots" not in existing:
        op.create_table(
            "slots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.vendor_id"), nullable=False),
            sa.Column("start_time", sa.DateTime(), nullable=False),
            sa.Column("end_time", sa.DateTime(), nullable=False),
            sa.Column("capacity", sa.Integer(), nullable=False),
            sa.Column("current_orders", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.Enum(name="slotstatus", create_type=False), nullable=False, server_default="OPEN"),
        )
        op.create_index("ix_slots_vendor_id", "slots", ["vendor_id"])
        op.create_index("ix_slots_time", "slots", ["vendor_id", "start_time", "end_time"])

    if "orders" not in existing:
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.vendor_id"), nullable=False),
            sa.Column("slot_id", sa.Integer(), sa.ForeignKey("slots.id"), nullable=True),
            sa.Column("status", sa.Enum(name="orderstatus", create_type=False), nullable=False, server_default="PENDING"),
            sa.Column("total_price_paise", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pickup_code", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_orders_user_id", "orders", ["user_id"])
        op.create_index("ix_orders_vendor_id", "orders", ["vendor_id"])

    if "order_items" not in existing:
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("unit_price_paise", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_price_paise", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    if "payments" not in existing:
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("provider", sa.String(length=64), nullable=True),
            sa.Column("status", sa.Enum(name="paymentstatus", create_type=False), nullable=False, server_default="INITIATED"),
            sa.Column("amount_paise", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payment_reference", sa.String(length=128), nullable=True),
            sa.Column("idempotency_key", sa.String(length=128), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_payments_order_id", "payments", ["order_id"])

    if "notifications" not in existing:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    if "favorites" not in existing:
        op.create_table(
            "favorites",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.vendor_id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("user_id", "vendor_id", name="uq_favorites_user_vendor"),
        )
        op.create_index("ix_favorites_user_id", "favorites", ["user_id"])

    # Legacy group_carts and group_cart_members are not used by the app models, so we skip creating them
    # to avoid duplicate enum errors and keep the DB schema clean.
    # if "group_carts" not in existing:
    #     op.create_table(
    #         "group_carts",
    #         sa.Column("id", sa.Integer(), primary_key=True),
    #         sa.Column("creator_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
    #         sa.Column("slot_id", sa.Integer(), sa.ForeignKey("slots.id"), nullable=True),
    #         sa.Column("status", sa.Enum(name="groupcartstatus", create_type=False), nullable=False, server_default="OPEN"),
    #         sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    #     )
    #     op.create_index("ix_group_carts_creator_id", "group_carts", ["creator_id"])
    #
    # if "group_cart_members" not in existing:
    #     op.create_table(
    #         "group_cart_members",
    #         sa.Column("id", sa.Integer(), primary_key=True),
    #         sa.Column("group_cart_id", sa.Integer(), sa.ForeignKey("group_carts.id"), nullable=False),
    #         sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
    #         sa.Column("role", sa.String(50), nullable=False, server_default="MEMBER"),
    #         sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    #         sa.UniqueConstraint("group_cart_id", "user_id", name="uq_group_cart_member"),
    #     )
    #     op.create_index("ix_group_cart_members_group_cart_id", "group_cart_members", ["group_cart_id"])

    if "group_cart_items" not in existing:
        op.create_table(
            "group_cart_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("price_at_time", sa.Float(), nullable=False),
            sa.Column("added_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_group_cart_items_group_id", "group_cart_items", ["group_id"])

    if "feedback" not in existing:
        op.create_table(
            "feedback",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.vendor_id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("rating_quality", sa.Integer(), nullable=True),
            sa.Column("rating_time", sa.Integer(), nullable=True),
            sa.Column("rating_behavior", sa.Integer(), nullable=True),
            sa.Column("comments", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_feedback_user_id", "feedback", ["user_id"])
        op.create_index("ix_feedback_vendor_id", "feedback", ["vendor_id"])

    if "rewards" not in existing:
        op.create_table(
            "rewards",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("points_delta", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reason", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_rewards_user_id", "rewards", ["user_id"])

    if "ai_preferences" not in existing:
        op.create_table(
            "ai_preferences",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
            sa.Column("favorite_items", sa.JSON(), nullable=True),
            sa.Column("frequent_slots", sa.JSON(), nullable=True),
            sa.Column("vendor_preferences", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if "vendor_load_metrics" not in existing:
        op.create_table(
            "vendor_load_metrics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.vendor_id"), nullable=False),
            sa.Column("slot_id", sa.Integer(), sa.ForeignKey("slots.id"), nullable=True),
            sa.Column("metric_date", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("avg_queue_length", sa.Float(), nullable=True),
            sa.Column("avg_prep_time_minutes", sa.Float(), nullable=True),
            sa.Column("concurrency", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_vendor_load_metrics_vendor_id", "vendor_load_metrics", ["vendor_id"])


def downgrade() -> None:
    existing = _tables()

    for name in [
        "vendor_load_metrics",
        "ai_preferences",
        "rewards",
        "feedback",
        "group_cart_items",
        "group_cart_members",
        "group_carts",
        "favorites",
        "notifications",
        "payments",
        "order_items",
        "orders",
        "slots",
        "menu_items",
        "vendors",
        "users",
    ]:
        if name in existing:
            op.drop_table(name)

    bind = op.get_bind()
    for enum_name in [
        "groupcartrole",
        "groupcartstatus",
        "paymentstatus",
        "orderstatus",
        "slotstatus",
        "userrole",
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
