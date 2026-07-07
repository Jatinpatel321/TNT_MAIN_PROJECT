#!/usr/bin/env python3
"""Complete demo data - ensure every user has orders, notifications, and activity."""

import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'tnt_dev.db'

def add_orders_for_all_users(conn):
    """Ensure all users have at least one order."""
    cur = conn.cursor()

    # Get students without orders
    cur.execute('''
        SELECT u.id FROM users u
        WHERE u.role = 'STUDENT'
        AND u.id NOT IN (SELECT DISTINCT user_id FROM orders)
    ''')
    users_without_orders = [r[0] for r in cur.fetchall()]

    # Get slots
    cur.execute("SELECT id, vendor_id FROM slots")
    slots = cur.fetchall()

    # Get menu items
    cur.execute("SELECT id, vendor_id, price FROM menu_items")
    items = cur.fetchall()

    if not slots or not items:
        print("No slots or items found")
        return

    statuses = ['picked', 'ready', 'confirmed', 'preparing', 'completed']
    now = datetime.utcnow()

    added = 0
    for i, uid in enumerate(users_without_orders):
        slot = slots[i % len(slots)]
        slot_id, vid = slot[0], slot[1]

        # Find items for this vendor
        vendor_items = [m for m in items if m[1] == vid][:2]
        if len(vendor_items) < 2:
            vendor_items = items[i*2:i*2+2] if i*2+2 <= len(items) else items[:2]

        status = statuses[i % len(statuses)]
        days_ago = random.randint(1, 7)
        eta = random.randint(10, 30)
        created_at = (now - timedelta(days=days_ago, hours=i)).strftime('%Y-%m-%d %H:%M:%S')
        qr = f'TNT-{added:04d}'
        total = sum(m[2] for m in vendor_items[:2])

        cur.execute('''
            INSERT INTO orders (user_id, vendor_id, slot_id, status, created_at, eta_minutes, qr_code, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uid, vid, slot_id, status, created_at, eta, qr, total))

        order_id = cur.lastrowid

        for mid, _, price in vendor_items[:2]:
            cur.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_time)
                VALUES (?, ?, 1, ?)
            ''', (order_id, mid, price))

        added += 1

    conn.commit()
    print(f"Added {added} orders for users without orders")

def add_notifications_for_all(conn):
    """Ensure all users have notifications."""
    cur = conn.cursor()

    # Get students without notifications
    cur.execute('''
        SELECT u.id FROM users u
        WHERE u.role = 'STUDENT'
        AND u.id NOT IN (SELECT DISTINCT user_id FROM notifications)
    ''')
    users_without_notifs = [r[0] for r in cur.fetchall()]

    notif_types = [
        ('order_placed', 'Order Placed', 'Your order has been placed successfully.'),
        ('order_accepted', 'Order Accepted', 'Vendor confirmed your order.'),
        ('order_ready', 'Order Ready', 'Your order is ready for pickup.'),
        ('promo', 'Flash Sale', 'Get 15% off on all items today!'),
        ('system', 'Welcome', 'Welcome to TapNTake! Start ordering now.'),
    ]

    now = datetime.utcnow()
    added = 0

    for i, uid in enumerate(users_without_notifs):
        # Add 3 notifications per user
        for j, (ntype, title, msg) in enumerate(notif_types[:3]):
            created = (now - timedelta(hours=j*2, days=i%3)).strftime('%Y-%m-%d %H:%M:%S')
            cur.execute('''
                INSERT INTO notifications (user_id, title, message, notification_type, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (uid, title, msg, ntype, 1 if j == 0 else 0, created))
            added += 1

    conn.commit()
    print(f"Added {added} notifications for users without notifications")

def add_ai_recommendations(conn):
    """Add AI recommendation data for all users."""
    cur = conn.cursor()

    # Get students and vendors
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT'")
    students = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT id, vendor_id FROM menu_items ORDER BY RANDOM()")
    items = cur.fetchall()

    if not items or not students:
        return

    added = 0
    for i, uid in enumerate(students[:30]):  # Limit to 30 users for AI data
        # Add 5 recommendations per user
        user_items = items[i*5:(i+1)*5] if (i+1)*5 <= len(items) else items[:5]
        for score_offset, (item_id, vid) in enumerate(user_items):
            score = 0.85 - (score_offset * 0.1) + (random.random() * 0.05)
            reason = ['previous_order', 'trending', 'similar_order', 'popular', 'time_based'][score_offset]
            cur.execute('SELECT id FROM ai_recommendations WHERE user_id = ? AND menu_item_id = ?', (uid, item_id))
            if cur.fetchone():
                continue
            cur.execute('''
                INSERT INTO ai_recommendations (user_id, vendor_id, menu_item_id, score, reason_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (uid, vid, item_id, score, reason, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
            added += 1

    conn.commit()
    print(f"Added {added} AI recommendations")

def create_final_summary(conn):
    """Print final verification."""
    cur = conn.cursor()

    print("\n" + "="*60)
    print("FINAL DEMO DATA VERIFICATION")
    print("="*60)

    # Users with orders
    cur.execute('SELECT COUNT(DISTINCT user_id) FROM orders')
    users_with_orders = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM users WHERE role = 'STUDENT'")
    total_students = cur.fetchone()[0]
    print(f"Users with orders: {users_with_orders}/{total_students}")

    # Users with notifications
    cur.execute('SELECT COUNT(DISTINCT user_id) FROM notifications')
    users_with_notifs = cur.fetchone()[0]
    print(f"Users with notifications: {users_with_notifs}/{total_students}")

    # AI recommendations
    cur.execute('SELECT COUNT(*) FROM ai_recommendations')
    print(f"AI Recommendations: {cur.fetchone()[0]}")

    # Total counts
    cur.execute('SELECT COUNT(*) FROM orders')
    print(f"Total Orders: {cur.fetchone()[0]}")
    cur.execute('SELECT COUNT(*) FROM notifications')
    print(f"Total Notifications: {cur.fetchone()[0]}")
    cur.execute('SELECT COUNT(*) FROM order_items')
    print(f"Order Items: {cur.fetchone()[0]}")

    print("="*60)

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        print("Completing demo data for all users...")
        add_orders_for_all_users(conn)
        add_notifications_for_all(conn)
        # AI recommendations are computed dynamically by the analytics service
        create_final_summary(conn)
        print("\nDemo data completion finished!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
