#!/usr/bin/env python
"""
Direct SQL seeder to add demo data to TNT database.
Extends the base seed with additional users, items, orders, notifications.
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'tnt_dev.db'

def utcnow():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def rupees(v):
    return int(round(v * 100))

def add_users(conn):
    """Add 40 more users to reach 50 total."""
    cur = conn.cursor()

    users = [
        ('7016918111', 'Ishaan Mehta', 'STUDENT', 'UNIV-2024-09', '{"preferred_pickup_hour": 13}'),
        ('7016918112', 'Priya Kapoor', 'STUDENT', 'UNIV-2024-10', '{"preferred_pickup_hour": 12}'),
        ('7016918113', 'Vikram Singh', 'STUDENT', 'UNIV-2024-11', '{"preferred_pickup_hour": 19}'),
        ('7016918114', 'Neha Gupta', 'STUDENT', 'UNIV-2024-12', '{"preferred_pickup_hour": 14}'),
        ('7016918115', 'Rohit Sharma', 'STUDENT', 'UNIV-2024-13', '{"preferred_pickup_hour": 20}'),
        ('7016918116', 'Tanvi Desai', 'STUDENT', 'UNIV-2024-14', '{"preferred_pickup_hour": 11}'),
        ('7016918117', 'Karthik Nair', 'STUDENT', 'UNIV-2024-15', '{"preferred_pickup_hour": 13}'),
        ('7016918118', 'Aisha Khan', 'STUDENT', 'UNIV-2024-16', '{"preferred_pickup_hour": 21}'),
        ('7016918119', 'Yash Patel', 'STUDENT', 'UNIV-2024-17', '{"preferred_pickup_hour": 10}'),
        ('7016918120', 'Diya Reddy', 'STUDENT', 'UNIV-2024-18', '{"preferred_pickup_hour": 12}'),
        ('7016918121', 'Varun Malhotra', 'STUDENT', 'UNIV-2024-19', '{"preferred_pickup_hour": 18}'),
        ('7016918122', 'Shreya Joshi', 'STUDENT', 'UNIV-2024-20', '{"preferred_pickup_hour": 9}'),
        ('7016918123', 'Aditya Verma', 'STUDENT', 'UNIV-2024-21', '{"preferred_pickup_hour": 13}'),
        ('7016918124', 'Rhea Mukherjee', 'STUDENT', 'UNIV-2024-22', '{"preferred_pickup_hour": 14}'),
        ('7016918125', 'Dhruv Saxena', 'STUDENT', 'UNIV-2024-23', '{"preferred_pickup_hour": 19}'),
        ('7016918126', 'Anvi Sharma', 'STUDENT', 'UNIV-2024-24', '{"preferred_pickup_hour": 20}'),
        ('7016918127', 'Aryan Gupta', 'STUDENT', 'UNIV-2024-25', '{"preferred_pickup_hour": 18}'),
        ('7016918128', 'Kavya Iyer', 'STUDENT', 'UNIV-2024-26', '{"preferred_pickup_hour": 12}'),
        ('7016918129', 'Veer Rathore', 'STUDENT', 'UNIV-2024-27', '{"preferred_pickup_hour": 21}'),
        ('7016918130', 'Myra Choudhury', 'STUDENT', 'UNIV-2024-28', '{"preferred_pickup_hour": 10}'),
        ('7016918131', 'Krish Bansal', 'STUDENT', 'UNIV-2024-29', '{"preferred_pickup_hour": 13}'),
        ('7016918132', 'Anaya Kapoor', 'STUDENT', 'UNIV-2024-30', '{"preferred_pickup_hour": 14}'),
        ('7016918133', 'Pranav Kulkarni', 'STUDENT', 'UNIV-2024-31', '{"preferred_pickup_hour": 19}'),
        ('7016918134', 'Trisha Sen', 'STUDENT', 'UNIV-2024-32', '{"preferred_pickup_hour": 11}'),
        ('7016918135', 'Aryan Deshmukh', 'STUDENT', 'UNIV-2024-33', '{"preferred_pickup_hour": 20}'),
        ('7016918136', 'Siya Bhatia', 'STUDENT', 'UNIV-2024-34', '{"preferred_pickup_hour": 12}'),
        ('7016918137', 'Advik Menon', 'STUDENT', 'UNIV-2024-35', '{"preferred_pickup_hour": 13}'),
        ('7016918138', 'Kiara Malhotra', 'STUDENT', 'UNIV-2024-36', '{"preferred_pickup_hour": 18}'),
        ('7016918139', 'Reyansh Pandey', 'STUDENT', 'UNIV-2024-37', '{"preferred_pickup_hour": 19}'),
        ('7016918140', 'Ahana Rao', 'STUDENT', 'UNIV-2024-38', '{"preferred_pickup_hour": 14}'),
        ('7016918141', 'Vihaan Sharma', 'STUDENT', 'UNIV-2024-39', '{"preferred_pickup_hour": 20}'),
        ('7016918142', 'Sara Ali', 'STUDENT', 'UNIV-2024-40', '{"preferred_pickup_hour": 21}'),
        ('7016918143', 'Aarnav Kaul', 'STUDENT', 'UNIV-2024-41', '{"preferred_pickup_hour": 10}'),
        ('7016918144', 'Riva Sinha', 'STUDENT', 'UNIV-2024-42', '{"preferred_pickup_hour": 9}'),
        ('7016918145', 'Hritik Dhawan', 'STUDENT', 'UNIV-2024-43', '{"preferred_pickup_hour": 13}'),
        ('7016918146', 'Drishti Saha', 'STUDENT', 'UNIV-2024-44', '{"preferred_pickup_hour": 12}'),
        ('7016918147', 'Ansh Nigam', 'STUDENT', 'UNIV-2024-45', '{"preferred_pickup_hour": 18}'),
        ('7016918148', 'Pari Mallick', 'STUDENT', 'UNIV-2024-46', '{"preferred_pickup_hour": 19}'),
        ('7016918149', 'Ashwin Kumar', 'STUDENT', 'UNIV-2024-47', '{"preferred_pickup_hour": 20}'),
        ('7016918150', 'Bhoomi Trivedi', 'STUDENT', 'UNIV-2024-48', '{"preferred_pickup_hour": 11}'),
        ('7016918151', 'Shivani Bose', 'STUDENT', 'UNIV-2024-49', '{"preferred_pickup_hour": 14}'),
        ('7016918152', 'Laksh Narayan', 'STUDENT', 'UNIV-2024-50', '{"preferred_pickup_hour": 13}'),
    ]

    added = 0
    for phone, name, role, uid, prefs in users:
        cur.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cur.fetchone():
            continue
        cur.execute('''
            INSERT INTO users (phone, name, role, university_id, is_active, is_approved, preferences, vendor_type, created_at)
            VALUES (?, ?, ?, ?, 1, 1, ?, 'food', ?)
        ''', (phone, name, role, uid, prefs, utcnow()))
        added += 1

    conn.commit()
    print(f"Added {added} new users")

def add_vendor(conn):
    """Add 1 more food vendor to reach 9 total."""
    cur = conn.cursor()

    # Check if Noodle House already exists
    cur.execute("SELECT id FROM users WHERE phone = '9810001006'")
    existing = cur.fetchone()

    if existing:
        print(f"Noodle House already exists (ID={existing[0]})")
        return existing[0]

    cur.execute('''
        INSERT INTO users (phone, name, role, university_id, is_active, is_approved, vendor_type, preferences, created_at)
        VALUES ('9810001006', 'Noodle House', 'VENDOR', 'VEN-NOD-09', 1, 1, 'food', '{"vendor_profile": {"category": "Asian Cuisine", "description": "Fresh wok-tossed noodles"}}', ?)
    ''', (utcnow(),))

    vendor_id = cur.lastrowid

    # Add vendor profile
    cur.execute('''
        INSERT INTO vendor_profiles (vendor_id, category, description, rating, location, logo_url, cover_image, is_open)
        VALUES (?, 'Asian Cuisine', 'Fresh wok-tossed noodles, fried rice, and dim sum baskets', 4.6, 'East Wing Food Court',
                'https://cdn.tapntake.app/vendors/noodle_house_logo.png', 'https://cdn.tapntake.app/vendors/noodle_house_cover.jpg', 1)
    ''', (vendor_id,))

    conn.commit()
    print(f"Added 1 new vendor (Noodle House ID={vendor_id})")
    return vendor_id

def add_menu_items(conn, vendor_id):
    """Add 60 more menu items to reach 100 total."""
    cur = conn.cursor()

    # Get all vendor IDs
    cur.execute("SELECT id FROM users WHERE role = 'VENDOR'")
    vendor_ids = [r[0] for r in cur.fetchall()]

    items = [
        # Noodle House items
        (vendor_id, 'Veg Hakka Noodles', 'Wok-tossed veggies with soy sauce', rupees(149), 'https://cdn.tapntake.app/menu/veg_hakka.jpg'),
        (vendor_id, 'Schezwan Noodles', 'Spicy red chilli paste noodles', rupees(159), 'https://cdn.tapntake.app/menu/schezwan_noodles.jpg'),
        (vendor_id, 'Veg Fried Rice', 'Fluffy rice with mixed veggies', rupees(139), 'https://cdn.tapntake.app/menu/fried_rice.jpg'),
        (vendor_id, 'Steamed Momos', '8-piece vegetable momo basket', rupees(129), 'https://cdn.tapntake.app/menu/momos.jpg'),
        (vendor_id, 'Veg Manchurian', 'Crispy balls in tangy sauce', rupees(169), 'https://cdn.tapntake.app/menu/manchurian.jpg'),
        (vendor_id, 'Spring Rolls', 'Crispy rolls with veggie filling', rupees(119), 'https://cdn.tapntake.app/menu/spring_rolls.jpg'),
        (vendor_id, 'Thai Red Curry', 'Coconut curry with veggies', rupees(189), 'https://cdn.tapntake.app/menu/thai_curry.jpg'),
        (vendor_id, 'Dim Sum Platter', 'Assorted dim sum basket', rupees(199), 'https://cdn.tapntake.app/menu/dim_sum.jpg'),
    ]

    # Add more items to existing vendors
    for vid in vendor_ids:
        if vid == vendor_id:
            continue
        cur.execute("SELECT name FROM users WHERE id = ?", (vid,))
        vendor_name = cur.fetchone()[0]

        if 'Campus' in vendor_name:
            items.extend([
                (vid, 'Butter Croissant', 'Flaky French pastry', rupees(99), 'https://cdn.tapntake.app/menu/croissant.jpg'),
                (vid, 'Iced Vanilla Latte', 'Espresso with vanilla and cold milk', rupees(129), 'https://cdn.tapntake.app/menu/iced_latte.jpg'),
                (vid, 'Mango Lassi Shake', 'Seasonal mango yogurt shake', rupees(149), 'https://cdn.tapntake.app/menu/mango_shake.jpg'),
                (vid, 'Tea Cake Slice', 'Traditional tea-time cake', rupees(79), 'https://cdn.tapntake.app/menu/tea_cake.jpg'),
            ])
        elif 'Burger' in vendor_name:
            items.extend([
                (vid, 'Double Cheese Burger', 'Double patty, triple cheese', rupees(219), 'https://cdn.tapntake.app/menu/double_cheese.jpg'),
                (vid, 'Veggie Delight Burger', 'Loaded vegetable patty', rupees(149), 'https://cdn.tapntake.app/menu/veggie_delight.jpg'),
                (vid, 'Onion Rings', 'Crispy breaded onion rings', rupees(99), 'https://cdn.tapntake.app/menu/onion_rings.jpg'),
                (vid, 'Strawberry Milkshake', 'Fresh strawberry shake', rupees(139), 'https://cdn.tapntake.app/menu/strawberry_shake.jpg'),
            ])
        elif 'Spice' in vendor_name:
            items.extend([
                (vid, 'Rava Dosa', 'Crispy semolina crepe', rupees(119), 'https://cdn.tapntake.app/menu/rava_dosa.jpg'),
                (vid, 'Paneer Dosa', 'Cottage cheese stuffed dosa', rupees(159), 'https://cdn.tapntake.app/menu/paneer_dosa.jpg'),
                (vid, 'Poori Bhaji', 'Puffy bread with potato curry', rupees(129), 'https://cdn.tapntake.app/menu/poori_bhaji.jpg'),
                (vid, 'Curd Rice', 'Cool yogurt rice with pickle', rupees(99), 'https://cdn.tapntake.app/menu/curd_rice.jpg'),
            ])
        elif 'Green' in vendor_name:
            items.extend([
                (vid, 'Quinoa Wrap', 'Quinoa and greens in tortilla', rupees(179), 'https://cdn.tapntake.app/menu/quinoa_wrap.jpg'),
                (vid, 'Beetroot Salad', 'Roasted beets with feta', rupees(169), 'https://cdn.tapntake.app/menu/beet_salad.jpg'),
                (vid, 'Mango Smoothie', 'Fresh mango blended', rupees(139), 'https://cdn.tapntake.app/menu/mango_smoothie.jpg'),
                (vid, 'Overnight Oats', 'Pre-soaked oats with berries', rupees(149), 'https://cdn.tapntake.app/menu/overnight_oats.jpg'),
            ])
        elif 'Pizza' in vendor_name:
            items.extend([
                (vid, 'Pepper Paneer Pizza', 'Paneer with bell peppers', rupees(279), 'https://cdn.tapntake.app/menu/pepper_paneer.jpg'),
                (vid, 'Cheese Burst Pizza', 'Extra cheese layer inside', rupees(319), 'https://cdn.tapntake.app/menu/cheese_burst_pizza.jpg'),
                (vid, 'Garlic Knots', 'Twisted garlic bread bites', rupees(119), 'https://cdn.tapntake.app/menu/garlic_knots.jpg'),
                (vid, 'Veg Lasagna', 'Layered pasta bake', rupees(249), 'https://cdn.tapntake.app/menu/lasagna.jpg'),
            ])

    added = 0
    for vid, name, desc, price, img in items:
        cur.execute('SELECT id FROM menu_items WHERE vendor_id = ? AND name = ?', (vid, name))
        if cur.fetchone():
            continue
        cur.execute('''
            INSERT INTO menu_items (vendor_id, name, description, price, image_url, is_available)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (vid, name, desc, price, img))
        added += 1

    conn.commit()
    print(f"Added {added} new menu items")

def add_slots(conn, vendor_id):
    """Add slots for new vendor."""
    cur = conn.cursor()
    now = datetime.utcnow()
    base_day = now.replace(hour=8, minute=0, second=0, microsecond=0)

    slots = [
        (vendor_id, base_day.replace(hour=9), base_day.replace(hour=10), 24, 0, 'available'),
        (vendor_id, base_day.replace(hour=12), base_day.replace(hour=13, minute=30), 48, 0, 'available'),
        (vendor_id, base_day.replace(hour=18), base_day.replace(hour=19, minute=30), 42, 0, 'available'),
    ]

    for vid, start, end, max_ord, cur_ord, status in slots:
        cur.execute('''
            INSERT INTO slots (vendor_id, start_time, end_time, max_orders, current_orders, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (vid, start, end, max_ord, cur_ord, status))

    conn.commit()
    print(f"Added {len(slots)} slots for new vendor")

def add_orders(conn):
    """Add 10 more orders to reach 30 total."""
    cur = conn.cursor()

    # Get user IDs
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT' ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]

    # Get vendor IDs with slots
    cur.execute("SELECT DISTINCT vendor_id FROM slots")
    vendor_ids = [r[0] for r in cur.fetchall()]

    # Get slot IDs
    cur.execute("SELECT id, vendor_id FROM slots ORDER BY id")
    slots = cur.fetchall()

    # Get menu items
    cur.execute("SELECT id, vendor_id, price FROM menu_items ORDER BY id")
    menu_items = cur.fetchall()

    now = datetime.utcnow()
    orders_data = []

    for i, uid in enumerate(user_ids[:10]):
        if i >= len(vendor_ids):
            break
        vid = vendor_ids[i % len(vendor_ids)]
        slot = next((s for s in slots if s[1] == vid), slots[0])
        slot_id = slot[0]

        # Find items for this vendor
        vendor_items = [m for m in menu_items if m[1] == vid][:2]
        if len(vendor_items) < 2:
            vendor_items = menu_items[:2]

        status = ['picked', 'ready', 'confirmed', 'preparing'][i % 4]
        days_ago = i % 5
        eta = [15, 20, 25, 18][i % 4]

        orders_data.append({
            'user_id': uid,
            'vendor_id': vid,
            'slot_id': slot_id,
            'status': status,
            'days_ago': days_ago,
            'eta': eta,
            'items': [(vendor_items[0][0], 1, vendor_items[0][2]), (vendor_items[1][0], 1, vendor_items[1][2])] if len(vendor_items) > 1 else [(vendor_items[0][0], 2, vendor_items[0][2])]
        })

    created = 0
    for od in orders_data:
        created_at = (now - timedelta(days=od['days_ago'])).strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('''
            INSERT INTO orders (user_id, vendor_id, slot_id, status, created_at, eta_minutes, qr_code, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (od['user_id'], od['vendor_id'], od['slot_id'], od['status'], created_at, od['eta'],
              f'TNT-{created:03d}-DEMO', sum(i[1] * i[2] for i in od['items'])))
        order_id = cur.lastrowid

        for item_id, qty, price in od['items']:
            cur.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_time)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item_id, qty, price))

        created += 1

    conn.commit()
    print(f"Added {created} new orders")

def add_notifications(conn):
    """Add 20 more notifications to reach 50 total."""
    cur = conn.cursor()

    # Get user IDs
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT' ORDER BY id")
    user_ids = [r[0] for r in cur.fetchall()]

    notif_types = ['order_placed', 'order_accepted', 'order_preparing', 'order_ready', 'pickup_reminder', 'delay_alert', 'promo', 'system']
    messages = [
        ('Order Placed', 'Your order has been placed successfully.'),
        ('Order Accepted', 'Vendor confirmed your order.'),
        ('Order Preparing', 'Your food is being prepared.'),
        ('Order Ready', 'Your order is ready for pickup.'),
        ('Pickup Reminder', 'Head to the counter for pickup.'),
        ('Flash Sale', 'Get 15% off on all items today!'),
        ('New Vendor', 'Check out our newest food vendor!'),
        ('Rewards Update', 'You earned bonus points on your last order!'),
    ]

    now = datetime.utcnow()
    created = 0
    for i, uid in enumerate(user_ids):
        if created >= 25:
            break
        msg = messages[i % len(messages)]
        ntype = notif_types[i % len(notif_types)]
        is_read = 1 if i % 3 == 0 else 0
        created_at = (now - timedelta(hours=i, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

        cur.execute('''
            INSERT INTO notifications (user_id, title, message, notification_type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (uid, msg[0], msg[1], ntype, is_read, created_at))
        created += 1

    conn.commit()
    print(f"Added {created} new notifications")

def add_more_feedback(conn):
    """Add additional feedback records."""
    cur = conn.cursor()

    # Get picked/completed orders
    cur.execute("SELECT id, user_id, vendor_id FROM orders WHERE status IN ('picked', 'completed', 'ready')")
    orders = cur.fetchall()

    now = datetime.utcnow()
    created = 0
    for i, (oid, uid, vid) in enumerate(orders[:15]):
        q = 3 + (i % 3)
        t = 3 + (i % 3)
        b = 4 + (i % 2)
        overall = round((q + t + b) / 3)

        cur.execute('''
            INSERT INTO feedback (order_id, user_id, vendor_id, quality_rating, time_rating, behavior_rating, overall_rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (oid, uid, vid, q, t, b, overall, f'Order #{oid} was great!' if i % 2 == 0 else None, (now - timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S')))
        created += 1

    conn.commit()
    print(f"Added {created} additional feedback records")

def create_summary(conn):
    """Print final summary."""
    cur = conn.cursor()

    tables = ['users', 'menu_items', 'orders', 'notifications', 'feedback', 'vendor_reviews', 'slots', 'reward_points']
    print("\n=== Final Database Summary ===")
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM {t}')
        print(f'{t}: {cur.fetchone()[0]}')

    cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    print("\nUsers by role:")
    for row in cur.fetchall():
        print(f'  {row[0]}: {row[1]}')

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        print("Adding additional demo data...")
        add_users(conn)
        vendor_id = add_vendor(conn)
        add_menu_items(conn, vendor_id)
        add_slots(conn, vendor_id)
        add_orders(conn)
        add_notifications(conn)
        add_more_feedback(conn)
        create_summary(conn)
        print("\nDemo data population complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
