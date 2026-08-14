# reminder_notification_service.py
#
# Two-phase reminder pipeline (see design discussion — "Approach 1"):
#   1. run_reminder_matcher() — runs once/day. For each device with active
#      reminders, computes Panchang once and checks it against every one of
#      that device's reminders, writing a "pending" NotificationLog row (with
#      its exact UTC send time) for each match. Self-corrects regardless of
#      what wall-clock time it actually runs at, by always targeting the next
#      upcoming occurrence of each fire type relative to the device's current
#      local time.
#   2. send_pending_reminder_notifications() — runs frequently (same cadence
#      as the existing notification tick). Just queries pending rows whose
#      fire_at_utc has passed and sends them — cheap, and naturally
#      restart-safe since nothing lives only in scheduler memory.

import logging
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from .firebase_service import send_push_notification
from app.db.repositories.device_repository import DeviceRepository
from app.db.repositories.reminder_repository import ReminderRepository
from app.db.repositories.notification_log_repository import NotificationLogRepository
from app.db.services.reminder_service import ReminderService
from app.db.session import SessionLocal
from app.astrology import get_planet_positions

logger = logging.getLogger("reminder_notification")


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _combine_local_to_utc(local_date, hhmm_str: str, tz: ZoneInfo) -> datetime:
    t = _parse_hhmm(hhmm_str)
    local_dt = datetime.combine(local_date, t, tzinfo=tz)
    return local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def _next_send_date(local_now: datetime, hhmm_str: str):
    """The next local calendar date on which this HH:MM hasn't passed yet."""
    target_time = _parse_hhmm(hhmm_str)
    if local_now.time() < target_time:
        return local_now.date()
    return local_now.date() + timedelta(days=1)


def _panchang_for_date(target_date, lat: float, lon: float, tz_offset_hours: float) -> dict:
    # `hour` only affects nothing beyond sunrise anchoring for a given
    # calendar date — passing 0 is fine since sunrise/panchang for a fixed
    # date+location doesn't depend on it.
    return get_planet_positions(
        year=target_date.year,
        month=target_date.month,
        day=target_date.day,
        hour=0,
        lat=lat,
        lon=lon,
        tz_offset=tz_offset_hours,
    )


def _schedule_fire_if_matched(db, device, reminder, matched_date, notif_type, fire_at_utc):
    matched_date_str = matched_date.isoformat()

    if NotificationLogRepository.pending_or_sent_fire_exists(
        db, reminder.id, notif_type, matched_date_str
    ):
        return

    try:
        panchang = _panchang_for_date(
            matched_date,
            device.latitude,
            device.longitude,
            _tz_offset_for(device.timezone, matched_date),
        )
    except Exception as e:
        logger.error(
            "ERROR computing panchang for reminder_id=%s device_id=%s date=%s: %s",
            reminder.id, device.device_id, matched_date_str, e,
        )
        return

    if not ReminderService.reminder_matches(reminder, panchang):
        return

    NotificationLogRepository.create_pending_fire(
        db=db,
        device_id=device.device_id,
        reminder_id=reminder.id,
        notif_type=notif_type,
        matched_date=matched_date_str,
        fire_at_utc=fire_at_utc,
    )
    logger.info(
        "reminder_fire_scheduled reminder_id=%s device_id=%s type=%s matched_date=%s fire_at_utc=%s",
        reminder.id, device.device_id, notif_type, matched_date_str, fire_at_utc.isoformat(),
    )


def _tz_offset_for(timezone_str: str, on_date) -> float:
    tz = ZoneInfo(timezone_str)
    # Anchor to local noon on the target date so DST transitions on that
    # specific date are reflected correctly, rather than using "now"'s offset.
    probe = datetime.combine(on_date, time(12, 0), tzinfo=tz)
    return probe.utcoffset().total_seconds() / 3600


def evaluate_reminder_for_device(db, device, reminder, local_now, tz) -> None:
    """
    Checks a single reminder's before/day-of fires against the device's
    upcoming Panchang and schedules any matches. Shared by the daily batch
    matcher and the immediate check run right after a reminder is created/edited.
    """
    before_send_date = _next_send_date(local_now, reminder.before_time)
    before_matched_date = before_send_date + timedelta(days=1)
    before_fire_at_utc = _combine_local_to_utc(before_send_date, reminder.before_time, tz)
    _schedule_fire_if_matched(
        db, device, reminder, before_matched_date, "REMINDER_BEFORE", before_fire_at_utc,
    )

    day_of_send_date = _next_send_date(local_now, reminder.day_of_time)
    day_of_matched_date = day_of_send_date
    day_of_fire_at_utc = _combine_local_to_utc(day_of_send_date, reminder.day_of_time, tz)
    _schedule_fire_if_matched(
        db, device, reminder, day_of_matched_date, "REMINDER_DAY_OF", day_of_fire_at_utc,
    )


