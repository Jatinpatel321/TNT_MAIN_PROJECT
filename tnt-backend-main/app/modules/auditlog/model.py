"""Audit log model - immutable record of all admin actions."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.sql import func

from app.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)

    # Actor
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_role = Column(String(50), nullable=True)

    # Action — use dot notation: "vendor.approved", "user.blocked", "policy.updated"
    action = Column(String(100), nullable=False)
    action_category = Column(String(50), nullable=False)

    # Target entity
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)

    # State snapshots
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    meta = Column("metadata", JSON, nullable=True)

    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
