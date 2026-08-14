import fcntl
import logging
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.notification.notification_service import send_daily_notifications
from app.notification.reminder_notification_service import (
    run_reminder_matcher,
    send_pending_reminder_notifications,
)

_scheduler = None  # 🔒 singleton
_scheduler_lock_handle = None
logger = logging.getLogger("scheduler")


def _acquire_scheduler_lock() -> bool:
    global _scheduler_lock_handle

    if _scheduler_lock_handle is not None:
        return True

    lock_path = os.getenv(
        "SCHEDULER_LOCK_FILE",
        "/tmp/nakshatra_app_scheduler.lock",
    )
    lock_handle = open(lock_path, "a+")

    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_handle.close()
        return False

    lock_handle.seek(0)
    lock_handle.truncate()
    lock_handle.write(str(os.getpid()))
    lock_handle.flush()
    _scheduler_lock_handle = lock_handle
    return True


def _release_scheduler_lock():
    global _scheduler_lock_handle

    if _scheduler_lock_handle is None:
        return

    fcntl.flock(_scheduler_lock_handle.fileno(), fcntl.LOCK_UN)
    _scheduler_lock_handle.close()
    _scheduler_lock_handle = None


def create_scheduler():
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    if not _acquire_scheduler_lock():
        logger.info(
            "Scheduler startup skipped in pid=%s because another process already owns the lock",
            os.getpid(),
        )
        return None

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        send_daily_notifications,
        trigger="interval",
        seconds=60,
        id="notification_dispatcher",
        replace_existing=True,
        max_instances=1,          # 🔒 prevents overlap
        coalesce=True             # 🔒 skip missed runs
    )

    # Reminder pipeline (see reminder_notification_service.py for design notes):
    # a cheap once-daily matcher that precomputes matches, and a frequent
    # sender that just checks/sends whatever's due.
    scheduler.add_job(
        run_reminder_matcher,
        trigger="interval",
        hours=24,
        # Fire immediately on startup (so newly created reminders don't wait
        # up to 24h after a deploy/restart before their first match check),
        # then every 24h after that.
        next_run_time=datetime.now(),
        id="reminder_matcher",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        send_pending_reminder_notifications,
        trigger="interval",
        seconds=60,
        id="reminder_sender",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    _scheduler = scheduler
    return scheduler


def shutdown_scheduler():
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown()

    _scheduler = None
    _release_scheduler_lock()
