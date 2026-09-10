import app.database.init_db
from app.database.session import SessionLocal
from app.modules.vendors.model import Vendor
from app.modules.menu.model import MenuItem
from app.modules.users.model import User

db = SessionLocal()
vendors = db.query(Vendor).all()
print(f"=== TOTAL VENDORS: {len(vendors)} ===")
for v in vendors:
    print(f"ID={v.id} | Name={v.name} | Type={v.vendor_type} | Active={v.is_active} | Img={getattr(v, 'image_url', None)}")

items = db.query(MenuItem).all()
print(f"\n=== TOTAL MENU ITEMS: {len(items)} ===")
for i in items[:25]:
    print(f"ID={i.id} | VendorID={i.vendor_id} | Name={i.name} | Price={i.price} | Avail={i.is_available} | Category={getattr(i, 'category', None)} | Img={getattr(i, 'image_url', None)}")

users = db.query(User).all()
print(f"\n=== TOTAL USERS: {len(users)} ===")
for u in users[:5]:
    print(f"ID={u.id} | Name={u.name} | Phone={u.phone} | Role={u.role}")

db.close()
