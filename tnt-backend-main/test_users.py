import sys

sys.path.insert(0, '.')

from app.database.session import SessionLocal
from app.modules.users.model import User, UserRole


def add_test_users():
    db = SessionLocal()
    try:
        # Add student
        student = User(
            phone="1111111111",
            name="Test Student",
            role=UserRole.STUDENT,
            university_id="STU001"
        )
        db.add(student)

        # Add vendor
        vendor = User(
            phone="2222222222",
            name="Test Vendor",
            role=UserRole.VENDOR
        )
        db.add(vendor)

        db.commit()
        print("Test users added successfully")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_users()
