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

        sched.start()
        logger.info("Backup scheduler started (daily@02:00 UTC, weekly@Sunday 03:00 UTC)")
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
