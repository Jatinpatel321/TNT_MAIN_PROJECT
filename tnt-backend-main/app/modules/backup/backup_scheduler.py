"""
Backup Scheduler — APScheduler-based cron jobs for automatic backups.

Jobs:
  - daily_backup   → runs every day at 02:00 UTC
  - weekly_backup  → runs every Sunday at 03:00 UTC

The scheduler is started/stopped inside the FastAPI lifespan context manager
in app/main.py.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger("tnt.backup.scheduler")

_scheduler = None  # module-level singleton


def _get_scheduler():
    """Lazy-import APScheduler to avoid import errors if not installed."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
        _scheduler = AsyncIOScheduler(timezone="UTC")
        return _scheduler
    except ImportError:
        logger.warning(
            "APScheduler not installed — scheduled backups disabled. "
            "Run: pip install apscheduler"
        )
        return None


def _run_daily_backup():
    """Scheduled job: daily backup at 02:00 UTC."""
    try:
        from app.database.session import SessionLocal
        from app.modules.backup.backup_service import run_backup
        from app.modules.backup.models import BackupType

        logger.info("Scheduler: starting daily backup")
        db = SessionLocal()
        try:
            run_backup(backup_type=BackupType.daily, db=db)
            logger.info("Scheduler: daily backup complete")
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: daily backup failed: %s", exc)


def _run_weekly_backup():
    """Scheduled job: weekly backup on Sunday at 03:00 UTC."""
    try:
        from app.database.session import SessionLocal
        from app.modules.backup.backup_service import run_backup
        from app.modules.backup.models import BackupType

        logger.info("Scheduler: starting weekly backup")
        db = SessionLocal()
        try:
            run_backup(backup_type=BackupType.weekly, db=db)
            logger.info("Scheduler: weekly backup complete")
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: weekly backup failed: %s", exc)


