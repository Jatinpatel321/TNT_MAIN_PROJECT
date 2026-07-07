#!/usr/bin/env python3
"""Add remaining demo data: more menu items, groups, slot bookings, reward points, favorites."""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'tnt_dev.db'

def utcnow():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def add_more_menu_items(conn):
    """Add more menu items to reach 100+."""
    cur = conn.cursor()

    # Get vendors
    cur.execute("SELECT id, name FROM users WHERE role = 'VENDOR' AND vendor_type = 'food'")
    vendors = list(cur.fetchall())

    items = []
    for vid, vname in vendors:
        # Add 3 more items per vendor
        if 'Campus' in vname:
            items.extend([
                (vid, 'Cold Brew Coffee', 'Smooth cold-steeped coffee', 14900, 'https://cdn.tapntake.app/menu/cold_brew.jpg'),
                (vid, 'Blueberry Muffin', 'Fresh baked muffin', 8900, 'https://cdn.tapntake.app/menu/blueberry_muffin.jpg'),
                (vid, 'Avocado Toast', 'Creamy avocado on sourdough', 15900, 'https://cdn.tapntake.app/menu/avocado_toast.jpg'),
            ])
        elif 'Burger' in vname:
            items.extend([
                (vid, 'BBQ Chicken Burger', 'Grilled chicken with BBQ sauce', 19900, 'https://cdn.tapntake.app/menu/bbq_chicken.jpg'),
                (vid, 'Loaded Fries', 'Cheese and bacon fries', 13900, 'https://cdn.tapntake.app/menu/loaded_fries.jpg'),
                (vid, 'Chocolate Brownie', 'Rich chocolate treat', 9900, 'https://cdn.tapntake.app/menu/brownie.jpg'),
            ])
        elif 'Spice' in vname:
            items.extend([
                (vid, 'Set Dosa', '3-piece soft dosa set', 10900, 'https://cdn.tapntake.app/menu/set_dosa.jpg'),
                (vid, 'Upma', 'Semolina breakfast', 8900, 'https://cdn.tapntake.app/menu/upma.jpg'),
                (vid, 'Filter Coffee', 'Traditional South Indian', 4900, 'https://cdn.tapntake.app/menu/filter_coffee.jpg'),
            ])
        elif 'Green' in vname:
            items.extend([
                (vid, 'Caesar Salad', 'Classic caesar with croutons', 16900, 'https://cdn.tapntake.app/menu/caesar.jpg'),
                (vid, 'Fruit Bowl', 'Seasonal mixed fruits', 14900, 'https://cdn.tapntake.app/menu/fruit_bowl.jpg'),
                (vid, 'Green Detox Smoothie', 'Kale and spinach blend', 13900, 'https://cdn.tapntake.app/menu/detox.jpg'),
            ])
        elif 'Pizza' in vname:
            items.extend([
                (vid, 'BBQ Chicke Pizza', 'Smoky BBQ base pizza', 24900, 'https://cdn.tapntake.app/menu/bbq_pizza.jpg'),
                (vid, 'Mac and Cheese', 'Creamy macaroni pasta', 14900, 'https://cdn.tapntake.app/menu/mac_cheese.jpg'),
                (vid, 'Tiramisu', 'Italian coffee dessert', 17000, 'https://cdn.tapntake.app/menu/tiramisu.jpg'),
            ])
        elif 'Noodle' in vname:
            items.extend([
                (vid, 'Wonton Soup', 'Clear broth dumpling soup', 12900, 'https://cdn.tapntake.app/menu/wonton_soup.jpg'),
                (vid, 'Pancake Stack', 'Fluffy pancakes with syrup', 15900, 'https://cdn.tapntake.app/menu/pancakes.jpg'),
                (vid, 'Kung Pao Tofu', 'Spicy tofu stir fry', 17900, 'https://cdn.tapntake.app/menu/kung_pao.jpg'),
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
    print(f"Added {added} more menu items")

def add_groups(conn):
    """Add study groups for group ordering feature."""
    cur = conn.cursor()

    # Get students
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT' LIMIT 15")
    students = [r[0] for r in cur.fetchall()]

    if not students:
        print("No students found")
        return

    # Create 3 groups
    groups = [
        ('CS 2024 Study Group', students[0]),
        ('Anime Club Orders', students[1]),
        ('Hostel A Buddies', students[2]),
    ]

    added_groups = 0
    group_ids = []
    for name, owner_id in groups:
        cur.execute('SELECT id FROM groups WHERE name = ?', (name,))
        if cur.fetchone():
            continue
        created_at = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('''
            INSERT INTO groups (name, owner_id, status, created_at)
            VALUES (?, ?, 'active', ?)
        ''', (name, owner_id, created_at))
        group_ids.append(cur.lastrowid)
        added_groups += 1

    conn.commit()
    print(f"Added {added_groups} groups")

    # Add members to groups
    added_members = 0
    for i, gid in enumerate(group_ids):
        # Add 3-5 members per group
        start_idx = i * 5
        for j in range(min(5, len(students) - start_idx)):
            uid = students[start_idx + j]
            role = 'owner' if j == 0 else 'member'
            cur.execute('''
                INSERT INTO group_members (group_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            ''', (gid, uid, role, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
            added_members += 1

    conn.commit()
    print(f"Added {added_members} group members")

    # Add some group cart items
    cur.execute("SELECT id, price FROM menu_items LIMIT 6")
    items = cur.fetchall()

    added_items = 0
    for gid in group_ids:
        for i, uid in enumerate(students[:3]):
            if i >= len(items):
                continue
            item_id, price = items[i]
            cur.execute('''
                INSERT INTO group_cart_items (group_id, owner_id, menu_item_id, quantity, price_at_time, added_at)
                VALUES (?, ?, ?, 1, ?, ?)
            ''', (gid, uid, item_id, price, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
            added_items += 1

    conn.commit()
    print(f"Added {added_items} group cart items")

def add_slot_bookings(conn):
    """Add slot bookings for users."""
    cur = conn.cursor()

    # Get slots
    cur.execute("SELECT id, vendor_id FROM slots WHERE status = 'available'")
    slots = cur.fetchall()

    # Get students
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT' LIMIT 20")
    students = [r[0] for r in cur.fetchall()]

    added = 0
    for i, uid in enumerate(students):
        if i >= len(slots):
            break
        slot = slots[i % len(slots)]
        # Check if booking exists
        cur.execute('SELECT id FROM slot_bookings WHERE slot_id = ? AND user_id = ?', (slot[0], uid))
        if cur.fetchone():
            continue
        cur.execute('''
            INSERT INTO slot_bookings (slot_id, user_id, status, booked_at)
            VALUES (?, ?, 'confirmed', ?)
        ''', (slot[0], uid, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
        added += 1

    conn.commit()
    print(f"Added {added} slot bookings")

def add_more_reward_points(conn):
    """Add reward points for more users."""
    cur = conn.cursor()

    # Get students
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT'")
    students = [r[0] for r in cur.fetchall()]

    # Check current points
    cur.execute("SELECT user_id FROM reward_points")
    existing = set(r[0] for r in cur.fetchall())

    added = 0
    for uid in students:
        if uid in existing:
            # Update existing
            cur.execute('UPDATE reward_points SET points = points + ? WHERE user_id = ?', (1000 + added * 50, uid))
        else:
            # Create new
            cur.execute('''
                INSERT INTO reward_points (user_id, points, total_earned, total_redeemed, created_at)
                VALUES (?, ?, ?, 0, ?)
            ''', (uid, 1000 + added * 50, 1000 + added * 50, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
            added += 1

    conn.commit()
    print(f"Added/updated reward points for {len(students)} users")

def add_reward_redemptions(conn):
    """Add more reward redemptions."""
    cur = conn.cursor()

    # Get students with points
    cur.execute("SELECT user_id, points FROM reward_points WHERE points > 500")
    users = cur.fetchall()

    added = 0
    for i, (uid, pts) in enumerate(users[:15]):
        points_used = min(pts, 500 + i * 50)
        value = points_used * 0.1  # 10% of points as value
        redemption_type = 'discount' if i % 2 == 0 else 'item'
        desc = f'{"10% discount" if i % 2 == 0 else "Free coffee"} redemption'
        cur.execute('''
            INSERT INTO reward_redemptions (user_id, redemption_type, points_used, value, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (uid, redemption_type, points_used, value, desc, (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d %H:%M:%S')))
        added += 1

    conn.commit()
    print(f"Added {added} reward redemptions")

def create_summary(conn):
    """Print final summary."""
    cur = conn.cursor()

    print("\n" + "="*50)
    print("FINAL DATABASE SUMMARY")
    print("="*50)

    cur.execute("SELECT COUNT(*) FROM users")
    print(f"Users: {cur.fetchone()[0]} (target: 50)")

    cur.execute("SELECT COUNT(*) FROM vendor_profiles")
    print(f"Vendors: {cur.fetchone()[0]} (target: 9)")

    cur.execute("SELECT COUNT(*) FROM menu_items")
    print(f"Menu Items: {cur.fetchone()[0]} (target: 100)")

    cur.execute("SELECT COUNT(*) FROM orders")
    print(f"Orders: {cur.fetchone()[0]} (target: 30)")

    cur.execute("SELECT COUNT(*) FROM notifications")
    print(f"Notifications: {cur.fetchone()[0]} (target: 50)")

    cur.execute("SELECT COUNT(*) FROM feedback")
    print(f"Feedback/Ratings: {cur.fetchone()[0]} (target: 50)")

    cur.execute("SELECT COUNT(*) FROM vendor_reviews")
    print(f"Vendor Reviews: {cur.fetchone()[0]} (target: 20)")

    cur.execute("SELECT COUNT(*) FROM reward_points")
    print(f"Reward Points Records: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM reward_redemptions")
    print(f"Reward Redemptions: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM groups")
    print(f"Groups: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM group_members")
    print(f"Group Members: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM slot_bookings")
    print(f"Slot Bookings: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM slots")
    print(f"Slots: {cur.fetchone()[0]}")

    print("="*50)

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        print("Adding final demo data...")
        add_more_menu_items(conn)
        add_groups(conn)
        add_slot_bookings(conn)
        add_more_reward_points(conn)
        add_reward_redemptions(conn)
        create_summary(conn)
        print("\nDemo data population complete!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
