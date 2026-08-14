from sqlalchemy.orm import Session
from app.db.models.reminder import Reminder


class ReminderRepository:

    @staticmethod
    def create_reminder(db: Session, reminder: Reminder) -> Reminder:
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder

    @staticmethod
    def get_reminder_by_id(db: Session, reminder_id: int) -> Reminder | None:
        return db.query(Reminder).filter(Reminder.id == reminder_id).first()

    @staticmethod
    def get_reminders_for_device(db: Session, device_id: str, active_only: bool = True) -> list[Reminder]:
        query = db.query(Reminder).filter(Reminder.device_id == device_id)
        if active_only:
            query = query.filter(Reminder.is_active == True)
        return query.order_by(Reminder.created_at.desc()).all()

    @staticmethod
    def get_all_active_reminders(db: Session) -> list[Reminder]:
        return db.query(Reminder).filter(Reminder.is_active == True).all()

    @staticmethod
    def update_reminder(db: Session, reminder: Reminder) -> Reminder:
        db.commit()
        db.refresh(reminder)
        return reminder

    @staticmethod
    def delete_reminder(db: Session, reminder: Reminder) -> None:
        reminder.is_active = False
        db.commit()
