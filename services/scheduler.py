"""Background scheduler (APScheduler). Disable with ENABLE_SCHEDULER=false."""
import logging
import os
from datetime import datetime
from database import SessionLocal
from services.jobs import get_settings, company_tz, finalize_pending, accrue_month

log = logging.getLogger("scheduler")


def daily_job():
    db = SessionLocal()
    try:
        now = datetime.now(company_tz(get_settings(db)))
        finalize_pending(db, now.date(), now=now)   # includes today: night shifts end in the morning
    except Exception:
        db.rollback()
        log.exception("Daily finalize failed")
    finally:
        db.close()


def monthly_job():
    db = SessionLocal()
    try:
        now = datetime.now(company_tz(get_settings(db)))
        accrue_month(db, now.year, now.month)
    except ValueError as e:
        log.warning("Monthly accrual skipped: %s", e)
    except Exception:
        db.rollback()
        log.exception("Monthly accrual failed")
    finally:
        db.close()


def overtime_job():
    from services.overtime import run_cycle
    db = SessionLocal()
    try:
        run_cycle(db)
    except Exception:
        db.rollback()
        log.exception("Overtime cycle failed")
    finally:
        db.close()


def catch_up():
    daily_job()
    monthly_job()


def start_scheduler():
    if os.getenv("ENABLE_SCHEDULER", "true").lower() != "true":
        return None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        log.warning("apscheduler is not installed; scheduled jobs are disabled")
        return None
    db = SessionLocal()
    try:
        tz = company_tz(get_settings(db))
    except Exception:
        tz = company_tz(None)
    finally:
        db.close()
    sch = BackgroundScheduler(timezone=tz)
    # every 15 minutes: finalizes each employee-day once THAT employee's shift is over (day, evening, night ...)
    sch.add_job(daily_job, "interval", minutes=15, id="finalize_due", max_instances=1, coalesce=True,
                replace_existing=True)
    sch.add_job(monthly_job, CronTrigger(day=1, hour=0, minute=10), id="monthly_accrual", replace_existing=True)
    sch.add_job(overtime_job, "interval", minutes=1, id="overtime_cycle", max_instances=1, coalesce=True,
                replace_existing=True)
    sch.add_job(catch_up, id="startup_catch_up")  # runs once, immediately
    sch.start()
    return sch