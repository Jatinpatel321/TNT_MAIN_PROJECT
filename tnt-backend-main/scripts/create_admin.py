"""
Seed script: Create an admin user for the TNT Admin web dashboard.

Usage:
    python scripts/create_admin.py [phone] [name]

Defaults:
    phone = 9999999999
    name  = Super Admin

The script will:
1. Connect to the DB using DATABASE_URL from .env
2. Create user if not exists
3. Set role = admin, is_active = True, is_approved = True
"""

import sys
import os
from pathlib import Path

# ── ensure project root is on PYTHONPATH ────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database.session import SessionLocal
from app.modules.users.model import User, UserRole


def create_admin(phone: str, name: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.phone == phone).first()
        if user:
            user.role = UserRole.ADMIN
            user.is_active = True
            user.is_approved = True
            user.name = name
            db.commit()
            print(f"✅ Updated existing user {phone} → role=admin")
        else:
            user = User(
                phone=phone,
                name=name,
                role=UserRole.ADMIN,
                is_active=True,
                is_approved=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created admin user: id={user.id}  phone={phone}  name={name}")

        print()
        print("─── Login Instructions ───────────────────────────────────────")
        print(f"  1. Open http://localhost:5173")
        print(f"  2. Enter phone: {phone}")
        print(f"  3. Click 'Send OTP'")
        print(f"  4. The OTP will be shown in the API response (SMS_ENABLED=false)")
        print(f"     Watch the backend terminal for: 'otp': '...' in the JSON")
        print("──────────────────────────────────────────────────────────────")
    finally:
        db.close()


if __name__ == "__main__":
    phone = sys.argv[1] if len(sys.argv) > 1 else "9999999999"
    name  = sys.argv[2] if len(sys.argv) > 2 else "Super Admin"
    create_admin(phone, name)
