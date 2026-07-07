"""Generate realistic campus seed data for TNT.

Usage:
    # optionally set DATABASE_URL, else defaults to sqlite:///tnt_dev.db
    # run from project root (tnt-backend-main)
    python scripts/seed_sample_data.py

This script is idempotent-ish: it truncates target tables before inserting.
"""
import os
import random
import string
from datetime import datetime, timedelta, time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tnt_dev.db")
random.seed(42)

FOOD_VENDORS = [
    ("Campus Cafe", "food"),
    ("Burger Hub", "food"),
    ("Pizza Station", "food"),
    ("Healthy Bites", "food"),
]
STATIONERY_VENDORS = [
    ("Xerox Point", "stationery"),
    ("Print Hub", "stationery"),
    ("Stationery Store", "stationery"),
]

ITEMS_BY_VENDOR = {
    "Campus Cafe": [
        ("Masala Chai", 3000),
        ("Cold Coffee", 4500),
        ("Paneer Roll", 6500),
        ("Veg Puff", 3500),
        ("Samosa", 2000),
        ("Aloo Paratha", 5000),
        ("Cheese Sandwich", 5500),
        ("Brownie", 4000),
    ],
    "Burger Hub": [
        ("Veg Burger", 7500),
        ("Peri Peri Fries", 5000),
        ("Cheese Burger", 9000),
        ("Paneer Burger", 8500),
        ("Tandoori Burger", 9500),
        ("Iced Tea", 3500),
        ("Choco Shake", 5500),
        ("Onion Rings", 4500),
    ],
    "Pizza Station": [
        ("Margherita", 12000),
        ("Veggie Feast", 15000),
        ("Garlic Breadsticks", 6000),
        ("Paneer Tikka Pizza", 17000),
        ("Corn & Cheese", 14000),
        ("Choco Lava", 6500),
        ("Pepsi", 3000),
        ("Stuffed Garlic Bread", 7500),
    ],
    "Healthy Bites": [
        ("Grilled Sandwich", 7000),
        ("Sprout Salad", 6500),
        ("Smoothie Bowl", 8000),
        ("Veg Wrap", 6000),
        ("Fruit Bowl", 5500),
        ("Cold Pressed Juice", 5000),
        ("Oats Upma", 4500),
        ("Protein Shake", 6500),
    ],
    "Xerox Point": [
        ("Notebook Printing", 1000),
        ("Color Printing", 3000),
        ("B/W Printing", 500),
        ("Lamination", 2000),
        ("Scan & Email", 800),
        ("Project Binding", 4000),
        ("ID Card Print", 2500),
        ("Thesis Print", 15000),
    ],
    "Print Hub": [
        ("Poster Printing", 5000),
        ("Banner Printing", 12000),
        ("Photo Print (4x6)", 2000),
        ("Photo Print (A4)", 3000),
        ("Vinyl Sticker", 2500),
        ("Business Cards", 3500),
        ("Brochure Print", 6000),
        ("Booklet Print", 8000),
    ],
    "Stationery Store": [
        ("A4 Notebook", 6000),
        ("Exam Pad", 2500),
        ("Gel Pen Pack", 1500),
        ("Pencil Pack", 800),
        ("Highlighter Pack", 2500),
        ("Eraser & Sharpener", 600),
        ("Geometry Box", 3000),
        ("Sticky Notes", 1200),
    ],
}

ORDER_STATUS_BUCKETS = [
    ("COMPLETED", 0.30),
    ("READY", 0.25),
    ("CONFIRMED", 0.25),  # treating as "PREPARING"
    ("PENDING", 0.20),    # treating as "PLACED"
]


def pick_status() -> str:
    r = random.random()
    acc = 0.0
    for status, pct in ORDER_STATUS_BUCKETS:
        acc += pct
        if r <= acc:
            return status
    return ORDER_STATUS_BUCKETS[-1][0]


def connect() -> Engine:
    return create_engine(DATABASE_URL, future=True)


def reset_tables(engine: Engine) -> None:
    tables = [
        "order_items",
        "payments",
        "orders",
        "group_cart_items",
        "group_cart_members",
        "group_carts",
        "favorites",
        "feedback",
        "notifications",
        "slots",
        "menu_items",
        "vendors",
        "users",
        "ai_preferences",
        "rewards",
        "vendor_load_metrics",
    ]
    with engine.begin() as conn:
        for tbl in tables:
            try:
                conn.execute(text(f"DELETE FROM {tbl}"))
            except Exception:
                pass