def evaluate_reminder_now(db, reminder) -> None:
    """
    Immediate single-reminder check — called right after create/update so a
    new reminder doesn't sit unevaluated for up to 24h waiting on the next
    daily matcher pass. Silently no-ops if the device isn't ready
    (no location/timezone yet); the next daily pass will pick it up then.
    """
    device = DeviceRepository.get_device_by_device_id(db, reminder.device_id)
    if not device or not device.is_active:
        return
    if not device.timezone or device.latitude is None or device.longitude is None:
        return

    try:
        tz = ZoneInfo(device.timezone)
    except Exception:
        return

    now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    local_now = now_utc.astimezone(tz)

    try:
        evaluate_reminder_for_device(db, device, reminder, local_now, tz)
    except Exception as e:
        logger.error(
            "ERROR in evaluate_reminder_now for reminder_id=%s device_id=%s: %s",
            reminder.id, reminder.device_id, e,
        )


def run_reminder_matcher():
    db = SessionLocal()
    try:
        reminders = ReminderRepository.get_all_active_reminders(db)
        if not reminders:
            return

        reminders_by_device = defaultdict(list)
        for reminder in reminders:
            reminders_by_device[reminder.device_id].append(reminder)

        now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))

        for device_id, device_reminders in reminders_by_device.items():
            device = DeviceRepository.get_device_by_device_id(db, device_id)
            if not device or not device.is_active:
                continue
            if not device.timezone or device.latitude is None or device.longitude is None:
                continue

            try:
                tz = ZoneInfo(device.timezone)
            except Exception:
                continue

            local_now = now_utc.astimezone(tz)

            for reminder in device_reminders:
                try:
                    evaluate_reminder_for_device(db, device, reminder, local_now, tz)
                except Exception as e:
                    logger.error(
                        "ERROR in run_reminder_matcher for reminder_id=%s device_id=%s: %s",
                        reminder.id, device_id, e,
                    )
    finally:
        db.close()


def _criteria_label(reminder) -> str:
    parts = []
    if reminder.tithi:
        parts.append(f"Tithi: {reminder.tithi}")
    if reminder.var:
        parts.append(f"Var: {reminder.var}")
    if reminder.yoga:
        parts.append(f"Yoga: {reminder.yoga}")
    if reminder.nakshatra:
        parts.append(f"Nakshatra: {reminder.nakshatra}")
    return " · ".join(parts)


def _build_reminder_message(reminder, notif_type: str):
    criteria = _criteria_label(reminder)
    note = (reminder.note or "").strip()

    if notif_type == "REMINDER_BEFORE":
        title = "Reminder — Tomorrow"
        fallback = f"Tomorrow matches your reminder ({criteria})" if criteria else "Tomorrow matches your reminder"
    else:
        title = "Reminder — Today"
        fallback = f"Today matches your reminder ({criteria})" if criteria else "Today matches your reminder"

    if note:
        body = f"{note} ({criteria})" if criteria else note
    else:
        body = fallback

    return title, body


def send_pending_reminder_notifications():
    db = SessionLocal()
    try:
        now_utc = datetime.utcnow()
        due_fires = NotificationLogRepository.get_due_pending_fires(db, now_utc)

        for log in due_fires:
            try:
                device = DeviceRepository.get_device_by_device_id(db, log.device_id)
                if not device or not device.fcm_token or not device.is_active:
                    NotificationLogRepository.mark_fire_failed(db, log)
                    continue

                reminder = ReminderRepository.get_reminder_by_id(db, log.reminder_id)
                if not reminder or not reminder.is_active:
                    NotificationLogRepository.mark_fire_failed(db, log)
                    continue

                title, body = _build_reminder_message(reminder, log.notif_type)

                message_id = send_push_notification(
                    token=device.fcm_token,
                    title=title,
                    body=body,
                    data={
                        "type": log.notif_type,
                        "date": log.matched_date,
                        "reminderId": str(reminder.id),
                        "navigateTo": "Reminders",
                        "deviceId": str(device.device_id),
                        "icon": "bell",
                        "emoji": "🔔",
                        "style": "reminder",
                    },
                )

                if message_id:
                    NotificationLogRepository.mark_fire_sent(db, log)
                    logger.info(
                        "reminder_notification_sent reminder_id=%s device_id=%s type=%s message_id=%s",
                        reminder.id, device.device_id, log.notif_type, message_id,
                    )
                else:
                    NotificationLogRepository.mark_fire_failed(db, log)

            except ValueError as e:
                if str(e) == "INVALID_FCM_TOKEN":
                    NotificationLogRepository.mark_fire_failed(db, log)
                else:
                    logger.error("ERROR in send_pending_reminder_notifications for log_id=%s: %s", log.id, e)
            except Exception as e:
                logger.error("ERROR in send_pending_reminder_notifications for log_id=%s: %s", log.id, e)
    finally:
        db.close()
