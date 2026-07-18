# notification_service.py

import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from .firebase_service import send_push_notification
from app.db.repositories.device_repository import DeviceRepository
from app.db.session import SessionLocal
from app.astrology import (
    get_today_nakshatra_end_datetime,
    get_planet_positions,
)

# In-memory cache to prevent duplicate notifications
# Key format: (device_token, notification_type, date)
_SENT_CACHE = set()
logger = logging.getLogger("notification")


def _already_sent(device_token: str, notif_type: str, date_str: str) -> bool:
    return (device_token, notif_type, date_str) in _SENT_CACHE


def _mark_sent(device_token: str, notif_type: str, date_str: str):
    _SENT_CACHE.add((device_token, notif_type, date_str))


def _deactivate_device_for_invalid_token(db, device):
    device.is_active = False


def _deactivate_invalid_devices(db, device_ids: list[str]):
    for device_id in dict.fromkeys(device_ids):
        device = DeviceRepository.get_device_by_device_id(db, device_id)
        if device is None:
            continue

        _deactivate_device_for_invalid_token(db, device)

    db.commit()

    for device_id in dict.fromkeys(device_ids):
        logger.warning(
            "device_deactivated_invalid_fcm device_id=%s",
            device_id,
        )


def send_daily_notifications():
    db = SessionLocal()

    try:
        devices = DeviceRepository.get_active_devices(db)
        invalid_device_ids = []

        now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))

        for device in devices:
            try:
                # Skip devices without location/timezone information
                if (
                    not device.timezone
                    or device.latitude is None
                    or device.longitude is None
                ):
                    continue

                tz = ZoneInfo(device.timezone)
                local_now = now_utc.astimezone(tz)
                today_str = local_now.date().isoformat()

                # Try to compute today's nakshatra name for this device
                nakshatra_name = ""
                try:
                    panchang = get_planet_positions(
                        year=local_now.year,
                        month=local_now.month,
                        day=local_now.day,
                        hour=local_now.hour + local_now.minute / 60.0,
                        lat=device.latitude,
                        lon=device.longitude,
                        tz_offset=local_now.utcoffset().total_seconds() / 3600,
                    )
                    nakshatra_name = panchang.get("moon", {}).get("nakshatra") or ""
                except Exception as astro_err:
                    logger.debug(
                        "Failed to compute nakshatra for device %s: %s",
                        device.device_id,
                        astro_err,
                    )

                # -------------------------
                # 🌅 Morning Window (6:00–6:05)
                # -------------------------
                if local_now.hour == 6 and 0 <= local_now.minute <= 5:
                    notif_type = "DAILY_NAKSHATRA"

                    if not _already_sent(device.fcm_token, notif_type, today_str):
                        message_id = send_push_notification(
                            token=device.fcm_token,
                            title="Nakshatra Update ✨",
                            body=(
                                f"Today's Nakshatra: {nakshatra_name} 🌙"
                                if nakshatra_name
                                else "Your daily nakshatra update is ready ✨"
                            ),
                            data={
                                "type": notif_type,
                                "date": today_str,
                                "nakshatra": nakshatra_name,
                                "navigateTo": "Home",
                                "deviceId": str(device.device_id),
                                "icon": "moon_stars",
                                "emoji": "✨",
                                "style": "daily",
                            },
                            image_url="https://images.unsplash.com/photo-1532968961962-8a0cb3a2d4f5",
                        )

                        if message_id:
                            _mark_sent(device.fcm_token, notif_type, today_str)
                            logger.info(
                                "notification_sent device_id=%s type=%s date=%s message_id=%s",
                                device.device_id,
                                notif_type,
                                today_str,
                                message_id,
                            )

                # -------------------------
                # 🧪 Every 5 Minutes Window
                # Temporary test block. Safe to comment out or delete later.
                # -------------------------
                # if local_now.minute % 5 == 0:
                #     notif_type = "DAILY_NAKSHATRA"
                #     bucket_str = local_now.replace(
                #         second=0,
                #         microsecond=0,
                #     ).isoformat()

                #     if not _already_sent(device.fcm_token, notif_type, bucket_str):
                #         message_id = send_push_notification(
                #             token=device.fcm_token,
                #             title="Nakshatra Update ✨",
                #             body=(
                #                 f"Today's Nakshatra: {nakshatra_name} 🌙"
                #                 if nakshatra_name
                #                 else "Your daily nakshatra update is ready ✨"
                #             ),
                #             data={
                #                 "type": notif_type,
                #                 "date": today_str,
                #                 "nakshatra": nakshatra_name,
                #                 "navigateTo": "Home",
                #                 "deviceId": str(device.device_id),
                #                 "icon": "moon_stars",
                #                 "emoji": "✨",
                #                 "style": "daily",
                #             },
                #             image_url="https://images.unsplash.com/photo-1532968961962-8a0cb3a2d4f5",
                #         )

                #         if message_id:
                #             _mark_sent(device.fcm_token, notif_type, bucket_str)
                #             logger.info(
                #                 "notification_sent device_id=%s type=%s date=%s message_id=%s",
                #                 device.device_id,
                #                 notif_type,
                #                 bucket_str,
                #                 message_id,
                #             )

                # -------------------------
                # ⏳ Nakshatra End Window (±2 min)
                # -------------------------
                nak_end_dt = get_today_nakshatra_end_datetime(
                    lat=device.latitude,
                    lon=device.longitude,
                    timezone_str=device.timezone,
                )

                if nak_end_dt:
                    diff_seconds = abs((local_now - nak_end_dt).total_seconds())

                    if diff_seconds <= 120:
                        notif_type = "NAKSHATRA_END"

                        if not _already_sent(device.fcm_token, notif_type, today_str):
                            message_id = send_push_notification(
                                token=device.fcm_token,
                                title="Nakshatra Ending Soon ⏳",
                                body=(
                                    f"{nakshatra_name} ends soon 🌠"
                                    if nakshatra_name
                                    else "Your current nakshatra is about to end ⏳"
                                ),
                                data={
                                    "type": notif_type,
                                    "date": today_str,
                                    "nakshatra": nakshatra_name,
                                    "navigateTo": "Home",
                                    "deviceId": str(device.device_id),
                                    "icon": "hourglass",
                                    "emoji": "⏳",
                                    "style": "ending",
                                },
                                image_url="https://images.unsplash.com/photo-1519681393784-d120267933ba",
                            )

                            if message_id:
                                _mark_sent(device.fcm_token, notif_type, today_str)
                                logger.info(
                                    "notification_sent device_id=%s type=%s date=%s message_id=%s",
                                    device.device_id,
                                    notif_type,
                                    today_str,
                                    message_id,
                                )
            except ValueError as e:
                if str(e) == "INVALID_FCM_TOKEN":
                    invalid_device_ids.append(device.device_id)
                else:
                    logger.error(
                        "ERROR in notification_service.send_daily_notifications for device_id=%s: %s",
                        device.device_id,
                        e,
                    )
            except Exception as e:
                logger.error(
                    "ERROR in notification_service.send_daily_notifications for device_id=%s: %s",
                    device.device_id,
                    e,
                )

        if invalid_device_ids:
            try:
                _deactivate_invalid_devices(db, invalid_device_ids)
            except Exception as e:
                db.rollback()
                logger.error(
                    "ERROR in notification_service._deactivate_invalid_devices for devices=%s: %s",
                    ",".join(dict.fromkeys(invalid_device_ids)),
                    e,
                )

    finally:
        db.close()
