import re
from sqlalchemy.orm import Session

from app.db.models.reminder import Reminder
from app.db.repositories.reminder_repository import ReminderRepository

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

CRITERIA_FIELDS = ("tithi", "var", "yoga", "nakshatra")


def _validate_time(value: str, field_name: str) -> str:
    if not TIME_RE.match(value or ""):
        raise ValueError(f"{field_name} must be in 24-hour HH:MM format")
    return value


def _validate_criteria(fields: dict) -> None:
    if not any((fields.get(key) or "").strip() for key in CRITERIA_FIELDS):
        raise ValueError(
            "At least one of tithi, var, yoga, or nakshatra must be selected"
        )


class ReminderService:

    @staticmethod
    def create_reminder(
        db: Session,
        device_id: str,
        tithi: str | None,
        var: str | None,
        yoga: str | None,
        nakshatra: str | None,
        note: str | None,
        before_time: str = "20:00",
        day_of_time: str = "06:00",
    ) -> Reminder:
        fields = {"tithi": tithi, "var": var, "yoga": yoga, "nakshatra": nakshatra}
        _validate_criteria(fields)
        _validate_time(before_time, "before_time")
        _validate_time(day_of_time, "day_of_time")

        reminder = Reminder(
            device_id=device_id,
            tithi=(tithi or "").strip() or None,
            var=(var or "").strip() or None,
            yoga=(yoga or "").strip() or None,
            nakshatra=(nakshatra or "").strip() or None,
            note=(note or "").strip() or None,
            before_time=before_time,
            day_of_time=day_of_time,
        )
        return ReminderRepository.create_reminder(db, reminder)

    @staticmethod
    def update_reminder(
        db: Session,
        reminder_id: int,
        device_id: str,
        tithi: str | None,
        var: str | None,
        yoga: str | None,
        nakshatra: str | None,
        note: str | None,
        before_time: str,
        day_of_time: str,
    ) -> Reminder:
        reminder = ReminderRepository.get_reminder_by_id(db, reminder_id)
        if reminder is None or reminder.device_id != device_id:
            raise ValueError("Reminder not found")

        fields = {"tithi": tithi, "var": var, "yoga": yoga, "nakshatra": nakshatra}
        _validate_criteria(fields)
        _validate_time(before_time, "before_time")
        _validate_time(day_of_time, "day_of_time")

        reminder.tithi = (tithi or "").strip() or None
        reminder.var = (var or "").strip() or None
        reminder.yoga = (yoga or "").strip() or None
        reminder.nakshatra = (nakshatra or "").strip() or None
        reminder.note = (note or "").strip() or None
        reminder.before_time = before_time
        reminder.day_of_time = day_of_time

        return ReminderRepository.update_reminder(db, reminder)

    @staticmethod
    def delete_reminder(db: Session, reminder_id: int, device_id: str) -> None:
        reminder = ReminderRepository.get_reminder_by_id(db, reminder_id)
        if reminder is None or reminder.device_id != device_id:
            raise ValueError("Reminder not found")
        ReminderRepository.delete_reminder(db, reminder)

    @staticmethod
    def list_reminders(db: Session, device_id: str) -> list[Reminder]:
        return ReminderRepository.get_reminders_for_device(db, device_id)

    @staticmethod
    def reminder_matches(reminder: Reminder, panchang: dict) -> bool:
        """
        AND-match across whichever fields the reminder specifies — a field
        left unset by the user is not checked at all.
        """
        checks = [
            (reminder.tithi, panchang.get("tithi", {}).get("name")),
            (reminder.var, panchang.get("var")),
            (reminder.yoga, panchang.get("yoga", {}).get("name")),
            (reminder.nakshatra, panchang.get("moon", {}).get("nakshatra")),
        ]
        for expected, actual in checks:
            if expected is None:
                continue
            if (actual or "").strip().lower() != expected.strip().lower():
                return False
        return True
