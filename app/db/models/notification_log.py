from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from datetime import datetime
from app.db.base import Base


class NotificationLog(Base):
    """
    Persisted record of every notification, replacing the old in-memory
    _SENT_CACHE dedup set (which lost state on every restart and didn't work
    across multiple worker processes).

    Two roles in one table:
    - DAILY_NAKSHATRA / NAKSHATRA_END: written with status="sent" at the
      moment of sending (same live check-and-send pattern as before, just
      backed by a real table now).
    - REMINDER_BEFORE / REMINDER_DAY_OF: written with status="pending" by the
      daily reminder matcher job (with fire_at_utc set to the target send
      time), then flipped to "sent" by the reminder sender job once it's due.
    """

    __tablename__ = "notification_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)

    notif_type = Column(String, nullable=False, index=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id"), nullable=True, index=True)

    # Local calendar date (YYYY-MM-DD) this notification pertains to.
    matched_date = Column(String, nullable=True, index=True)

    # Only meaningful for pre-scheduled reminder types.
    fire_at_utc = Column(DateTime, nullable=True, index=True)

    status = Column(String, nullable=False, default="sent")  # pending | sent | failed
    sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
