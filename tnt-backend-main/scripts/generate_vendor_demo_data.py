#!/usr/bin/env python3
"""Generate comprehensive demo data for the Vendor Module.

Creates:
- 10 Vendors
- 200 Menu Items
- 500 Orders
- 100 Notifications
- 50 Promotions
- 100 Analytics Records

Usage:
    python scripts/generate_vendor_demo_data.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.time_utils import utcnow_naive
from app.database.session import SessionLocal
from app.modules.menu.model import MenuItem
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.vendors.model import Vendor, VendorStaff
from app.modules.vendors.profile_models import VendorProfile, VendorStaffPermission
from app.modules.vendors.settlement_models import VendorWallet, VendorTransaction, VendorSettlement
from app.modules.vendors.retention_models import VendorPromotion, VendorLoyaltyProgram, CustomerLoyalty
from app.modules.notifications.model import Notification
from app.modules.users.model import User


# ── Helpers ────────────────────────────────────────────────────────────────

def random_phone() -> str:
    return f"+91{random.randint(7000000000, 9999999999)}"


def random_email(name: str) -> str:
    return f"{name.lower().replace(' ', '.')}@example.com"


def random_date(days_back: int = 90) -> datetime:
    return utcnow_naive() - timedelta(days=random.randint(0, days_back))


# ── Main Generator ─────────────────────────────────────────────────────────

def main() -> None:
    db = SessionLocal()
    try:
        print("🚀 Starting Vendor Module Demo Data Generation...")

        # ── 1. Ensure Users exist ──────────────────────────────────────────
        print("\n👥 Creating users...")
        users = []
        for i in range(1, 11):
            phone = f"999000000{i:02d}"
            user = db.query(User).filter(User.phone == phone).first()
            if not user:
                user = User(
                    phone=phone,
                    name=f"Vendor Owner {i}",
                    email=f"vendor{i}@example.com",
                    role="VENDOR",
                    is_verified=True,
                )
                db.add(user)
                db.flush()
            users.append(user)
        db.commit()
        print(f"   ✅ {len(users)} users ready")

        # ── 2. Create 10 Vendors ───────────────────────────────────────────
        print("\n🏪 Creating vendors...")
        vendors = []
        categories = ["food", "stationery", "food", "food", "stationery", "food", "food", "stationery", "food", "food"]
        vendor_names = [
            "Spice Garden", "Paper World", "Burger Barn", "Tiffin Express",
            "Study Station", "Dragon Wok", "Cafe Mocha", "Ink & Paper",
            "Pizza Point", "Lunch Box"
        ]

        for i, user in enumerate(users):
            vendor = db.query(Vendor).filter(Vendor.owner_id == user.id).first()
            if not vendor:
                vendor = Vendor(
                    vendor_name=vendor_names[i],
                    category=categories[i],
                    owner_id=user.id,
                    password_hash="hashed_password",
                    status="active",
                )
                db.add(vendor)
                db.flush()
            vendors.append(vendor)
        db.commit()
        print(f"   ✅ {len(vendors)} vendors created")

        # ── 3. Create Vendor Profiles ──────────────────────────────────────
        print("\n📋 Creating vendor profiles...")
        for vendor in vendors:
            profile = db.query(VendorProfile).filter(VendorProfile.vendor_id == vendor.vendor_id).first()
            if not profile:
                profile = VendorProfile(
                    vendor_id=vendor.vendor_id,
                    business_name=vendor.vendor_name,
                    category=vendor.category,
                    description=f"Best {vendor.category} in town! Quality guaranteed.",
                    phone=random_phone(),
                    email=random_email(vendor.vendor_name),
                    location=f"Shop {random.randint(1, 50)}, Market Street, City",
                    latitude=Decimal(f"{random.uniform(12.9, 13.1):.6f}"),
                    longitude=Decimal(f"{random.uniform(77.5, 77.7):.6f}"),
                    logo_url=f"https://example.com/logos/{vendor.vendor_name.lower().replace(' ', '_')}.png",
                    cover_image=f"https://example.com/covers/{vendor.vendor_name.lower().replace(' ', '_')}.jpg",
                    business_hours={
                        "monday": {"open": "09:00", "close": "21:00"},
                        "tuesday": {"open": "09:00", "close": "21:00"},
                        "wednesday": {"open": "09:00", "close": "21:00"},
                        "thursday": {"open": "09:00", "close": "21:00"},
                        "friday": {"open": "09:00", "close": "22:00"},
                        "saturday": {"open": "10:00", "close": "22:00"},
                        "sunday": {"open": "10:00", "close": "20:00"},
                    },
                    pickup_instructions="Please collect your order within 15 minutes. Show order ID at counter.",
                    holidays=[
                        {"date": "2024-12-25", "reason": "Christmas"},
                        {"date": "2025-01-01", "reason": "New Year"},
                    ],
                    is_open=True,
                    max_pickup_distance_km=5.0,
                    prep_time_minutes=15,
                )
                db.add(profile)
        db.commit()
        print(f"   ✅ {len(vendors)} vendor profiles created")

        # ── 4. Create Staff Members ────────────────────────────────────────
        print("\n👔 Creating staff members...")
        staff_count = 0
        for vendor in vendors:
            existing_staff = db.query(VendorStaff).filter(VendorStaff.vendor_id == vendor.vendor_id).count()
            if existing_staff == 0:
                # Add 1 manager
                manager = VendorStaff(
                    vendor_id=vendor.vendor_id,
                    name=f"{vendor.vendor_name} Manager",
                    role="manager",
                    phone=random_phone(),
                    is_active=True,
                )
                db.add(manager)
                db.flush()

                # Manager permissions
                manager_perms = [
                    "orders.view", "orders.accept", "orders.prepare", "orders.ready", "orders.complete",
                    "menu.view", "menu.edit", "menu.toggle_availability",
                    "slots.view", "slots.manage",
                    "analytics.view",
                    "profile.view", "profile.edit",
                    "staff.view",
                    "promotions.view",
                ]
                for perm in manager_perms:
                    db.add(VendorStaffPermission(staff_id=manager.id, permission=perm, is_granted=True))

                # Add 2 staff
                for j in range(2):
                    staff = VendorStaff(
                        vendor_id=vendor.vendor_id,
                        name=f"Staff {j+1} @ {vendor.vendor_name}",
                        role="staff",
                        phone=random_phone(),
                        is_active=True,
                    )
                    db.add(staff)
                    db.flush()

                    staff_perms = [
                        "orders.view", "orders.accept", "orders.prepare", "orders.ready", "orders.complete",
                        "menu.view",
                        "slots.view",
                        "profile.view",
                    ]
                    for perm in staff_perms:
                        db.add(VendorStaffPermission(staff_id=staff.id, permission=perm, is_granted=True))
                    staff_count += 2
                staff_count += 1
        db.commit()
        print(f"   ✅ Staff created (1 manager + 2 staff per vendor)")

        # ── 5. Create 200 Menu Items ───────────────────────────────────────
        print("\n🍔 Creating menu items...")
        menu_count = 0
        for vendor in vendors:
            existing = db.query(MenuItem).filter(MenuItem.vendor_id == vendor.vendor_id).count()
            if existing < 20:
                items_to_add = 20 - existing
                for j in range(items_to_add):
                    item = MenuItem(
                        vendor_id=vendor.vendor_id,
                        name=f"{vendor.vendor_name} Item {j+1}",
                        description=f"Delicious item {j+1} from {vendor.vendor_name}",
                        price=random.randint(50, 500),
                        category=random.choice(["main", "starter", "dessert", "beverage"]),
                        is_available=random.choice([True, True, True, False]),
                        preparation_time=random.randint(5, 30),
                    )
                    db.add(item)
                    menu_count += 1
        db.commit()
        print(f"   ✅ {menu_count} menu items created")

        # ── 6. Create 500 Orders ───────────────────────────────────────────
        print("\n📦 Creating orders...")
        order_count = 0
        payment_count = 0
        for vendor in vendors:
            existing_orders = db.query(Order).filter(Order.vendor_id == vendor.vendor_id).count()
            orders_to_add = 50 - existing_orders
            for _ in range(orders_to_add):
                order_date = random_date(90)
                status = random.choice([
                    OrderStatus.PICKED, OrderStatus.PICKED, OrderStatus.PICKED,
                    OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.COMPLETED
                ])

                order = Order(
                    vendor_id=vendor.vendor_id,
                    user_id=random.choice(users).id,
                    slot_id=random.randint(1, 10),
                    total_amount=random.randint(100, 1000),
                    status=status,
                    created_at=order_date,
                    updated_at=order_date + timedelta(minutes=random.randint(5, 60)),
                )
                db.add(order)
                db.flush()

                # Add order items
                menu_items = db.query(MenuItem).filter(MenuItem.vendor_id == vendor.vendor_id).limit(5).all()
                for _ in range(random.randint(1, 3)):
                    if menu_items:
                        item = random.choice(menu_items)
                        db.add(OrderItem(
                            order_id=order.id,
                            menu_item_id=item.id,
                            quantity=random.randint(1, 3),
                            price=item.price,
                        ))

                # Add payment (70% online, 30% cash)
                if random.random() < 0.7:
                    payment = Payment(
                        order_id=order.id,
                        amount=order.total_amount * 100,  # paise
                        status=PaymentStatus.SUCCESS,
                        razorpay_payment_id=f"pay_{random.randint(100000, 999999)}",
                        created_at=order_date,
                    )
                    db.add(payment)
                    payment_count += 1

                order_count += 1
        db.commit()
        print(f"   ✅ {order_count} orders created ({payment_count} with payments)")

        # ── 7. Create Wallets & Transactions ───────────────────────────────
        print("\n💰 Creating wallets and transactions...")
        for vendor in vendors:
            wallet = db.query(VendorWallet).filter(VendorWallet.vendor_id == vendor.vendor_id).first()
            if not wallet:
                wallet = VendorWallet(
                    vendor_id=vendor.vendor_id,
                    total_earned=random.uniform(10000, 50000),
                    total_pending=random.uniform(1000, 5000),
                    total_settled=random.uniform(5000, 30000),
                    total_refunded=random.uniform(100, 1000),
                    balance=random.uniform(5000, 20000),
                )
                db.add(wallet)
                db.flush()

            # Add some transactions
            existing_tx = db.query(VendorTransaction).filter(VendorTransaction.vendor_id == vendor.vendor_id).count()
            if existing_tx == 0:
                for _ in range(10):
                    tx_type = random.choice(["online_payment", "cash_order", "refund"])
                    amount = random.uniform(100, 1000)
                    db.add(VendorTransaction(
                        vendor_id=vendor.vendor_id,
                        order_id=random.randint(1, 100),
                        transaction_type=tx_type,
                        amount=amount,
                        fee=amount * 0.02 if tx_type == "online_payment" else 0,
                        net_amount=amount * 0.98 if tx_type == "online_payment" else amount,
                        description=f"Transaction for order",
                        payment_method="online" if tx_type == "online_payment" else "cash",
                        is_online=tx_type == "online_payment",
                        created_at=random_date(30),
                    ))

                # Add settlement
                db.add(VendorSettlement(
                    vendor_id=vendor.vendor_id,
                    period_start=utcnow_naive() - timedelta(days=30),
                    period_end=utcnow_naive(),
                    total_amount=random.uniform(5000, 20000),
                    total_fees=random.uniform(100, 500),
                    net_amount=random.uniform(4000, 19000),
                    order_count=random.randint(20, 100),
                    online_payments=random.uniform(3000, 15000),
                    cash_orders=random.uniform(1000, 5000),
                    refunds=random.uniform(100, 500),
                    status=random.choice(["pending", "processing", "completed"]),
                    settled_at=random_date(7) if random.random() < 0.5 else None,
                ))
        db.commit()
        print(f"   ✅ Wallets, transactions, and settlements created")

        # ── 8. Create Promotions ───────────────────────────────────────────
        print("\n🎉 Creating promotions...")
        promo_count = 0
        for vendor in vendors:
            existing = db.query(VendorPromotion).filter(VendorPromotion.vendor_id == vendor.vendor_id).count()
            for _ in range(5 - existing):
                promo = VendorPromotion(
                    vendor_id=vendor.vendor_id,
                    title=f"{vendor.vendor_name} Special Offer {promo_count+1}",
                    description=f"Get {random.randint(10, 50)}% off on all items!",
                    discount_type=random.choice(["percentage", "fixed"]),
                    discount_value=random.randint(10, 50),
                    min_order_amount=random.randint(100, 500),
                    max_discount=random.randint(50, 200),
                    start_date=utcnow_naive() - timedelta(days=random.randint(0, 30)),
                    end_date=utcnow_naive() + timedelta(days=random.randint(1, 60)),
                    is_active=random.choice([True, True, False]),
                    usage_limit=random.randint(50, 200),
                    usage_count=random.randint(0, 50),
                )
                db.add(promo)
                promo_count += 1
        db.commit()
        print(f"   ✅ {promo_count} promotions created")

        # ── 9. Create Loyalty Programs ─────────────────────────────────────
        print("\n⭐ Creating loyalty programs...")
        for vendor in vendors:
            program = db.query(VendorLoyaltyProgram).filter(VendorLoyaltyProgram.vendor_id == vendor.vendor_id).first()
            if not program:
                db.add(VendorLoyaltyProgram(
                    vendor_id=vendor.vendor_id,
                    program_name=f"{vendor.vendor_name} Rewards",
                    points_per_rupee=random.uniform(1, 5),
                    redemption_rate=random.uniform(0.1, 0.5),
                    min_points_redemption=random.randint(100, 500),
                    is_active=True,
                ))
        db.commit()
        print(f"   ✅ Loyalty programs created")

        # ── 10. Create Notifications ───────────────────────────────────────
        print("\n🔔 Creating notifications...")
        notif_count = 0
        for vendor in vendors:
            existing = db.query(Notification).filter(Notification.vendor_id == vendor.vendor_id).count()
            for _ in range(10 - existing):
                notif = Notification(
                    vendor_id=vendor.vendor_id,
                    title=f"Notification for {vendor.vendor_name}",
                    message=f"Sample notification {notif_count+1}",
                    notification_type=random.choice(["order", "promotion", "system", "alert"]),
                    is_read=random.choice([True, False]),
                    created_at=random_date(30),
                )
                db.add(notif)
                notif_count += 1
        db.commit()
        print(f"   ✅ {notif_count} notifications created")

        print("\n✅ Demo data generation complete!")
        print("\n📊 Summary:")
        print(f"   • Vendors: {len(vendors)}")
        print(f"   • Menu Items: {menu_count}")
        print(f"   • Orders: {order_count}")
        print(f"   • Notifications: {notif_count}")
        print(f"   • Promotions: {promo_count}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()