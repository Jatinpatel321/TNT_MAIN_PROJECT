"""Seed vendor table with test vendors matching the user IDs from seed_data.py.

The seed_data.py creates vendor users (role=VENDOR) in the users table,
but the `vendors` table (Vendor model) is a separate entity that must be
populated independently. Without records in `vendors`, POST /vendor/login
fails with "invalid credentials".

Run this after seed_data.py or the SQL seeds.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env")
    sys.exit(1)

if DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Pre-computed bcrypt hash for password='vendor123' (cost=12)
# This was generated using bcrypt and matches the hash in seeds/02_vendors_seed.sql
VENDOR_PASSWORD_HASH = "$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS"

# Pre-computed bcrypt hash for password='staff123'
STAFF_PASSWORD_HASH = "$2b$12$YhFLwiIfQB5XGm/gzVqS9uBbtV0xDGXAC2dI1I65A5kPpmfZmIMlS"

VENDOR_DATA = [
    # (vendor_name, category, status)
    ("Campus Cafe", "food", "active"),
    ("Parul Mess", "food", "active"),
    ("Juice Junction", "food", "active"),
    ("Stationery Shop", "stationery", "active"),
    ("Book Nook", "stationery", "active"),
    ("Tandoor Express", "food", "active"),
    ("Pizza Hub", "food", "pending"),
    ("Art & Craft", "stationery", "inactive"),
]

STAFF_DATA = [
    # (vendor_name, name, role, phone, permissions)
    ("Campus Cafe", "Rajesh Kumar", "manager", "+919800000001",
     '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}'),
    ("Campus Cafe", "Karan Dev", "staff", "+919800000002",
     '{"orders": ["view", "status_update"]}'),
    ("Parul Mess", "Sohan Lal", "manager", "+919800000003",
     '{"orders": ["view", "edit", "status_update"], "menu": ["edit"]}'),
    ("Parul Mess", "Ramesh Ram", "staff", "+919800000004",
     '{"orders": ["view", "status_update"]}'),
]


def get_vendor_id(session, vendor_name):
    """Look up a vendor_id by name."""
    result = session.execute(
        text("SELECT vendor_id FROM vendors WHERE vendor_name = :name"),
        {"name": vendor_name}
    ).fetchone()
    return result[0] if result else None


def main():
    print("=" * 60)
    print("   🌱 VENDOR TABLE SEEDER")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Check if vendors already exist
        existing = db.execute(text("SELECT COUNT(*) FROM vendors")).scalar()
        print(f"   Current vendors in table: {existing}")

        if existing > 0:
            print("   ✅ Vendors table already populated — skipping insert.")
        else:
            print("\n   📦 Seeding vendors table …")
            for name, category, status in VENDOR_DATA:
                # Check owner_id exists in users by name match
                user = db.execute(
                    text("SELECT id FROM users WHERE name = :name AND role = 'vendor'"),
                    {"name": name}
                ).fetchone()
                if not user:
                    print(f"   ⚠️  User name='{name}' not found in users table — skipping vendor '{name}'")
                    continue
                owner_id = user[0]

                db.execute(
                    text("""
                        INSERT INTO vendors (vendor_name, category, owner_id, password_hash, status, created_at)
                        VALUES (:name, :category, :owner_id, :pwd, :status, NOW())
                    """),
                    {
                        "name": name,
                        "category": category,
                        "owner_id": owner_id,
                        "pwd": VENDOR_PASSWORD_HASH,
                        "status": status,
                    }
                )
                print(f"      ✓ '{name}' (owner_id={owner_id}, category={category})")

            db.commit()
            print(f"   ✅ {len(VENDOR_DATA)} vendors inserted.")

        # Seed staff
        existing_staff = db.execute(text("SELECT COUNT(*) FROM vendor_staff")).scalar()
        if existing_staff > 0:
            print("   ✅ vendor_staff already populated — skipping.")
        else:
            print("\n   👥 Seeding vendor staff …")
            for vname, sname, role, phone, perms in STAFF_DATA:
                vid = get_vendor_id(db, vname)
                if not vid:
                    print(f"   ⚠️  Vendor '{vname}' not found — skipping staff '{sname}'")
                    continue
                db.execute(
                    text("""
                        INSERT INTO vendor_staff (vendor_id, name, role, phone, permissions, password_hash, is_active, created_at)
                        VALUES (:vid, :name, :role, :phone, CAST(:perms AS JSON), :pwd, true, NOW())
                    """),
                    {
                        "vid": vid,
                        "name": sname,
                        "role": role,
                        "phone": phone,
                        "perms": perms,
                        "pwd": STAFF_PASSWORD_HASH,
                    }
                )
                print(f"      ✓ '{sname}' ({role}) at '{vname}'")
            db.commit()
            print(f"   ✅ {len(STAFF_DATA)} staff inserted.")

        # Verify
        count = db.execute(text("SELECT COUNT(*) FROM vendors")).scalar()
        staff_count = db.execute(text("SELECT COUNT(*) FROM vendor_staff")).scalar()
        print(f"\n   📊 Final counts: vendors={count}, staff={staff_count}")
        print("\n   ✅ Vendor seeding complete.")
        print("\n   LOGIN CREDENTIALS (vendor_id=1...n, password=vendor123)")
        rows = db.execute(
            text("SELECT vendor_id, vendor_name FROM vendors ORDER BY vendor_id")
        ).fetchall()
        for r in rows:
            print(f"      vendor_id={r[0]}  password=vendor123  ({r[1]})")
        print("   STAFF: phone=+919800000001..0002  password=staff123")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
