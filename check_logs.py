from database_layer.db_manager import SessionLocal, SystemLogModel
import sys

db = SessionLocal()
logs = db.query(SystemLogModel).order_by(SystemLogModel.timestamp.desc()).limit(10).all()
for l in logs:
    print(f"{l.level}: {l.message}")
db.close()
