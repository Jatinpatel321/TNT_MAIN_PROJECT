"""
Setup script: Creates all DB tables and admin user in one shot.
Run: .\venv\Scripts\python.exe scripts\setup_db.py
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.database.session import engine, SessionLocal
from app.database.base import Base

# Register all models
import app.modules.users.model
import app.modules.menu.model
import app.modules.slots.model
import app.modules.orders.model
import app.modules.orders.history_model
import app.modules.payments.model
import app.modules.rewards.model
import app.modules.ledger.model
import app.modules.notifications.model
import app.modules.stationery.job_model
import app.modules.stationery.service_model
import app.modules.group_cart.model

try:
    import app.modules.feedback.model
except Exception as e:
    print("feedback model skip:", e)

try:
    import app.modules.complaints.model
except Exception as e:
    print("complaints model skip:", e)

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("All tables created!")

# Create admin user
from app.modules.users.model import User, UserRole

phone = sys.argv[1] if len(sys.argv) > 1 else "9999999999"
name  = sys.argv[2] if len(sys.argv) > 2 else "Super Admin"

db = SessionLocal()
try:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        user.role = UserRole.ADMIN
        user.is_active = True
        user.is_approved = True
        user.name = name
        db.commit()
        print("Updated existing user -> role=admin  phone=" + phone)
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
        print("Admin user created!  id=" + str(user.id) + "  phone=" + phone)
finally:
    db.close()

print("")
print("=== HOW TO LOGIN ===")
print("1. Open http://localhost:5173 (admin frontend)")
print("2. Enter phone: " + phone)
print("3. Click Send OTP")
print("4. OTP will appear in the BACKEND terminal output (SMS_ENABLED=false)")
print("5. Enter the OTP and login")
print("====================")
