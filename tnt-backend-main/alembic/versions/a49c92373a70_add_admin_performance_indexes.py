"""add_admin_performance_indexes

Revision ID: a49c92373a70
Revises: 20260626_0030
Create Date: 2026-06-26 13:37:27.653246

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a49c92373a70'
down_revision = '20260626_0030'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_audit_logs_actor_id', 'audit_logs', ['actor_id'], unique=False)
    op.create_index('ix_audit_logs_action_category', 'audit_logs', ['action_category'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    
    op.create_index('ix_fraud_alerts_status', 'fraud_alerts', ['status'], unique=False)
    op.create_index('ix_fraud_alerts_severity', 'fraud_alerts', ['severity'], unique=False)
    op.create_index('ix_fraud_alerts_created_at', 'fraud_alerts', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_logs_actor_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action_category', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    
    op.drop_index('ix_fraud_alerts_status', table_name='fraud_alerts')
    op.drop_index('ix_fraud_alerts_severity', table_name='fraud_alerts')
    op.drop_index('ix_fraud_alerts_created_at', table_name='fraud_alerts')