def _run_proactive_delays():
    """Scheduled job: check and proactively alert users of order delays."""
    try:
        from app.database.session import SessionLocal
        from app.modules.notifications.alert_tasks import check_proactive_delays_job
        db = SessionLocal()
        try:
            check_proactive_delays_job(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: proactive delay checks failed: %s", exc)


def _run_proactive_rush_hour_alerts():
    """Scheduled job: check and send proactive rush hour alerts."""
    try:
        from app.database.session import SessionLocal
        from app.modules.notifications.alert_tasks import send_proactive_rush_hour_alerts_job
        db = SessionLocal()
        try:
            send_proactive_rush_hour_alerts_job(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: proactive rush hour alerts failed: %s", exc)


def _run_auto_escalate_complaints():
    """Scheduled job: run SLA complaint escalation."""
    try:
        from app.database.session import SessionLocal
        from app.modules.complaints.escalation_service import auto_escalate_complaints_job
        db = SessionLocal()
        try:
            auto_escalate_complaints_job(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: auto-escalate complaints failed: %s", exc)


def _run_dynamic_slot_adjustment():
    """Scheduled job: apply AI slot-capacity adjustments for all active vendors."""
    try:
        from app.database.session import SessionLocal
        from app.modules.ai_intelligence.service import AIIntelligenceService
        from app.modules.users.model import User, UserRole

        logger.info("Scheduler: starting dynamic slot adjustment sweep")
        db = SessionLocal()
        try:
            vendors = db.query(User).filter(
                User.role == UserRole.VENDOR,
                User.is_active == True,  # noqa: E712
                User.is_approved == True,  # noqa: E712
            ).all()
            service = AIIntelligenceService(db)
            total_applied = 0
            for vendor in vendors:
                try:
                    result = service.apply_slot_adjustments(vendor.id)
                    total_applied += result.adjustments_applied
                except Exception as vexc:
                    logger.warning(
                        "Scheduler: slot adjustment failed for vendor %s: %s", vendor.id, vexc
                    )
            logger.info(
                "Scheduler: dynamic slot adjustment complete — %s vendors, %s adjustments applied",
                len(vendors), total_applied,
            )
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: dynamic slot adjustment sweep failed: %s", exc)


def _run_ml_retraining():
    """Scheduled job to retrain all ML models periodically."""
    logger.info("Scheduler: starting ML model retraining sweep")
    try:
        from app.database.session import SessionLocal
        from app.ml.retraining import run_scheduled_retraining
        db = SessionLocal()
        try:
            results = run_scheduled_retraining(db=db)
            logger.info("Scheduler: ML model retraining sweep complete: %s", results)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: ML model retraining sweep failed: %s", exc)


def _run_weekly_ml_retraining():
    """Scheduled job: weekly retraining for fast-changing models (ETA, Demand, Slot, Fraud)."""
    logger.info("Scheduler: starting weekly ML model retraining")
    try:
        from app.database.session import SessionLocal
        from app.ml.retraining import run_scheduled_retraining
        db = SessionLocal()
        try:
            results = run_scheduled_retraining(
                model_types=["eta_prediction", "demand_forecast", "slot_recommendation", "fraud_detection"],
                db=db,
            )
            logger.info("Scheduler: weekly ML retraining complete: %s", results)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: weekly ML retraining failed: %s", exc)


def _run_monthly_ml_retraining():
    """Scheduled job: monthly retraining for slower-changing models (Vendor Ranking)."""
    logger.info("Scheduler: starting monthly ML model retraining")
    try:
        from app.database.session import SessionLocal
        from app.ml.retraining import run_scheduled_retraining
        db = SessionLocal()
        try:
            results = run_scheduled_retraining(
                model_types=["vendor_ranking"],
                db=db,
            )
            logger.info("Scheduler: monthly ML retraining complete: %s", results)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: monthly ML retraining failed: %s", exc)


def _run_payment_reconciliation():
    """Scheduled job: reconcile stuck initiated payments (>15 mins old)."""
    try:
        from app.database.session import SessionLocal
        from app.modules.payments.reconciliation_service import reconcile_stuck_payments_job
        db = SessionLocal()
        try:
            results = reconcile_stuck_payments_job(db)
            logger.info("Scheduler: payment reconciliation complete: %s", results)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: payment reconciliation failed: %s", exc)


def _run_weekly_drift_checks():
    """Scheduled job to check feature and prediction drift weekly for all ML models."""
    logger.info("Scheduler: starting weekly ML drift checks")
    try:
        from app.database.session import SessionLocal
        from app.ml.drift import run_all_drift_checks
        db = SessionLocal()
        try:
            results = run_all_drift_checks(db, lookback_days=7)
            logger.info("Scheduler: weekly ML drift checks complete: %s", results)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: weekly ML drift checks failed: %s", exc)


def _run_daily_rollback_checks():
    """Scheduled job: daily check to automatically rollback degraded models (< 7 days old, > 20% drop)."""
    logger.info("Scheduler: starting daily ML automatic rollback checks")
    try:
        from app.database.session import SessionLocal
        from app.ml.promotion import check_and_rollback_degraded_models
        db = SessionLocal()
        try:
            results = check_and_rollback_degraded_models(db)
            logger.info("Scheduler: daily ML rollback checks complete: %s", results)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduler: daily ML rollback checks failed: %s", exc)


def start_scheduler() -> None:
    """Start the background scheduler with daily + weekly backup jobs."""
    sched = _get_scheduler()
    if sched is None:
        return

    try:
        from apscheduler.triggers.cron import CronTrigger  # type: ignore

        # Daily at 02:00 UTC
        sched.add_job(
            _run_daily_backup,
            trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
            id="daily_backup",
            name="Daily Database Backup",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        # Weekly on Sunday at 03:00 UTC
        sched.add_job(
            _run_weekly_backup,
            trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
            id="weekly_backup",
            name="Weekly Database Backup",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        # Proactive Delay Checks (every 10 minutes)
        sched.add_job(
            _run_proactive_delays,
            trigger=CronTrigger(minute="*/10", timezone="UTC"),
            id="proactive_delays",
            name="Proactive Delay Alerts Check",
            replace_existing=True,
            misfire_grace_time=300,
        )

        # Payment Reconciliation (every 15 minutes)
        sched.add_job(
            _run_payment_reconciliation,
            trigger=CronTrigger(minute="*/15", timezone="UTC"),
            id="payment_reconciliation",
            name="Automated Razorpay Payment Reconciliation",
            replace_existing=True,
            misfire_grace_time=600,
        )

        # Proactive Rush Hour Alerts (every hour)
        sched.add_job(
            _run_proactive_rush_hour_alerts,
            trigger=CronTrigger(minute="0", timezone="UTC"),
            id="proactive_rush_hour",
            name="Proactive Rush Hour Alerts Check",
            replace_existing=True,
            misfire_grace_time=600,
        )

        # Complaint Auto-escalation (every hour)
        sched.add_job(
            _run_auto_escalate_complaints,
            trigger=CronTrigger(minute="0", timezone="UTC"),
            id="complaint_escalation",
            name="Complaint SLA Auto-Escalation Check",
            replace_existing=True,
            misfire_grace_time=600,
        )

        # Weekly ML model retraining (Sunday at 05:00 UTC)
        sched.add_job(
            _run_weekly_ml_retraining,
            trigger=CronTrigger(day_of_week="sun", hour=5, minute=0, timezone="UTC"),
            id="weekly_ml_retraining",
            name="Weekly ML Model Retraining (ETA, Demand, Slot, Fraud)",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        # Monthly ML model retraining (1st of month at 05:30 UTC)
        sched.add_job(
            _run_monthly_ml_retraining,
            trigger=CronTrigger(day=1, hour=5, minute=30, timezone="UTC"),
            id="monthly_ml_retraining",
            name="Monthly ML Model Retraining (Vendor Ranking)",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        # Dynamic slot capacity adjustment (every 2 hours)
        sched.add_job(
            _run_dynamic_slot_adjustment,
            trigger=CronTrigger(hour="*/2", minute=15, timezone="UTC"),
            id="dynamic_slot_adjustment",
            name="Dynamic Slot Capacity Adjustment",
            replace_existing=True,
            misfire_grace_time=1800,
        )

        # Weekly ML drift checks (Sunday at 04:00 UTC)
        sched.add_job(
            _run_weekly_drift_checks,
            trigger=CronTrigger(day_of_week="sun", hour=4, minute=0, timezone="UTC"),
            id="weekly_ml_drift_checks",
            name="Weekly ML Drift Checks",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        # Daily ML rollback check (06:00 UTC)
        sched.add_job(
            _run_daily_rollback_checks,
            trigger=CronTrigger(hour=6, minute=0, timezone="UTC"),
            id="daily_ml_rollback_check",
            name="Daily ML Degradation Rollback Check",
            replace_existing=True,
            misfire_grace_time=3600,
        )

        sched.start()
        logger.info("Backup scheduler started (daily@02:00 UTC, weekly@Sunday 03:00 UTC, proactive tasks configured)")
    except Exception as exc:
        logger.error("Failed to start backup scheduler: %s", exc)


def stop_scheduler() -> None:
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Backup scheduler stopped")
        except Exception as exc:
            logger.error("Error stopping scheduler: %s", exc)
        _scheduler = None


def get_scheduler_status() -> dict:
    """Return current scheduler status and next run times for all jobs."""
    sched = _scheduler

    if sched is None or not sched.running:
        return {
            "running": False,
            "jobs": [
                {
                    "job_id": "daily_backup",
                    "name": "Daily Database Backup",
                    "next_run_time": None,
                    "trigger": "cron(hour=2, minute=0) UTC",
                },
                {
                    "job_id": "weekly_backup",
                    "name": "Weekly Database Backup",
                    "next_run_time": None,
                    "trigger": "cron(day_of_week=sun, hour=3, minute=0) UTC",
                },
                {
                    "job_id": "ml_retraining",
                    "name": "Periodic ML Model Retraining",
                    "next_run_time": None,
                    "trigger": "cron(hour=1, minute=0) UTC",
                },
            ],
        }

    jobs_info = []
    for job in sched.get_jobs():
        next_run = job.next_run_time
        jobs_info.append(
            {
                "job_id": job.id,
                "name": job.name,
                "next_run_time": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger),
            }
        )

    return {
        "running": sched.running,
        "jobs": jobs_info,
    }
