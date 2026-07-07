#!/usr/bin/env python3
"""Add stationery services and more orders to meet demo requirements."""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = 'tnt_dev.db'

def utcnow():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def add_stationery_services(conn):
    """Add stationery services to vendors without items."""
    cur = conn.cursor()

    # Get stationery vendor IDs
    cur.execute("SELECT id, name FROM users WHERE role = 'VENDOR' AND vendor_type = 'stationery'")
    vendors = cur.fetchall()

    services = {
        'Xerox Point': [
            ('B&W Xerox (per page)', 'Black & white photocopy', 5, 'https://cdn.tapntake.app/stationery/bw_xerox.jpg'),
            ('Color Xerox (per page)', 'Full color photocopy', 15, 'https://cdn.tapntake.app/stationery/color_xerox.jpg'),
            ('Double-sided Xerox', 'Both sides printing', 8, 'https://cdn.tapntake.app/stationery/double_xerox.jpg'),
            ('A3 Xerox', 'Large format copy', 25, 'https://cdn.tapntake.app/stationery/a3_xerox.jpg'),
            ('ID Card Lamination', 'PVC card lamination', 50, 'https://cdn.tapntake.app/stationery/lamination.jpg'),
            ('Document Binding', 'Spiral binding service', 40, 'https://cdn.tapntake.app/stationery/binding.jpg'),
            ('Scan to PDF', 'Document scanning service', 10, 'https://cdn.tapntake.app/stationery/scanning.jpg'),
        ],
        'Print Hub': [
            ('B&W Print (per page)', 'Black & white laser print', 8, 'https://cdn.tapntake.app/stationery/bw_print.jpg'),
            ('Color Print (per page)', 'Full color inkjet print', 20, 'https://cdn.tapntake.app/stationery/color_print.jpg'),
            ('Photo Print 4x6', 'Standard photo print', 30, 'https://cdn.tapntake.app/stationery/photo_print.jpg'),
            ('Poster Print A3', 'Large poster printing', 80, 'https://cdn.tapntake.app/stationery/poster.jpg'),
            ('Vinyl Sticker', 'Custom sticker print', 100, 'https://cdn.tapntake.app/stationery/sticker.jpg'),
            ('Visiting Cards (100)', 'Business card printing', 150, 'https://cdn.tapntake.app/stationery/visiting_cards.jpg'),
            ('Thesis Binding', 'Hardcover thesis binding', 200, 'https://cdn.tapntake.app/stationery/thesis.jpg'),
            ('Soft Cover Binding', 'Soft cover document binding', 80, 'https://cdn.tapntake.app/stationery/soft_bind.jpg'),
        ],
        'Campus Stationery': [
            ('Notebook A5', '100 pages ruled notebook', 60, 'https://cdn.tapntake.app/stationery/notebook.jpg'),
            ('Pen Set (5)', 'Ballpoint pen pack', 40, 'https://cdn.tapntake.app/stationery/pen_set.jpg'),
            ('Highlighter Pack', '6-color highlighter set', 35, 'https://cdn.tapntake.app/stationery/highlighter.jpg'),
            ('A4 Sheet Bundle', '500 sheets bundle', 120, 'https://cdn.tapntake.app/stationery/a4_sheets.jpg'),
        ]
    }

    added = 0
    for vid, vname in vendors:
        if vname in services:
            for name, desc, price, img in services[vname]:
                cur.execute('SELECT id FROM menu_items WHERE vendor_id = ? AND name = ?', (vid, name))
                if cur.fetchone():
                    continue
                cur.execute('''
                    INSERT INTO menu_items (vendor_id, name, description, price, image_url, is_available)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (vid, name, desc, price * 100, img))  # Convert to cents
                added += 1

    conn.commit()
    print(f"Added {added} stationery services")

def add_more_orders(conn):
    """Add more orders to reach 30 total."""
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM orders')
    current = cur.fetchone()[0]

    if current >= 30:
        print(f"Already have {current} orders")
        return

    needed = 30 - current
    print(f"Adding {needed} more orders...")

    # Get user IDs
    cur.execute("SELECT id FROM users WHERE role = 'STUDENT' ORDER BY RANDOM()")
    user_ids = [r[0] for r in cur.fetchall()]

    # Get vendor IDs with slots
    cur.execute("SELECT id, vendor_id FROM slots ORDER BY RANDOM()")
    slots = cur.fetchall()

    # Get menu items
    cur.execute("SELECT id, vendor_id, price FROM menu_items ORDER BY RANDOM()")
    menu_items = cur.fetchall()

    if not slots or not menu_items:
        print("No slots or menu items found!")
        return

    statuses = ['picked', 'ready', 'confirmed', 'preparing']
    now = datetime.utcnow()

    added = 0
    for i in range(needed):
        if i >= len(user_ids):
            break

        slot = slots[i % len(slots)]
        slot_id, vid = slot[0], slot[1]

        # Find items for this vendor
        vendor_items = [m for m in menu_items if m[1] == vid][:2]
        if len(vendor_items) < 2:
            vendor_items = menu_items[:2]

        status = statuses[i % len(statuses)]
        days_ago = i % 7
        eta = [15, 20, 25, 18][i % 4]
        created_at = (now - timedelta(days=days_ago, hours=i)).strftime('%Y-%m-%d %H:%M:%S')
        qr_code = f'TNT-EXTRA-{added:03d}'
        total = sum(m[2] for m in vendor_items[:2])

        cur.execute('''
            INSERT INTO orders (user_id, vendor_id, slot_id, status, created_at, eta_minutes, qr_code, total_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_ids[i], vid, slot_id, status, created_at, eta, qr_code, total))

        order_id = cur.lastrowid

        for mid, _, price in vendor_items[:2]:
            cur.execute('''
                INSERT INTO order_items (order_id, menu_item_id, quantity, price_at_time)
                VALUES (?, ?, 1, ?)
            ''', (order_id, mid, price))

        added += 1

    conn.commit()
    print(f"Added {added} orders")

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        add_stationery_services(conn)
        add_more_orders(conn)

        print("\n=== Final Summary ===")
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM menu_items")
        print(f"Menu items (food + stationery): {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM orders")
        print(f"Orders: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM notifications")
        print(f"Notifications: {cur.fetchone()[0]}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
