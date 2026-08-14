from app.db.session import engine
from app.db.base import Base
from app.db.models.device import Device
from app.db.models.reminder import Reminder
from app.db.models.notification_log import NotificationLog

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()