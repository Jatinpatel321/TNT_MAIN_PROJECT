"""Baseline schema capture

Revision ID: 20260214_0001
Revises: (None)
Create Date: 2026-02-14 00:00:00

NOTE: This migration was originally a no-op. The actual schema was created
via Base.metadata.create_all() in init_db.py.  This backfill was added in
the June 2026 re-audit to give the migration chain a recoverable baseline.
On existing databases this migration is *stamped* (not re-run); on a fresh
database it creates the original core tables so that every subsequent
migration in the chain has a real parent schema.

What is included here
---------------------
Only the original tables that existed before *any* Alembic migration ran
(``users``, ``slots``, ``orders``, ``stationery_jobs``, etc.).  Tables
introduced by later migrations (e.g. ``slot_bookings``, ``ml_models``,
``vendor_reviews``) are not listed here — they are created by their own
upgrade scripts.

Usage
-----
Production / staging (already applied):
    alembic stamp 20260214_0001

Fresh database:
    alembic upgrade head
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260214_0001"
down_revision = None
branch_labels = None
depends_on = None


# --------------------------------------------------------------------------
# Helper: only create a table if it does not already exist.
# This makes the migration idempotent for the (rare) case where it runs
# against an already-create_all'd database.
# --------------------------------------------------------------------------


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    # ── users ───────────────────────────────────────────────────────────
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("phone", sa.String(20), nullable=False, unique=True),
            sa.Column("name", sa.String(100), nullable=True),
            sa.Column("full_name", sa.String(100), nullable=True),
            sa.Column("role", sa.String(50), nullable=False, server_default="student"),
            sa.Column("vendor_type", sa.String(50), nullable=False, server_default="food"),
            sa.Column("university_id", sa.String(50), nullable=True),
            sa.Column("department", sa.String(100), nullable=True),
            sa.Column("semester", sa.Integer(), nullable=True),
            sa.Column("profile_image", sa.String(255), nullable=True),
            sa.Column("device_token", sa.String(512), nullable=True),
            sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("preferences", sa.JSON(), nullable=True),
            sa.Column("totp_secret", sa.String(64), nullable=True),
            sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_users_phone", "users", ["phone"])

    # ── slots ───────────────────────────────────────────────────────────
    if not _table_exists("slots"):
        op.create_table(
            "slots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("start_time", sa.DateTime(), nullable=False),
            sa.Column("end_time", sa.DateTime(), nullable=False),
            sa.Column("max_orders", sa.Integer(), nullable=False),
            sa.Column("current_orders", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("congestion_level", sa.Float(), nullable=True, server_default="0"),
            sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("locked_by", sa.String(100), nullable=True),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="available"),
            sa.Column("slot_duration_minutes", sa.Integer(), nullable=True),
            sa.Column("is_peak_hour", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("is_faculty_priority", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("auto_block_enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("dynamic_capacity", sa.Integer(), nullable=True),
            sa.Column("capacity_notes", sa.Text(), nullable=True),
        )
        op.create_index("ix_slots_vendor_id", "slots", ["vendor_id"])

    # ── stationery_services ─────────────────────────────────────────────
    if not _table_exists("stationery_services"):
        op.create_table(
            "stationery_services",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("service_type", sa.String(50), nullable=False, server_default="print"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price_per_page", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_capacity", sa.Integer(), nullable=True),
            sa.Column("current_load", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_available", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("image_url", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("price_per_unit", sa.Integer(), nullable=True),
            sa.Column("unit", sa.String(50), nullable=True),
        )

    # ── stationery_jobs ─────────────────────────────────────────────────
    if not _table_exists("stationery_jobs"):
        op.create_table(
            "stationery_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("service_id", sa.Integer(), sa.ForeignKey("stationery_services.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("file_url", sa.String(255), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_paid", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("razorpay_order_id", sa.String(100), nullable=True),
            sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
            sa.Column("razorpay_signature", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="submitted"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            # Legacy columns for compatibility
            sa.Column("service_name", sa.String(255), nullable=True),
            sa.Column("file_name", sa.String(255), nullable=True),
            sa.Column("pages", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("copies", sa.Integer(), nullable=True, server_default="1"),
            sa.Column("binding", sa.Boolean(), nullable=True, server_default="0"),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
        )

    # ── orders ──────────────────────────────────────────────────────────
    if not _table_exists("orders"):
        op.create_table(
            "orders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("slot_id", sa.Integer(), sa.ForeignKey("slots.id"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="placed"),
            sa.Column("total_amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("qr_code", sa.String(255), nullable=True, unique=True),
            sa.Column("pickup_confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("pickup_confirmed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("eta_minutes", sa.Integer(), nullable=True),
            sa.Column("actual_completion_minutes", sa.Integer(), nullable=True),
            sa.Column("fraud_flag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("flagged_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("stationery_job_id", sa.Integer(), sa.ForeignKey("stationery_jobs.id"), nullable=True),
            sa.Column("booking_type", sa.String(20), nullable=False, server_default="food"),
        )
        op.create_index("ix_orders_user_id", "orders", ["user_id"])
        op.create_index("ix_orders_vendor_id", "orders", ["vendor_id"])


    # ── menu_items ──────────────────────────────────────────────────────
    if not _table_exists("menu_items"):
        op.create_table(
            "menu_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("price", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_available", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_veg", sa.Boolean(), nullable=True, server_default="0"),
            sa.Column("current_stock", sa.Integer(), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("image_url", sa.String(255), nullable=True),
            sa.Column("prep_time_minutes", sa.Integer(), nullable=True, server_default="10"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_menu_items_vendor_id", "menu_items", ["vendor_id"])

    # ── order_items ─────────────────────────────────────────────────────
    if not _table_exists("order_items"):
        op.create_table(
            "order_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("price_at_time", sa.Float(), nullable=False),
        )
        op.create_index("ix_order_items_order_id", "order_items", ["order_id"])

    # ── notifications ───────────────────────────────────────────────────
    if not _table_exists("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # ── payments ────────────────────────────────────────────────────────
    if not _table_exists("payments"):
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="initiated"),
            sa.Column("razorpay_order_id", sa.String(100), nullable=True),
            sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
            sa.Column("razorpay_signature", sa.String(255), nullable=True),
            sa.Column("idempotency_key", sa.String(128), nullable=True, unique=True),
            sa.Column("razorpay_refund_id", sa.String(100), nullable=True),
            sa.Column("refunded_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_payments_order_id", "payments", ["order_id"])




    # ── vendors ─────────────────────────────────────────────────────────
    if not _table_exists("vendors"):
        op.create_table(
            "vendors",
            sa.Column("vendor_id", sa.Integer(), primary_key=True),
            sa.Column("vendor_name", sa.String(255), nullable=False),
            sa.Column("vendor_type", sa.String(50), nullable=False, server_default="food"),
            sa.Column("phone", sa.String(20), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("image_url", sa.String(255), nullable=True),
            sa.Column("rating", sa.Float(), nullable=True, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_approved", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("password_hash", sa.String(255), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # ── feedback ────────────────────────────────────────────────────────
    if not _table_exists("feedback"):
        op.create_table(
            "feedback",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=True),
            sa.Column("overall_rating", sa.Integer(), nullable=True),
            sa.Column("quality_rating", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("time_rating", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("behavior_rating", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # ── rewards ─────────────────────────────────────────────────────────
    if not _table_exists("rewards"):
        op.create_table(
            "rewards",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("reason", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_rewards_user_id", "rewards", ["user_id"])

    # ── vouchers ────────────────────────────────────────────────────────
    if not _table_exists("vouchers"):
        op.create_table(
            "vouchers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(50), nullable=False, unique=True),
            sa.Column("discount_type", sa.String(10), nullable=False),
            sa.Column("discount_value", sa.Integer(), nullable=False),
            sa.Column("min_order_amount", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("max_redemptions", sa.Integer(), nullable=True),
            sa.Column("redemption_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("expiry_date", sa.DateTime(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )





    # ── ledger ──────────────────────────────────────────────────────────
    if not _table_exists("ledger_entries"):
        op.create_table(
            "ledger_entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("type", sa.String(10), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("order_id", sa.Integer(), nullable=True),
            sa.Column("balance_after", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # ── off_peak_policies ───────────────────────────────────────────────
    if not _table_exists("off_peak_policies"):
        op.create_table(
            "off_peak_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("time_windows", sa.JSON(), nullable=True),
            sa.Column("bonus_points_per_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # ── reservations / groups ──────────────────────────────────────
    if not _table_exists("groups"):
        op.create_table(
            "groups",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(100), nullable=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if not _table_exists("group_members"):
        op.create_table(
            "group_members",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False, server_default="member"),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
        )

    # ── Group cart items ────────────────────────────────────────────────
    if not _table_exists("cart_items"):
        op.create_table(
            "cart_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("group_id", sa.Integer(), sa.ForeignKey("groups.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # ── order_history ───────────────────────────────────────────────────
    if not _table_exists("order_history"):
        op.create_table(
            "order_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("changed_by", sa.String(100), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("changed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    """Drop all tables created above (in reverse dependency order)."""
    tables = [
        "order_history",
        "cart_items",
        "group_members",
        "groups",
        "off_peak_policies",
        "ledger_entries",
        "complaints",
        "stationery_services",
        "vouchers",
        "rewards",
        "feedback",
        "vendors",
        "stationery_jobs",
        "menu_items",
        "payments",
        "notifications",
        "order_items",
        "orders",
        "slots",
        "users",
    ]
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    for t_name in tables:
        if t_name in existing:
            op.drop_table(t_name)
