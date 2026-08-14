from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models.notification_log import NotificationLog


class NotificationLogRepository:

    # ---- Live-send dedup (DAILY_NAKSHATRA / NAKSHATRA_END) ----

    @staticmethod
    def already_sent(db: Session, device_id: str, notif_type: str, matched_date: str) -> bool:
        return (
            db.query(NotificationLog)
            .filter(
                NotificationLog.device_id == device_id,
                NotificationLog.notif_type == notif_type,
                NotificationLog.matched_date == matched_date,
                NotificationLog.status == "sent",
            )
            .first()
            is not None
        )

    @staticmethod
    def mark_sent(db: Session, device_id: str, notif_type: str, matched_date: str) -> None:
        db.add(
            NotificationLog(
                device_id=device_id,
                notif_type=notif_type,
                matched_date=matched_date,
                status="sent",
                sent_at=datetime.utcnow(),
            )
        )
        db.commit()

    # ---- Reminder pre-scheduling (REMINDER_BEFORE / REMINDER_DAY_OF) ----

    @staticmethod
    def pending_or_sent_fire_exists(
        db: Session, reminder_id: int, notif_type: str, matched_date: str
    ) -> bool:
        return (
            db.query(NotificationLog)
            .filter(
                NotificationLog.reminder_id == reminder_id,
                NotificationLog.notif_type == notif_type,
                NotificationLog.matched_date == matched_date,
                NotificationLog.status.in_(["pending", "sent"]),
            )
            .first()
            is not None
        )

    @staticmethod
    def create_pending_fire(
        db: Session,
        device_id: str,
        reminder_id: int,
        notif_type: str,
        matched_date: str,
        fire_at_utc: datetime,
    ) -> NotificationLog:
        log = NotificationLog(
            device_id=device_id,
            reminder_id=reminder_id,
            notif_type=notif_type,
            matched_date=matched_date,
            fire_at_utc=fire_at_utc,
            status="pending",
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_due_pending_fires(db: Session, now_utc: datetime) -> list[NotificationLog]:
        return (
            db.query(NotificationLog)
            .filter(
                NotificationLog.status == "pending",
                NotificationLog.fire_at_utc <= now_utc,
            )
            .all()
        )

    @staticmethod
    def mark_fire_sent(db: Session, log: NotificationLog) -> None:
        log.status = "sent"
        log.sent_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def mark_fire_failed(db: Session, log: NotificationLog) -> None:
        log.status = "failed"
        db.commit()

    @staticmethod
    def cancel_pending_fires_for_reminder(db: Session, reminder_id: int) -> None:
        """
        Called when a reminder's criteria/times are edited — any fire already
        scheduled reflects the *old* criteria, so it must be dropped rather
        than sent with stale matching logic. The next evaluation (immediate
        or the next daily pass) recomputes fresh matches under the new criteria.
        """
        (
            db.query(NotificationLog)
            .filter(
                NotificationLog.reminder_id == reminder_id,
                NotificationLog.status == "pending",
            )
            .delete()
        )
        db.commit()

    # ---- History for the Reminder List screen ----

    @staticmethod
    def get_reminder_history_for_device(db: Session, device_id: str, limit: int = 100) -> list[NotificationLog]:
        return (
            db.query(NotificationLog)
            .filter(
                NotificationLog.device_id == device_id,
                NotificationLog.notif_type.in_(["REMINDER_BEFORE", "REMINDER_DAY_OF"]),
                NotificationLog.status == "sent",
            )
            .order_by(NotificationLog.sent_at.desc())
            .limit(limit)
            .all()
        )