def seed_users(conn):
    users = []
    phone_base = 9000000000
    for i in range(50):
        users.append({
            "name": f"Student {i+1}",
            "phone": str(phone_base + i),
            "role": "student",
            "department": random.choice(["CSE", "ECE", "ME", "CE", "MBA"]),
        })
    for i in range(10):
        users.append({
            "name": f"Faculty {i+1}",
            "phone": str(phone_base + 100 + i),
            "role": "faculty",
            "department": random.choice(["CSE", "ECE", "ME", "CE", "MBA"]),
        })
    inserted = []
    for u in users:
        res = conn.execute(
            text(
                """
                INSERT INTO users (name, phone, role, department, created_at)
                VALUES (:name, :phone, :role, :department, :created_at)
                RETURNING id
                """
            ),
            {**u, "created_at": datetime.utcnow()},
        )
        inserted.append(res.scalar_one())
    return inserted


def seed_vendors(conn):
    vendor_ids = {}
    for name, vtype in FOOD_VENDORS + STATIONERY_VENDORS:
        res = conn.execute(
            text(
                """
                INSERT INTO vendors (name, vendor_type, description, created_at)
                VALUES (:name, :vendor_type, :desc, :created_at)
                RETURNING id
                """
            ),
            {"name": name, "vendor_type": vtype, "desc": f"{name} on campus", "created_at": datetime.utcnow()},
        )
        vendor_ids[name] = res.scalar_one()
    return vendor_ids


def seed_menu_items(conn, vendor_ids):
    menu_ids = {}
    for v_name, items in ITEMS_BY_VENDOR.items():
        vid = vendor_ids[v_name]
        menu_ids[vid] = []
        for name, price in items:
            res = conn.execute(
                text(
                    """
                    INSERT INTO menu_items (vendor_id, name, description, price_paise, is_available, created_at)
                    VALUES (:vendor_id, :name, :description, :price_paise, 1, :created_at)
                    RETURNING id
                    """
                ),
                {
                    "vendor_id": vid,
                    "name": name,
                    "description": f"Tasty {name} at {v_name}",
                    "price_paise": price,
                    "created_at": datetime.utcnow(),
                },
            )
            menu_ids[vid].append(res.scalar_one())
    return menu_ids


def seed_slots(conn, vendor_ids):
    slots_by_vendor = {vid: [] for vid in vendor_ids.values()}
    base_date = datetime.utcnow().date()
    start_dt = datetime.combine(base_date, time(9, 0))
    end_dt = datetime.combine(base_date, time(18, 0))
    delta = timedelta(minutes=10)
    for v_name, vid in vendor_ids.items():
        current = start_dt
        while current < end_dt:
            res = conn.execute(
                text(
                    """
                    INSERT INTO slots (vendor_id, start_time, end_time, capacity, current_orders, status)
                    VALUES (:vendor_id, :start_time, :end_time, :capacity, 0, 'OPEN')
                    RETURNING id
                    """
                ),
                {
                    "vendor_id": vid,
                    "start_time": current,
                    "end_time": current + delta,
                    "capacity": random.choice([15, 20, 25]),
                },
            )
            slots_by_vendor[vid].append(res.scalar_one())
            current += delta
    return slots_by_vendor


