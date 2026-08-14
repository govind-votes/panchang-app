from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.db.schemas.reminder import (
    ReminderCreateRequest,
    ReminderUpdateRequest,
    ReminderDeleteRequest,
    ReminderResponse,
    ReminderHistoryEntry,
)
from app.db.services.reminder_service import ReminderService
from app.db.repositories.notification_log_repository import NotificationLogRepository
from app.notification.reminder_notification_service import evaluate_reminder_now

router = APIRouter(prefix="/reminders", tags=["Reminders"])
logger = logging.getLogger("reminder_route")


@router.post("", response_model=ReminderResponse)
def create_reminder(payload: ReminderCreateRequest, db: Session = Depends(get_db)):
    try:
        reminder = ReminderService.create_reminder(
            db=db,
            device_id=payload.device_id,
            tithi=payload.tithi,
            var=payload.var,
            yoga=payload.yoga,
            nakshatra=payload.nakshatra,
            note=payload.note,
            before_time=payload.before_time,
            day_of_time=payload.day_of_time,
        )
        try:
            evaluate_reminder_now(db, reminder)
        except Exception as e:
            # Non-fatal — the next daily matcher pass will pick it up regardless.
            logger.error("ERROR evaluating new reminder_id=%s immediately: %s", reminder.id, e)
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("ERROR in reminder.create for device_id=%s: %s", payload.device_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[ReminderResponse])
def list_reminders(device_id: str, db: Session = Depends(get_db)):
    try:
        return ReminderService.list_reminders(db, device_id)
    except Exception as e:
        logger.error("ERROR in reminder.list for device_id=%s: %s", device_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(reminder_id: int, payload: ReminderUpdateRequest, db: Session = Depends(get_db)):
    try:
        reminder = ReminderService.update_reminder(
            db=db,
            reminder_id=reminder_id,
            device_id=payload.device_id,
            tithi=payload.tithi,
            var=payload.var,
            yoga=payload.yoga,
            nakshatra=payload.nakshatra,
            note=payload.note,
            before_time=payload.before_time,
            day_of_time=payload.day_of_time,
        )
        # Criteria/times may have changed — any fire already scheduled
        # reflects the old ones, so drop it and recompute fresh.
        NotificationLogRepository.cancel_pending_fires_for_reminder(db, reminder.id)
        try:
            evaluate_reminder_now(db, reminder)
        except Exception as e:
            logger.error("ERROR evaluating updated reminder_id=%s immediately: %s", reminder.id, e)
        return reminder
    except ValueError as e:
        raise HTTPException(status_code=404 if "not found" in str(e).lower() else 400, detail=str(e))
    except Exception as e:
        logger.error("ERROR in reminder.update for reminder_id=%s: %s", reminder_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{reminder_id}")
def delete_reminder(reminder_id: int, payload: ReminderDeleteRequest, db: Session = Depends(get_db)):
    try:
        ReminderService.delete_reminder(db, reminder_id, payload.device_id)
        NotificationLogRepository.cancel_pending_fires_for_reminder(db, reminder_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("ERROR in reminder.delete for reminder_id=%s: %s", reminder_id, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=list[ReminderHistoryEntry])
def reminder_history(device_id: str, db: Session = Depends(get_db)):
    try:
        return NotificationLogRepository.get_reminder_history_for_device(db, device_id)
    except Exception as e:
        logger.error("ERROR in reminder.history for device_id=%s: %s", device_id, e)
        raise HTTPException(status_code=400, detail=str(e))
