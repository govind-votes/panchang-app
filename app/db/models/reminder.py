from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey
from datetime import datetime
from app.db.base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey("devices.device_id"), nullable=False, index=True)

    # At least one of these four must be set — enforced at the service layer,
    # not the DB, since "at least one of N nullable columns" isn't expressible
    # as a simple column constraint.
    tithi = Column(String, nullable=True)
    var = Column(String, nullable=True)
    yoga = Column(String, nullable=True)
    nakshatra = Column(String, nullable=True)

    note = Column(Text, nullable=True)

    # "HH:MM" 24-hour, device-local wall clock.
    before_time = Column(String, nullable=False, default="20:00")
    day_of_time = Column(String, nullable=False, default="06:00")

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
