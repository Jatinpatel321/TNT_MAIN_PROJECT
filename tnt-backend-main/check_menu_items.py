import app.database.init_db
from app.database.session import SessionLocal
from app.modules.menu.model import MenuItem
from app.modules.users.model import User

db = SessionLocal()
items = db.query(MenuItem).all()
print(f"Total menu items: {len(items)}")
items_with_img = [i for i in items if i.image_url]
print(f"Items with image_url: {len(items_with_img)}")
print(f"Items with None image_url: {len(items) - len(items_with_img)}")

for i in items[:10]:
    print(f"ID={i.id} Name='{i.name}' image_url='{i.image_url}'")

vendors = db.query(User).filter(User.role == "vendor").all()
print(f"\nTotal vendor users: {len(vendors)}")
for v in vendors:
    print(f"ID={v.id} Name='{v.name}' is_approved={v.is_approved}")

db.close()
