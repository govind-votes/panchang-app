from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ---------- REQUEST SCHEMAS ----------

class ReminderCreateRequest(BaseModel):
    device_id: str
    tithi: Optional[str] = None
    var: Optional[str] = None
    yoga: Optional[str] = None
    nakshatra: Optional[str] = None
    note: Optional[str] = None
    before_time: str = "20:00"
    day_of_time: str = "06:00"


class ReminderUpdateRequest(BaseModel):
    device_id: str
    tithi: Optional[str] = None
    var: Optional[str] = None
    yoga: Optional[str] = None
    nakshatra: Optional[str] = None
    note: Optional[str] = None
    before_time: str = "20:00"
    day_of_time: str = "06:00"


class ReminderDeleteRequest(BaseModel):
    device_id: str


# ---------- RESPONSE SCHEMAS ----------

class ReminderResponse(BaseModel):
    id: int
    device_id: str
    tithi: Optional[str]
    var: Optional[str]
    yoga: Optional[str]
    nakshatra: Optional[str]
    note: Optional[str]
    before_time: str
    day_of_time: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderHistoryEntry(BaseModel):
    id: int
    reminder_id: Optional[int]
    notif_type: str
    matched_date: Optional[str]
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True
