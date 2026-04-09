from app import app, db
from models import MonitorScheduledTask, MonitorSystemLog

print("Models imported OK")

with app.app_context():
    db.create_all()
    print("Tables created/updated OK")