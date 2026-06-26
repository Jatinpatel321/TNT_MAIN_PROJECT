import os
import sys
import random
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Ensure app package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import all models to register SQLAlchemy metadata
import app.database.init_db
from app.database.session import SessionLocal, engine
from app.core.redis import redis_client
import redis

# Model imports
from app.modules.users.model import User, UserRole
from app.modules.orders.model import Order, OrderItem, OrderStatus
from app.modules.payments.model import Payment, PaymentStatus
from app.modules.menu.model import MenuItem
from app.modules.slots.model import Slot
from app.modules.auditlog.model import AuditLog
from app.modules.fraud.model import FraudAlert
from app.modules.backup.models import BackupRecord, BackupType, BackupStatus
from app.modules.feedback.model import Feedback, VendorReview
from app.modules.recommendations.models import UserBehaviour

# Configuration
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("[-] DATABASE_URL not found in .env")
    sys.exit(1)

# Helper lists
IPS = [
    "192.168.1.5", "192.168.1.12", "192.168.1.84", "10.0.0.15", "10.0.0.22",
    "172.16.2.45", "172.16.5.90", "203.0.113.195", "198.51.100.12", "198.51.100.55"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

def ensure_orders(db, target_count=250):
    """Ensures at least `target_count` orders exist for realistic relational seeding."""
    current_count = db.query(Order).count()
    if current_count >= target_count:
        print(f"   [+] Database already has {current_count} orders.")
        return db.query(Order).all()

    print(f"   [*] Database has only {current_count} orders. Generating up to {target_count} orders...")
    students = db.query(User).filter(User.role.in_([UserRole.STUDENT, UserRole.FACULTY])).all()
    vendors = db.query(User).filter(User.role == UserRole.VENDOR).all()
    menu_items = db.query(MenuItem).all()
    slots = db.query(Slot).all()

    if not students or not vendors or not menu_items or not slots:
        print("   [!] Cannot generate extra orders: missing core users, vendors, menu items, or slots.")
        return db.query(Order).all()

    status_pool = [
        OrderStatus.PICKED, OrderStatus.READY, OrderStatus.CONFIRMED,
        OrderStatus.PREPARING, OrderStatus.COMPLETED, OrderStatus.READY_FOR_PICKUP
    ]

    new_orders_count = target_count - current_count
    orders_added = 0
    for _ in range(new_orders_count):
        user = random.choice(students)
        slot = random.choice(slots)
        vendor_id = slot.vendor_id
        status = random.choice(status_pool)
        created = datetime.utcnow() - timedelta(days=random.uniform(0, 30))

        vendor_items = [m for m in menu_items if m.vendor_id == vendor_id]
        if not vendor_items:
            continue

        num_items = random.randint(1, 3)
        chosen_items = random.sample(vendor_items, min(num_items, len(vendor_items)))
        total_amount = sum(item.price * random.randint(1, 2) for item in chosen_items)

        order = Order(
            user_id=user.id,
            vendor_id=vendor_id,
            slot_id=slot.id,
            status=status,
            total_amount=total_amount,
            created_at=created,
            fraud_flag=random.random() < 0.05
        )
        db.add(order)
        db.flush()

        for item in chosen_items:
            oi = OrderItem(
                order_id=order.id,
                menu_item_id=item.id,
                quantity=random.randint(1, 2),
                price_at_time=item.price
            )
            db.add(oi)

        payment = Payment(
            order_id=order.id,
            amount=total_amount,
            status=PaymentStatus.SUCCESS if status != OrderStatus.CANCELLED else PaymentStatus.FAILED,
            razorpay_order_id=f"order_{random.randint(10000000, 99999999)}",
            created_at=created + timedelta(minutes=random.randint(1, 5))
        )
        db.add(payment)
        orders_added += 1

    db.commit()
    print(f"   [+] Generated {orders_added} extra orders.")
    return db.query(Order).all()

def seed_audit_logs(db, admins, vendors, students_faculty):
    """Seed 500 audit logs representing administrator/operator activities."""
    print("[-] Clearing old Audit Logs...")
    db.query(AuditLog).delete()
    db.commit()

    print("[*] Seeding 500 Audit Logs...")
    logs = []
    
    actions = [
        ("auth.login", "auth", "user", "Login successful"),
        ("auth.login_failed", "auth", "user", "Login failed - incorrect credentials"),
        ("user.role_changed", "user", "user", "User role elevated from student to faculty"),
        ("user.blocked", "user", "user", "User account suspended due to terms violation"),
        ("vendor.approved", "vendor", "vendor", "Vendor registration approved"),
        ("vendor.suspended", "vendor", "vendor", "Vendor suspended due to hygiene issues"),
        ("vendor.staff_permissions_updated", "vendor", "vendor", "Vendor staff dashboard permissions updated"),
        ("policy.updated", "policy", "policy", "Peak hour cancellation window policy updated"),
        ("settings.changed", "settings", "settings", "System maintenance mode status updated")
    ]
    
    # Pre-select some entities to reference
    admin_pool = admins if admins else students_faculty
    
    for i in range(500):
        actor = random.choice(admin_pool)
        action_tuple = random.choice(actions)
        action_name, category, entity_type, desc_info = action_tuple
        
        target_entity_id = None
        if entity_type == "user":
            target_entity_id = str(random.choice(students_faculty).id)
        elif entity_type == "vendor" and vendors:
            target_entity_id = str(random.choice(vendors).id)
        elif entity_type == "policy":
            target_entity_id = "cancellation_policy"
        elif entity_type == "settings":
            target_entity_id = "general_settings"
            
        before = None
        after = None
        if action_name == "user.role_changed":
            before = {"role": "student"}
            after = {"role": "faculty"}
        elif action_name == "vendor.suspended":
            before = {"is_active": True}
            after = {"is_active": False}
        elif action_name == "policy.updated":
            before = {"cancellation_window_mins": 5}
            after = {"cancellation_window_mins": 10}
        elif action_name == "settings.changed":
            before = {"maintenance_mode": False}
            after = {"maintenance_mode": True}

        log = AuditLog(
            actor_id=actor.id,
            actor_role=actor.role.value if actor.role else "admin",
            action=action_name,
            action_category=category,
            entity_type=entity_type,
            entity_id=target_entity_id,
            before_state=before,
            after_state=after,
            meta={"details": desc_info},
            ip_address=random.choice(IPS),
            user_agent=random.choice(USER_AGENTS),
            created_at=datetime.utcnow() - timedelta(days=random.uniform(0, 30))
        )
        logs.append(log)
        
    db.add_all(logs)
    db.commit()
    print("   [+] 500 Audit Logs seeded.")

def seed_fraud_alerts(db, students_faculty, vendors, orders):
    """Seed 200 Fraud Alerts indicating transactional/operational security anomalies."""
    print("[-] Clearing old Fraud Alerts...")
    db.query(FraudAlert).delete()
    db.commit()

    print("[*] Seeding 200 Fraud Cases...")
    alerts = []
    
    alert_templates = [
        ("mismatched_location", "Order picked up from IP far from user home department", "medium"),
        ("rapid_ordering", "Multiple orders checked out within 5 seconds", "high"),
        ("unusual_amount", "Single checkout transaction exceeds threshold limits", "low"),
        ("velocity_spike", "Too many checkout attempts from same IP address", "critical"),
        ("jwt_abusive_access", "Session JWT tokens replayed from multiple locations", "critical")
    ]
    
    statuses = ["pending", "resolved", "false_positive"]
    status_weights = [0.35, 0.50, 0.15] # ~70 pending, ~100 resolved, ~30 false positive
    
    resolution_notes_pool = [
        "Verified with user via call. Customer confirmed transactions.",
        "System auto-blocked IP address. User password forced reset.",
        "False positive: User verified department change during mid-sem.",
        "Confirmed abuse: Order voided and refund initiated. User suspended.",
        "Closed: Flagged due to network switching on university WiFi."
    ]

    for i in range(200):
        user = random.choice(students_faculty)
        vendor = random.choice(vendors) if vendors else None
        order = random.choice(orders) if orders else None
        
        tpl = random.choice(alert_templates)
        alert_type, description, default_severity = tpl
        
        status = random.choices(statuses, weights=status_weights)[0]
        score = random.uniform(0.5, 0.99)
        
        severity = default_severity
        if score > 0.85:
            severity = "critical"
        elif score > 0.70:
            severity = "high"
            
        created = datetime.utcnow() - timedelta(days=random.uniform(0, 30))
        updated = created
        res_notes = None
        
        if status != "pending":
            updated = created + timedelta(hours=random.uniform(1, 48))
            res_notes = random.choice(resolution_notes_pool)
            
        alert = FraudAlert(
            user_id=user.id,
            vendor_id=vendor.id if vendor else None,
            order_id=order.id if order else None,
            alert_type=alert_type,
            severity=severity,
            score=round(score, 2),
            description=description,
            status=status,
            resolution_notes=res_notes,
            created_at=created,
            updated_at=updated
        )
        alerts.append(alert)
        
    db.add_all(alerts)
    db.commit()
    print("   [+] 200 Fraud Cases seeded.")

def seed_backups(db):
    """Seed 50 database backup history records."""
    print("[-] Clearing old Backup Records...")
    db.query(BackupRecord).delete()
    db.commit()

    print("[*] Seeding 50 Backup Records...")
    backups = []
    
    base_time = datetime.utcnow() - timedelta(days=50)
    
    # 45 success, 5 failed
    status_pool = ["success"] * 45 + ["failed"] * 5
    random.shuffle(status_pool)
    
    for i in range(50):
        status = status_pool[i]
        created = base_time + timedelta(days=i) + timedelta(hours=random.uniform(-2, 2))
        
        # Decide backup type based on day of week / index
        if i % 7 == 0:
            backup_type = BackupType.weekly.value
            notes = "Scheduled weekly full database snapshot to AWS S3"
        elif i % 15 == 5:
            backup_type = BackupType.manual.value
            notes = f"Manual backup triggered by admin before schema revision {20260600 + i}"
        else:
            backup_type = BackupType.daily.value
            notes = "Automated daily incremental backup to regional store"
            
        completed = None
        duration = None
        error_msg = None
        size = None
        checksum = None
        rows = None
        
        if status == "success":
            duration = random.randint(3, 12)
            completed = created + timedelta(seconds=duration)
            size = random.randint(15 * 1024 * 1024, 65 * 1024 * 1024) # 15MB - 65MB
            checksum = "".join(random.choices("0123456789abcdef", k=64))
            rows = random.randint(5000, 35000)
        else:
            duration = random.randint(1, 4)
            completed = created + timedelta(seconds=duration)
            error_msg = random.choice([
                "pg_dump: error: connection to database failed: Connection timed out",
                "pg_dump: error: write failed: No space left on device",
                "Backup lock acquisition timeout: Database currently under heavy load"
            ])
            
        filename = f"tnt_backup_{created.strftime('%Y%m%d_%H%M%S')}_{backup_type}.sql.gz"
        
        backup = BackupRecord(
            filename=filename,
            backup_type=backup_type,
            status=status,
            size_bytes=size,
            checksum_sha256=checksum,
            database_name="tnt",
            tables_count=18,
            rows_exported=rows,
            duration_seconds=duration,
            error_message=error_msg,
            notes=notes,
            created_at=created,
            completed_at=completed
        )
        backups.append(backup)
        
    db.add_all(backups)
    db.commit()
    print("   [+] 50 Backup Records seeded.")

def seed_vendor_performance(db, students_faculty, vendors, orders):
    """Seed 100 Feedback and 100 Vendor Review entries with realistic ratings distributions."""
    print("[-] Clearing old Feedback and Reviews...")
    db.query(Feedback).delete()
    db.query(VendorReview).delete()
    db.commit()

    print("[*] Seeding 100 Feedback & 100 Vendor Reviews...")
    
    feedbacks = []
    reviews = []
    
    comments_good = [
        "Exceptional service, food was hot and delicious!",
        "Very fast preparation. Picked up in seconds.",
        "Best canteen in Parul University. Love the samosas.",
        "Quality is always high, behavior was polite.",
        "My go-to place for tea and stationery items."
    ]
    
    comments_avg = [
        "Food taste was okay but slightly delayed.",
        "Quantity was a bit small, but tastes nice.",
        "Average behavior, normal preparation time.",
        "Standard campus food. Reasonable prices."
    ]
    
    comments_poor = [
        "Ordered coffee but got cold tea instead.",
        "Staff was very rude and made me wait 15 minutes.",
        "Hygiene levels look terrible. Food was half-cooked.",
        "Incorrect items delivered. Totally disappointed."
    ]
    
    for i in range(100):
        order = random.choice(orders)
        user = random.choice(students_faculty)
        vendor = random.choice(vendors)
        
        # Distribute ratings based on vendor profile
        # E.g. Vendor IDs 9 and 10 are excellent, Vendor 11 is poor, others average
        if vendor.id in [9, 10]:
            r_overall = random.randint(4, 5)
            r_quality = random.randint(4, 5)
            r_time = random.randint(4, 5)
            r_behavior = random.randint(4, 5)
            comment = random.choice(comments_good)
        elif vendor.id == 11:
            r_overall = random.randint(1, 3)
            r_quality = random.randint(1, 2)
            r_time = random.randint(1, 3)
            r_behavior = random.randint(1, 2)
            comment = random.choice(comments_poor)
        else:
            r_overall = random.randint(3, 4)
            r_quality = random.randint(3, 4)
            r_time = random.randint(2, 4)
            r_behavior = random.randint(3, 5)
            comment = random.choice(comments_avg)
            
        fb = Feedback(
            order_id=order.id,
            user_id=user.id,
            vendor_id=vendor.id,
            overall_rating=r_overall,
            quality_rating=r_quality,
            time_rating=r_time,
            behavior_rating=r_behavior,
            comment=comment,
            created_at=datetime.utcnow() - timedelta(days=random.uniform(0, 30))
        )
        feedbacks.append(fb)

        # Generate Vendor Review
        rev_rating = r_overall
        rev_title = "Awesome!" if rev_rating >= 4 else "Average" if rev_rating == 3 else "Bad Experience"
        
        vr = VendorReview(
            vendor_id=vendor.id,
            user_id=user.id,
            order_id=order.id,
            rating=rev_rating,
            title=rev_title,
            review_text=comment,
            is_anonymous=random.random() < 0.25,
            created_at=datetime.utcnow() - timedelta(days=random.uniform(0, 30))
        )
        reviews.append(vr)
        
    db.add_all(feedbacks)
    db.add_all(reviews)
    db.commit()
    print("   [+] 100 Feedback and 100 Vendor Review records seeded.")

def seed_user_activity(db, students_faculty, vendors, orders):
    """Seed 100 user behaviour interaction logs."""
    print("[-] Clearing old User Behaviour logs...")
    db.query(UserBehaviour).delete()
    db.commit()

    print("[*] Seeding 100 User Activity records...")
    activities = []
    
    event_types = [
        ("page_view", 1.0, "vendor"),
        ("item_click", 2.0, "menu_item"),
        ("search", 1.5, "search"),
        ("category_view", 1.0, "category"),
        ("favourite", 4.0, "vendor"),
        ("order_placed", 5.0, "order")
    ]
    
    search_queries = ["samosa", "pen", "coffee", "notebook", "burger", "pizza", "pencil", "tea"]
    categories = ["food", "stationery", "beverages", "notebooks", "snacks"]
    screens = ["home", "menu", "search", "order_history", "profile"]
    referrers = ["direct", "home_banner", "search_results", "previous_orders"]
    
    menu_items = db.query(MenuItem).all()

    for i in range(100):
        user = random.choice(students_faculty)
        evt_type, weight, polymorphic_target = event_types[random.randint(0, len(event_types)-1)]
        
        v_id = None
        item_id = None
        ord_id = None
        cat = None
        s_query = None
        res_count = None
        
        if polymorphic_target == "vendor":
            v_id = random.choice(vendors).id if vendors else None
        elif polymorphic_target == "menu_item":
            item_id = random.choice(menu_items).id if menu_items else None
            v_id = random.choice(vendors).id if vendors else None
        elif polymorphic_target == "order":
            ord_id = random.choice(orders).id if orders else None
            v_id = random.choice(vendors).id if vendors else None
        elif polymorphic_target == "category":
            cat = random.choice(categories)
        elif polymorphic_target == "search":
            s_query = random.choice(search_queries)
            res_count = random.randint(0, 15)
            
        act = UserBehaviour(
            user_id=user.id,
            event_type=evt_type,
            vendor_id=v_id,
            menu_item_id=item_id,
            order_id=ord_id,
            category=cat,
            search_query=s_query,
            search_results_count=res_count,
            source_screen=random.choice(screens),
            duration_seconds=random.randint(2, 120),
            referrer=random.choice(referrers),
            weight=weight,
            created_at=datetime.utcnow() - timedelta(days=random.uniform(0, 30))
        )
        activities.append(act)
        
    db.add_all(activities)
    db.commit()
    print("   [+] 100 User Activity records seeded.")

def seed_redis_security_events():
    """Seed 100 security events and metric counters in Redis."""
    print("[-] Clearing and seeding Redis Security Events...")
    
    # Construct a RESP2 client for older version support
    r_client = redis.Redis(host="localhost", port=6379, decode_responses=True, protocol=2)
    
    try:
        # Clear existing keys
        r_client.delete("security:recent_events")
        
        # Clear metrics
        metric_keys = r_client.keys("security:metric:*")
        if metric_keys:
            r_client.delete(*metric_keys)
            
        print("   [+] Cleaned previous Redis security keys.")
    except Exception as e:
        print(f"   [!] Redis connection failed or key deletion failed: {e}. Attempting app client.")
        r_client = redis_client
        try:
            r_client.delete("security:recent_events")
        except Exception:
            pass

    # We generate: 40 jwt_failure, 40 rate_limit_violation, 15 api_abuse, 5 target_blocked = 100 events
    events = []
    current_time = time.time()
    
    # 1. 40 JWT Failures
    for i in range(40):
        events.append({
            "id": f"evt_jwt_{int(current_time * 1000) - i*10000}",
            "timestamp": current_time - i * 3600,
            "event_type": "jwt_failure",
            "severity": "high",
            "details": {
                "token_preview": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxN...",
                "reason": random.choice(["Signature verification failed", "Token has expired", "Invalid claims profile"])
            },
            "ip_address": random.choice(IPS),
            "user_id": None
        })

    # 2. 40 Rate Limit Violations
    for i in range(40):
        ip = random.choice(IPS)
        events.append({
            "id": f"evt_rl_{int(current_time * 1000) - i*10000 - 400000}",
            "timestamp": current_time - i * 1800,
            "event_type": "rate_limit_violation",
            "severity": "medium",
            "details": {
                "path": random.choice(["/v1/auth/login", "/v1/payments/webhook", "/v1/orders"]),
                "limit_key": f"ip:{ip}"
            },
            "ip_address": ip,
            "user_id": None
        })

    # 3. 15 API Abuses
    for i in range(15):
        events.append({
            "id": f"evt_abuse_{int(current_time * 1000) - i*10000 - 800000}",
            "timestamp": current_time - i * 7200,
            "event_type": "api_abuse",
            "severity": "critical",
            "details": {
                "path": "/v1/admin/users",
                "reason": "Mass scanning of student profiles detected via automation"
            },
            "ip_address": random.choice(IPS),
            "user_id": random.randint(1, 10)
        })

    # 4. 5 Target Blocked
    blocked_ips = ["198.51.100.99", "203.0.113.88", "198.51.100.11", "172.16.2.22", "192.168.1.199"]
    for i in range(5):
        events.append({
            "id": f"evt_block_{int(current_time * 1000) - i*10000 - 1200000}",
            "timestamp": current_time - i * 86400,
            "event_type": "target_blocked",
            "severity": "high",
            "details": {
                "target": blocked_ips[i],
                "reason": "Repeated API abuse & credential stuffing",
                "duration": 86400
            },
            "ip_address": blocked_ips[i],
            "user_id": None
        })
        
    # Sort events by timestamp ascending so when we LPUSH them, the newest ends up first
    events.sort(key=lambda x: x["timestamp"])

    try:
        # Push to Redis list
        for ev in events:
            r_client.lpush("security:recent_events", json.dumps(ev))
            
        r_client.ltrim("security:recent_events", 0, 99)

        # Set specific counter metrics (both singular & plural keys for safety)
        r_client.set("security:metric:jwt_failure:total", 40)
        r_client.set("security:metric:jwt_failures:total", 40)
        
        r_client.set("security:metric:rate_limit_violation:total", 40)
        r_client.set("security:metric:rate_limit_violations:total", 40)
        
        r_client.set("security:metric:api_abuse:total", 15)
        r_client.set("security:metric:target_blocked:total", 5)
        r_client.set("security:metric:total_events", 100)

        # Seed some blocked target hashes directly in Redis
        for ip in blocked_ips:
            r_client.setex(f"security:blocked:{ip}", 86400, "Repeated API abuse & credential stuffing")

        print("   [+] 100 Security Events and counters seeded in Redis.")
    except Exception as e:
        print(f"   [!] Could not insert events into Redis: {e}")

def seed_redis_health_history():
    """Seed 100 health metrics snapshots (KPI records) in Redis list `health:history`."""
    print("[-] Clearing and seeding Redis Health KPI History...")
    
    r_client = redis.Redis(host="localhost", port=6379, decode_responses=True, protocol=2)
    
    try:
        r_client.delete("health:history")
    except Exception:
        r_client = redis_client
        try:
            r_client.delete("health:history")
        except Exception:
            pass

    history = []
    now_ts = time.time()
    
    # Generate 100 snapshots, 15 minutes apart (~25 hours)
    for i in range(100, 0, -1):
        timestamp = now_ts - (i * 900)
        dt = datetime.utcfromtimestamp(timestamp)
        
        # Simulate slight variations throughout the day, e.g. spikes around lunch time
        hour = dt.hour
        is_peak = 12 <= hour <= 14 or 17 <= hour <= 19
        
        cpu = round(random.uniform(15.0, 45.0) if is_peak else random.uniform(4.0, 15.0), 1)
        mem = round(random.uniform(48.0, 52.0) if is_peak else random.uniform(40.0, 44.0), 1)
        db_lat = round(random.uniform(8.0, 22.0) if is_peak else random.uniform(1.5, 6.0), 2)
        red_lat = round(random.uniform(1.0, 2.5) if is_peak else random.uniform(0.1, 0.8), 2)
        q_depth = random.randint(3, 15) if is_peak else random.randint(0, 2)
        err = round(random.uniform(0.5, 2.0) if is_peak and random.random() < 0.3 else 0.0, 2)
        
        history.append({
            "timestamp": dt.isoformat() + "Z",
            "db_latency": db_lat,
            "redis_latency": red_lat,
            "cpu_usage": cpu,
            "memory_usage": mem,
            "queue_depth": q_depth,
            "error_rate": err
        })

    try:
        # Push snapshots chronologically
        for snapshot in history:
            r_client.rpush("health:history", json.dumps(snapshot))
            
        print("   [+] 100 KPI Records seeded in Redis (health:history).")
    except Exception as e:
        print(f"   [!] Could not insert health history into Redis: {e}")

def main():
    print("=" * 60)
    print("   TNT ADMIN DATA SEEDER")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Fetch reference users
        users = db.query(User).all()
        admins = [u for u in users if u.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]]
        vendors = [u for u in users if u.role == UserRole.VENDOR]
        students_faculty = [u for u in users if u.role in [UserRole.STUDENT, UserRole.FACULTY]]

        if not users or len(users) < 5:
            print("[!] Critical user base is low. Please run main seed_data.py first to bootstrap users/menu items.")
            sys.exit(1)

        # 2. Ensure we have sufficient orders to link vendor reviews, feedback, fraud alerts
        orders = ensure_orders(db, 250)

        # 3. Seed entities
        seed_audit_logs(db, admins, vendors, students_faculty)
        seed_fraud_alerts(db, students_faculty, vendors, orders)
        seed_backups(db)
        seed_vendor_performance(db, students_faculty, vendors, orders)
        seed_user_activity(db, students_faculty, vendors, orders)

        # 4. Seed Redis metrics
        seed_redis_security_events()
        seed_redis_health_history()

        print("\n" + "=" * 60)
        print("   ADMIN SEED DATA GENERATED AND POPULATED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[-] Error during administrative seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
