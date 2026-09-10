"""Update slot dates to today so they appear in the user app."""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(".env")

engine = create_engine(os.getenv("DATABASE_URL"))

now = datetime.utcnow()
today = now.replace(hour=0, minute=0, second=0, microsecond=0)

with engine.connect() as conn:
    existing = conn.execute(text("SELECT id, start_time, end_time FROM slots ORDER BY id")).fetchall()
    print(f"Updating {len(existing)} slots to today ({today.date()})")
    for slot in existing:
        old_start = slot[1]
        old_end = slot[2]
        hour_start = old_start.hour if old_start else 8
        hour_end = old_end.hour if old_end else 9
        new_start = today.replace(hour=hour_start, minute=0)
        new_end = today.replace(hour=hour_end, minute=0)
        if new_end <= new_start:
            new_end = new_start + timedelta(hours=1)
        conn.execute(
            text("UPDATE slots SET start_time = :s, end_time = :e WHERE id = :id"),
            {"s": new_start, "e": new_end, "id": slot[0]},
        )
    conn.commit()
    print("Done!")

    result = conn.execute(text("SELECT id, vendor_id, start_time, end_time FROM slots LIMIT 8")).fetchall()
    for r in result:
        print(f"  slot {r[0]}: vendor={r[1]}, {r[2]} → {r[3]}")