def seed_orders(conn, user_ids, vendor_ids, menu_ids, slots_by_vendor):
    order_ids = []
    statuses = [s for s, _ in ORDER_STATUS_BUCKETS]
    weights = [p for _, p in ORDER_STATUS_BUCKETS]
    for _ in range(120):
        user_id = random.choice(user_ids)
        vendor_id = random.choice(list(vendor_ids.values()))
        slot_choices = slots_by_vendor[vendor_id]
        slot_id = random.choice(slot_choices) if slot_choices else None
        status = random.choices(statuses, weights=weights, k=1)[0]
        total = 0

        res = conn.execute(
            text(
                """
                INSERT INTO orders (user_id, vendor_id, slot_id, status, total_price_paise, pickup_code, created_at)
                VALUES (:user_id, :vendor_id, :slot_id, :status, :total_price_paise, :pickup_code, :created_at)
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "vendor_id": vendor_id,
                "slot_id": slot_id,
                "status": status,
                "total_price_paise": 0,
                "pickup_code": "PK" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6)),
                "created_at": datetime.utcnow(),
            },
        )
        order_id = res.scalar_one()
        order_ids.append(order_id)

        # order items 1-3 items
        items_for_vendor = menu_ids[vendor_id]
        num_items = random.randint(1, 3)
        total_price = 0
        for _ in range(num_items):
            menu_item_id = random.choice(items_for_vendor)
            quantity = random.randint(1, 3)
            price = conn.execute(text("SELECT price_paise FROM menu_items WHERE id=:id"), {"id": menu_item_id}).scalar_one()
            line_total = price * quantity
            total_price += line_total
            conn.execute(
                text(
                    """
                    INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price_paise, total_price_paise)
                    VALUES (:order_id, :menu_item_id, :quantity, :unit_price_paise, :total_price_paise)
                    """
                ),
                {
                    "order_id": order_id,
                    "menu_item_id": menu_item_id,
                    "quantity": quantity,
                    "unit_price_paise": price,
                    "total_price_paise": line_total,
                },
            )
        conn.execute(text("UPDATE orders SET total_price_paise=:total WHERE id=:id"), {"total": total_price, "id": order_id})

    return order_ids


def seed_payments(conn, order_ids):
    for oid in order_ids:
        conn.execute(
            text(
                """
                INSERT INTO payments (order_id, provider, status, amount_paise, created_at)
                VALUES (:order_id, :provider, :status, :amount_paise, :created_at)
                """
            ),
            {
                "order_id": oid,
                "provider": random.choice(["MOCK", "RAZORPAY"]),
                "status": random.choice(["SUCCESS", "INITIATED", "FAILED", "REFUNDED"]),
                "amount_paise": random.randint(5000, 25000),
                "created_at": datetime.utcnow(),
            },
        )


def seed_feedback(conn, order_ids, user_ids, vendor_ids):
    vendor_list = list(vendor_ids.values())
    sampled_orders = random.sample(order_ids, k=min(60, len(order_ids)))
    for oid in sampled_orders:
        rating = round(random.uniform(4.0, 5.0), 1)
        conn.execute(
            text(
                """
                INSERT INTO feedback (user_id, vendor_id, order_id, rating_quality, rating_time, rating_behavior, comments, created_at)
                VALUES (:user_id, :vendor_id, :order_id, :rq, :rt, :rb, :comments, :created_at)
                """
            ),
            {
                "user_id": random.choice(user_ids),
                "vendor_id": random.choice(vendor_list),
                "order_id": oid,
                "rq": rating,
                "rt": rating,
                "rb": rating,
                "comments": random.choice(["Great!", "Smooth pickup", "Tasty", "On time"]),
                "created_at": datetime.utcnow(),
            },
        )


def seed_favorites(conn, user_ids, vendor_ids):
    for uid in user_ids:
        fav_vendors = random.sample(list(vendor_ids.values()), k=2)
        for vid in fav_vendors:
            conn.execute(
                text(
                    """
                    INSERT INTO favorites (user_id, vendor_id, created_at)
                    VALUES (:user_id, :vendor_id, :created_at)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {
                    "user_id": uid,
                    "vendor_id": vid,
                    "created_at": datetime.utcnow(),
                },
            )


def seed_notifications(conn, user_ids):
    messages = [
        "Order is being prepared",
        "Order is ready for pickup",
        "New slot available",
        "Vendor added new items",
    ]
    for uid in user_ids:
        for _ in range(2):
            conn.execute(
                text(
                    """
                    INSERT INTO notifications (user_id, title, body, is_read, created_at)
                    VALUES (:user_id, :title, :body, 0, :created_at)
                    """
                ),
                {
                    "user_id": uid,
                    "title": "Update",
                    "body": random.choice(messages),
                    "created_at": datetime.utcnow(),
                },
            )


def seed_ai_preferences(conn, user_ids, vendor_ids):
    vids = list(vendor_ids.values())
    for uid in user_ids:
        conn.execute(
            text(
                """
                INSERT INTO ai_preferences (user_id, favorite_items, frequent_slots, vendor_preferences, updated_at)
                VALUES (:user_id, :favorite_items, :frequent_slots, :vendor_preferences, :updated_at)
                ON CONFLICT (user_id) DO UPDATE SET
                    favorite_items = excluded.favorite_items,
                    frequent_slots = excluded.frequent_slots,
                    vendor_preferences = excluded.vendor_preferences,
                    updated_at = excluded.updated_at
                """
            ),
            {
                "user_id": uid,
                "favorite_items": ["Masala Chai", "Veg Burger", "Garlic Breadsticks"],
                "frequent_slots": ["09:30", "12:10", "17:20"],
                "vendor_preferences": random.sample(vids, k=2),
                "updated_at": datetime.utcnow(),
            },
        )


def main():
    engine = connect()
    reset_tables(engine)
    with engine.begin() as conn:
        user_ids = seed_users(conn)
        vendor_ids = seed_vendors(conn)
        menu_ids = seed_menu_items(conn, vendor_ids)
        slots_by_vendor = seed_slots(conn, vendor_ids)
        order_ids = seed_orders(conn, user_ids, vendor_ids, menu_ids, slots_by_vendor)
        seed_payments(conn, order_ids)
        seed_feedback(conn, order_ids, user_ids, vendor_ids)
        seed_favorites(conn, user_ids, vendor_ids)
        seed_notifications(conn, user_ids)
        seed_ai_preferences(conn, user_ids, vendor_ids)
    print("Seed data generated successfully.")


if __name__ == "__main__":
    main()
