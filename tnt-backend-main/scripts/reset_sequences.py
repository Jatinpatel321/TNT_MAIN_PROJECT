from __future__ import annotations

import logging
from sqlalchemy import text
from app.database.session import SessionLocal
from app.database.base import Base

# Import all SQLAlchemy models to ensure they register in Base.metadata
import app.modules.users.model
import app.modules.vendors.model
import app.modules.vendors.profile_models
import app.modules.vendors.settlement_models
import app.modules.vendors.retention_models
import app.modules.menu.model
import app.modules.slots.model
import app.modules.orders.model
import app.modules.orders.history_model
import app.modules.stationery.service_model
import app.modules.stationery.job_model
import app.modules.payments.model
import app.modules.ledger.model
import app.modules.rewards.model
import app.modules.notifications.model
import app.modules.feedback.model
import app.modules.complaints.model
import app.modules.calendar.model
import app.modules.auditlog.model
import app.modules.admin.model
import app.modules.admin.broadcast_model
import app.modules.recommendations.models
import app.modules.group_cart.model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_sequences")

def reset_sequences():
    db = SessionLocal()
    try:
        # Check if we are running on postgresql
        dialect_name = db.bind.dialect.name
        if dialect_name != "postgresql":
            logger.info(f"Skipping sequence reset: dialect is '{dialect_name}', not 'postgresql'")
            return

        for table_name, table in Base.metadata.tables.items():
            pk_cols = [c.name for c in table.primary_key.columns]
            if not pk_cols:
                continue
            pk_col = pk_cols[0]
            
            try:
                # Find the sequence name associated with the primary key
                res = db.execute(text(f"SELECT pg_get_serial_sequence('{table_name}', '{pk_col}')")).fetchone()
                seq_name = res[0] if res else None
                if seq_name:
                    # Find max value
                    max_val_res = db.execute(text(f"SELECT COALESCE(MAX({pk_col}), 0) FROM {table_name}")).fetchone()
                    max_val = max_val_res[0] if max_val_res else 0
                    next_val = max_val + 1
                    db.execute(text(f"SELECT setval(:seq_name, :next_val, false)"), {"seq_name": seq_name, "next_val": next_val})
                    db.commit()
                    logger.info(f"Successfully reset sequence '{seq_name}' for table '{table_name}' to {next_val}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error resetting sequence for table '{table_name}': {e}")
    finally:
        db.close()

if __name__ == "__main__":
    reset_sequences()
