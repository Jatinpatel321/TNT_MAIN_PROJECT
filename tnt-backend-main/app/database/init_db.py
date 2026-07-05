"""Database initialisation — imports every model so SQLAlchemy metadata is built."""
import app.modules.group_cart.model  # noqa
import app.modules.feedback.model  # noqa
import app.modules.admin.broadcast_model  # noqa
import app.modules.complaints.model  # noqa
import app.modules.ledger.model  # noqa
import app.modules.menu.model  # noqa
import app.modules.notifications.model
import app.modules.orders.history_model  # noqa
import app.modules.orders.model  # noqa
import app.modules.payments.model  # noqa
import app.modules.rewards.model  # noqa
import app.modules.slots.model  # noqa
import app.modules.stationery.job_model
import app.modules.stationery.service_model

# ── ML registry models ───────────────────────────────────────────────────
import app.ml.ml_models_model  # noqa

# ── VENDOR MODULE MODELS ──────────────────────────────────────────────────
import app.modules.vendors.model  # noqa
import app.modules.vendors.profile_models  # noqa
import app.modules.vendors.retention_models  # noqa
import app.modules.vendors.settlement_models  # noqa
import app.modules.admin.model  # noqa
import app.modules.recommendations.models  # noqa
import app.modules.calendar.model  # noqa
import app.modules.auditlog.model  # noqa
import app.modules.fraud.model  # noqa
import app.modules.backup.models  # noqa

# ── FORCE IMPORT MODELS ─────────────────────────────────────────────────────
import app.modules.users.model  # noqa
from app.database.base import Base
from app.database.session import engine



def init_db():
    from sqlalchemy import text
    # Check if vendor_profiles has 'id' column
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT id FROM vendor_profiles LIMIT 1"))
        except Exception:
            # Table doesn't have 'id' column or doesn't exist. Drop it CASCADE.
            try:
                conn.execute(text("DROP TABLE IF EXISTS vendor_profiles CASCADE"))
                conn.commit()
            except Exception:
                pass

    Base.metadata.create_all(bind=engine)
    # Ensure group_id column exists on orders table dynamically
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS group_id INTEGER REFERENCES groups(id)"))
            conn.commit()
        except Exception:
            pass


if __name__ == "__main__":
    init_db()
