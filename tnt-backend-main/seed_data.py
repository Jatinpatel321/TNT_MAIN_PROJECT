"""
Seed script — populates the TNT database with realistic sample data.

Usage:
    cd tnt-backend-main
    python seed_data.py

Requires:
    - PostgreSQL running and accessible at DATABASE_URL in .env
    - All tables already created (run `alembic upgrade head` if needed)
"""

import os
import sys
import random
from datetime import timedelta
from pathlib import Path

# Ensure the app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Import ALL models so tables get registered ──────────────────────────────
import app.database.init_db
from app.database.base import Base
from app.modules.users.model import User, UserRole
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot, SlotStatus
from app.modules.complaints.model import Complaint, ComplaintCategory, ComplaintStatus
from app.core.time_utils import utcnow_naive

# ─── CONFIG ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── HELPERS ────────────────────────────────────────────────────────────────
def random_past_days(days_back=45):
    """Return a naive datetime between now and ``days_back`` days ago."""
    now = utcnow_naive()
    delta = random.randint(0, days_back * 24 * 60)  # minutes
    return now - timedelta(minutes=delta)


def reset_db():
    """Drop all rows (in dependency order) and recreate tables."""
    print("🧹 Clearing existing data …")
    db = SessionLocal()
    try:
        from sqlalchemy import text
        table_names = list(Base.metadata.tables.keys())
        if table_names:
            tables_str = ", ".join([f'"{name}"' for name in table_names])
            db.execute(text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;"))
        db.commit()
        print("   ✓ All data cleared via TRUNCATE CASCADE.")
    except Exception as e:
        db.rollback()
        print(f"   ⚠️ TRUNCATE CASCADE failed: {e}. Trying direct delete...")
        # Fallback to direct delete in case metadata is not fully populated
        for table in reversed(Base.metadata.sorted_tables):
            try:
                db.execute(table.delete())
                db.commit()
            except Exception as ex:
                db.rollback()
                print(f"      Could not delete from {table.name}: {ex}")
    finally:
        db.close()


# ─── SEED DATA ──────────────────────────────────────────────────────────────
def seed_users(db):
    """Create admin, vendors, students, and faculty."""
    users = []

    # 1 admin
    admin = User(
        phone="9999999999",
        name="Admin User",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True,
        is_approved=True,
        created_at=random_past_days(30),
    )
    users.append(admin)

    # 3 super admins
    for i, name in enumerate(["Super Admin", "Root Admin", "System Admin"]):
        u = User(
            phone=f"999999990{i}",
            name=name,
            full_name=name,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_approved=True,
            created_at=random_past_days(30),
        )
        users.append(u)

    # 8 vendors (mix of food and stationery, some pending)
    vendor_data = [
        ("Campus Cafe", "food", True, True),
        ("Parul Mess", "food", True, True),
        ("Juice Junction", "food", True, True),
        ("Stationery Shop", "stationery", True, True),
        ("Book Nook", "stationery", True, True),
        ("Tandoor Express", "food", True, True),
        ("Pizza Hub", "food", True, False),         # active but not approved → "pending"
        ("Art & Craft", "stationery", False, False), # neither active nor approved
    ]
    for name, vtype, approved, active in vendor_data:
        u = User(
            phone=f"988{random.randint(1000000, 9999999)}",
            name=name,
            full_name=name,
            role=UserRole.VENDOR,
            vendor_type=vtype,
            is_approved=approved,
            is_active=active,
            created_at=random_past_days(20),
        )
        users.append(u)

    # 25 students
    for i in range(1, 26):
        u = User(
            phone=f"98765{str(i).zfill(5)}",
            name=f"Student {i}",
            full_name=f"Student Full Name {i}",
            role=UserRole.STUDENT,
            university_id=f"PU2024{str(i).zfill(4)}",
            department=random.choice(["CSE", "IT", "ECE", "ME", "CE", "EE"]),
            semester=random.randint(1, 8),
            is_active=True,
            is_approved=True,
            created_at=random_past_days(45),
        )
        users.append(u)

    # 5 faculty
    for i in range(1, 6):
        u = User(
            phone=f"98700{str(i).zfill(5)}",
            name=f"Faculty {i}",
            full_name=f"Faculty Full Name {i}",
            role=UserRole.FACULTY,
            university_id=f"FAC{str(i).zfill(4)}",
            department=random.choice(["CSE", "IT", "ECE", "ME", "CE"]),
            is_active=True,
            is_approved=True,
            created_at=random_past_days(30),
        )
        users.append(u)

    db.add_all(users)
    db.commit()
    print(f"   ✓ {len(users)} users created (1 admin, 3 super_admins, {len(vendor_data)} vendors, 25 students, 5 faculty).")
    return {u.name: u for u in users}  # name → object map


def seed_menu_items(db, users_map):
    """Create menu items for each approved food & stationery vendor."""
    items = []
    food_vendors = [
        u for name, u in users_map.items()
        if u.role == UserRole.VENDOR and u.vendor_type == "food" and u.is_approved and u.is_active
    ]
    stationery_vendors = [
        u for name, u in users_map.items()
        if u.role == UserRole.VENDOR and u.vendor_type == "stationery" and u.is_approved and u.is_active
    ]

    food_items_pool = [
        ("Samosa", 20, ""), ("Vada Pav", 15, ""), ("Pav Bhaji", 50, ""),
        ("Pizza Slice", 80, ""), ("Burger", 60, ""), ("French Fries", 40, ""),
        ("Sandwich", 45, ""), ("Pasta", 70, ""), ("Noodles", 55, ""),
        ("Biriyani Rice", 100, ""), ("Chicken Roll", 80, ""), ("Paneer Wrap", 70, ""),
        ("Cold Coffee", 50, ""), ("Mango Shake", 60, ""), ("Lassi", 40, ""),
        ("Chapati Meal", 60, ""), ("Dal Rice", 50, ""), ("Idli (2 pcs)", 30, ""),
    ]
    stationery_items_pool = [
        ("Notebook (120p)", 60, ""), ("Pen Pack (5)", 30, ""), ("Pencil Box", 45, ""),
        ("Eraser Pack", 15, ""), ("Sharpener", 10, ""), ("Scale (15cm)", 12, ""),
        ("Geometry Box", 85, ""), ("Sketch Pen (12)", 80, ""), ("A4 Sheets (100)", 50, ""),
        ("Glue Stick", 20, ""), ("Tape Roll", 25, ""), ("Stapler + Pins", 55, ""),
    ]

    for vendor in food_vendors:
        chosen = random.sample(food_items_pool, k=random.randint(4, 8))
        for name, price, _ in chosen:
            item = MenuItem(
                vendor_id=vendor.id,
                name=name,
                price=price,
                image_url=f"https://placehold.co/200x200?text={name.replace(' ','+')}",
                is_available=True,
            )
            items.append(item)

    for vendor in stationery_vendors:
        chosen = random.sample(stationery_items_pool, k=random.randint(4, 7))
        for name, price, _ in chosen:
            item = MenuItem(
                vendor_id=vendor.id,
                name=name,
                price=price,
                image_url=f"https://placehold.co/200x200?text={name.replace(' ','+')}",
                is_available=True,
            )
            items.append(item)

    db.add_all(items)
    db.commit()
    print(f"   ✓ {len(items)} menu items created.")
    return items


def seed_slots(db, users_map):
    """Create time slots for each approved vendor."""
    slots = []
    approved_vendors = [
        u for name, u in users_map.items()
        if u.role == UserRole.VENDOR and u.is_approved and u.is_active
    ]
    base = utcnow_naive()

    for vendor in approved_vendors:
        # Morning slots (8 AM - 12 PM)
        for h in [8, 9, 10, 11]:
            start = base.replace(hour=h, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            slots.append(Slot(
                vendor_id=vendor.id,
                start_time=start,
                end_time=end,
                max_orders=random.randint(20, 50),
                current_orders=random.randint(0, 15),
                status=SlotStatus.AVAILABLE,
            ))

        # Lunch slots (12 PM - 3 PM)
        for h in [12, 13, 14]:
            start = base.replace(hour=h, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            slots.append(Slot(
                vendor_id=vendor.id,
                start_time=start,
                end_time=end,
                max_orders=random.randint(30, 60),
                current_orders=random.randint(5, 25),
                status=SlotStatus.AVAILABLE,
            ))

        # Evening slots (4 PM - 8 PM)
        for h in [16, 17, 18, 19]:
            start = base.replace(hour=h, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            slots.append(Slot(
                vendor_id=vendor.id,
                start_time=start,
                end_time=end,
                max_orders=random.randint(25, 55),
                current_orders=random.randint(0, 20),
                status=SlotStatus.AVAILABLE,
            ))

    db.add_all(slots)
    db.commit()
    print(f"   ✓ {len(slots)} time slots created.")
    return slots


def seed_orders(db, users_map, menu_items, slots):
    """Create orders with order items and payments spanning the last 30 days."""
    students = [u for u in users_map.values() if u.role == UserRole.STUDENT]
    faculty = [u for u in users_map.values() if u.role == UserRole.FACULTY]

    # Weighted statuses so the chart looks realistic
    status_weights = [
        (OrderStatus.PLACED, 8),
        (OrderStatus.CONFIRMED, 10),
        (OrderStatus.PREPARING, 15),
        (OrderStatus.READY, 18),
        (OrderStatus.PICKED, 25),
        (OrderStatus.CANCELLED, 5),
        (OrderStatus.PENDING, 5),
        (OrderStatus.READY_FOR_PICKUP, 10),
        (OrderStatus.COMPLETED, 14),
    ]
    status_pool = []
    for s, w in status_weights:
        status_pool.extend([s] * w)

    orders = []
    order_items_list = []
    payments = []

    for _ in range(200):
        user = random.choice(students + faculty)
        slot = random.choice(slots)
        vendor_id = slot.vendor_id
        status = random.choice(status_pool)
        created = random_past_days(30)

        # Find menu items for this vendor
        vendor_items = [m for m in menu_items if m.vendor_id == vendor_id]
        if not vendor_items:
            continue

        num_items = random.randint(1, 4)
        chosen_items = random.sample(vendor_items, min(num_items, len(vendor_items)))
        total_amount = sum(item.price * random.randint(1, 3) for item in chosen_items)

        order = Order(
            user_id=user.id,
            vendor_id=vendor_id,
            slot_id=slot.id,
            status=status,
            total_amount=total_amount,
            created_at=created,
            fraud_flag=random.random() < 0.03,  # 3% flagged as fraud
        )
        orders.append(order)

        # Flush to get order ID
        db.add(order)
        db.flush()

        for item in chosen_items:
            qty = random.randint(1, 3)
            oi = OrderItem(
                order_id=order.id,
                menu_item_id=item.id,
                quantity=qty,
                price_at_time=item.price,
            )
            order_items_list.append(oi)

        # Payment (skip payment for some cancelled orders)
        pay_status = PaymentStatus.SUCCESS
        if status == OrderStatus.CANCELLED and random.random() < 0.5:
            pay_status = PaymentStatus.FAILED

        payment = Payment(
            order_id=order.id,
            amount=total_amount,
            status=pay_status,
            razorpay_order_id=f"order_{random.randint(10000000, 99999999)}",
            created_at=created + timedelta(minutes=random.randint(1, 5)),
        )
        payments.append(payment)

    db.add_all(order_items_list)
    db.add_all(payments)
    db.commit()
    print(f"   ✓ {len(orders)} orders, {len(order_items_list)} order items, {len(payments)} payments created.")


def seed_complaints(db, users_map):
    """Create sample complaints from students/faculty."""
    students = [u for u in users_map.values() if u.role == UserRole.STUDENT]
    faculty = [u for u in users_map.values() if u.role == UserRole.FACULTY]
    complainants = students + faculty
    vendors = [
        u for u in users_map.values()
        if u.role == UserRole.VENDOR and u.is_approved
    ]

    complaint_categories = list(ComplaintCategory)
    complaint_statuses = [ComplaintStatus.OPEN, ComplaintStatus.IN_PROGRESS, ComplaintStatus.RESOLVED, ComplaintStatus.ASSIGNED]
    complaint_descriptions = [
        "Order arrived 30 minutes late",
        "Received the wrong item",
        "Food quality was poor",
        "Item was missing from the order",
        "Portion size too small",
        "Overcharged for the order",
        "Staff was rude at pickup",
    ]

    complaints = []
    for _ in range(15):
        complaint = Complaint(
            user_id=random.choice(complainants).id,
            vendor_id=random.choice(vendors).id,
            category=random.choice(complaint_categories),
            status=random.choice(complaint_statuses),
            title=random.choice(complaint_descriptions),
            description=f"Sample complaint: {random.choice(complaint_descriptions)}",
            created_at=random_past_days(20),
        )
        complaints.append(complaint)

    db.add_all(complaints)
    db.commit()
    print(f"   ✓ {len(complaints)} complaints created.")


# ─── MAIN ───────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("   🌱 TNT DATABASE SEEDER")
    print("=" * 60)

    # Confirm with user
    print("\n⚠️  This will DELETE all existing data and reseed from scratch!")
    confirm = input("   Type 'yes' to continue: ")
    if confirm.lower() != "yes":
        print("   Aborted.")
        return

    reset_db()
    db = SessionLocal()
    try:
        print("\n📦 Seeding users …")
        users_map = seed_users(db)

        print("\n🍽️  Seeding menu items …")
        menu_items = seed_menu_items(db, users_map)

        print("\n⏰ Seeding time slots …")
        slots = seed_slots(db, users_map)

        print("\n📋 Seeding orders & payments …")
        seed_orders(db, users_map, menu_items, slots)

        print("\n⚠️  Seeding complaints …")
        seed_complaints(db, users_map)

        print("\n" + "=" * 60)
        print("   ✅ DATABASE SEEDED SUCCESSFULLY!")
        print("=" * 60)
        print()
        print("   Dashboard will now show real data:")
        print("   - 1 admin + 3 super admins")
        print("   - 6 approved + 2 pending vendors")
        print("   - 25 students + 5 faculty")
        print("   - 200 orders across statuses")
        print("   - Payments with revenue")
        print("   - Menu items & time slots per vendor")
        print("   - 15 sample complaints")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()