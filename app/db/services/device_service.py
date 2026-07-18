from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo

from app.db.models.device import Device
from app.db.repositories.device_repository import DeviceRepository


TIMEZONE_ALIASES = {
    "Asia/Calcutta": "Asia/Kolkata",
}


def normalize_timezone(timezone: str | None) -> str:
    """
    Normalize timezone to a valid IANA timezone.

    - Converts legacy aliases (Asia/Calcutta -> Asia/Kolkata)
    - Falls back to UTC if timezone is invalid or missing
    """

    if not timezone:
        return "UTC"

    timezone = TIMEZONE_ALIASES.get(timezone, timezone)

    try:
        ZoneInfo(timezone)
        return timezone
    except Exception:
        return "UTC"


class DeviceService:
    @staticmethod
    def register_or_update_device(
        db: Session,
        device_id: str,
        platform: str,
        timezone: str,
        fcm_token: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> Device:

        timezone = normalize_timezone(timezone)
        existing_device = DeviceRepository.get_device_by_device_id(
            db=db, device_id=device_id
        )

        if existing_device:
            # Update existing device
            if platform and platform != "unknown":
                existing_device.platform = platform
            existing_device.timezone = timezone
            if fcm_token:
                existing_device.fcm_token = fcm_token
                existing_device.is_active = True
            existing_device.latitude = latitude
            existing_device.longitude = longitude
            existing_device.last_seen_at = datetime.utcnow()

            return DeviceRepository.update_device(db, existing_device)

        if not fcm_token:
            raise ValueError("FCM token is required for new device")

        # Create new device
        new_device = Device(
            device_id=device_id,
            platform=platform,
            timezone=timezone,
            fcm_token=fcm_token,
            latitude=latitude,
            longitude=longitude,
            last_seen_at=datetime.utcnow(),
        )

        return DeviceRepository.create_device(db, new_device)
