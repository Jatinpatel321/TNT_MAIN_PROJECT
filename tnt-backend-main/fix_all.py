"""
Fix remaining issues with 9999999999 admin - need to delete STUDENT duplicate first.
"""
import sys, os
BACKEND_DIR = r"C:\finalyear-main-main\tnt-backend-main"
sys.path.insert(0, BACKEND_DIR)
os.chdir(BACKEND_DIR)
from sqlalchemy import text
from app.database.session import engine

print("Fixing 9999999999 admin...")
conn = engine.connect()
conn = conn.execution_options(isolation_level="AUTOCOMMIT")

try:
    # Check current state
    print("\nCurrent state for 9999999999:")
    rows = conn.execute(text(
        "SELECT id, phone, role::text, name FROM users WHERE phone LIKE '%9999%'"
    )).fetchall()
    for r in rows:
        print(f"  id={r[0]} phone='{r[1]}' role='{r[2]}' name='{r[3]}'")

    # Step 1: Delete the STUDENT duplicate (id=24) that has '+919999999999'
    conn.execute(text("DELETE FROM users WHERE id = 24"))
    print("\nDeleted STUDENT duplicate id=24")

    # Step 2: Now update admin (id=25) to '+919999999999'
    conn.execute(text(
        "UPDATE users SET phone = '+919999999999' WHERE id = 25"
    ))
    print("Updated admin id=25 phone to '+919999999999'")

    # Verify final state
    print("\nFinal state:")
    rows = conn.execute(text(
        "SELECT id, phone, role::text, name, is_active FROM users WHERE phone LIKE '%9999%'"
    )).fetchall()
    for r in rows:
        print(f"  id={r[0]} phone='{r[1]}' role='{r[2]}' name='{r[3]}' active={r[4]}")

    # Full admin check
    print("\nAll admins:")
    rows = conn.execute(text(
        "SELECT id, phone, role::text, name, is_active FROM users "
        "WHERE LOWER(role::text) IN ('admin', 'super_admin') ORDER BY id"
    )).fetchall()
    for r in rows:
        print(f"  id={r[0]} phone='{r[1]}' role='{r[2]}' name='{r[3]}' active={r[4]}")

    print("\n✓ DONE")

finally:
    conn.close()
