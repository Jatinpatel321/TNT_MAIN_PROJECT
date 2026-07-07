"""Diagnose admin login issue - phone number format + role issues."""
import sys, os

BACKEND_DIR = r"C:\finalyear-main-main\tnt-backend-main"
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)

from app.database.session import SessionLocal
from app.modules.users.model import User, UserRole

db = SessionLocal()
try:
    print("=== All users with admin/super_admin roles ===")
    from sqlalchemy import text

    # Raw SQL to check actual stored values
    result = db.execute(text("SELECT id, phone, role::text, name, is_active, is_approved FROM users WHERE role::text LIKE '%admin%' OR role::text LIKE '%ADMIN%'"))
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"  id={row[0]} phone='{row[1]}' role_raw='{row[2]}' name='{row[3]}' active={row[4]} approved={row[5]}")
    else:
        print("  No admin users found!")

    # Look for users by phone patterns
    print("\n=== Looking for phone matches ===")
    for phone_pattern in ['%9999%', '%9727%', '%9727804515%']:
        result = db.execute(text(f"SELECT id, phone, role::text, name, is_active FROM users WHERE phone LIKE '{phone_pattern}'"))
        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"  pattern '{phone_pattern}' -> id={row[0]} phone='{row[1]}' role='{row[2]}' name='{row[3]}' active={row[4]}")
        else:
            print(f"  pattern '{phone_pattern}' -> NOT FOUND")

    # Check ALL users' roles
    print("\n=== All role values in DB ===")
    result = db.execute(text("SELECT DISTINCT role::text FROM users ORDER BY role"))
    for row in result:
        raw_val = row[0]
        try:
            enum_val = UserRole(raw_val)
            status = f"OK (maps to UserRole.{enum_val.name})"
        except ValueError:
            status = f"INVALID - not a valid UserRole value"
        print(f"  '{raw_val}' -> {status}")

    # Count users
    result = db.execute(text("SELECT COUNT(*) FROM users"))
    print(f"\nTotal users: {result.scalar()}")

finally:
    db.close()

print("\n=== JWT Settings ===")
from app.core.security import SECRET_KEY, ALGORITHM
print(f"  SECRET_KEY: {SECRET_KEY!r}")
print(f"  ALGORITHM: {ALGORITHM!r}")
print(f"  expects role in JWT to be the UserRole.value string")

print("\n=== PHONE NORMALIZATION CHECK ===")
print("Frontend sends: +919999999999 to /v1/auth/send-otp and /v1/auth/verify-otp")
print("Backend queries for: phone == '+919999999999'")
print("If DB has: 9999999999 -> no match -> AUTO-REGISTER as STUDENT")
print("JWT role = 'student' -> frontend check rejects: 'Access denied - Admin only portal'")
print()
print("If DB has: +919999999999 -> match -> role from DB used in JWT")
print()
print("ROOT CAUSES:")
print("1. Phone mismatch: frontend sends '+91' prefix, DB may store without it")
print("2. No admin user in DB for the phone being used")
print("3. If phone matches but role is not 'admin'/'super_admin' -> frontend denies")
