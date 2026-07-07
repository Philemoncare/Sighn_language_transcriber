import sys
import os
sys.path.append(r'c:\SnLag')
from database_layer.db_manager import SessionLocal, SignDatasetModel

db = SessionLocal()
rows = db.query(SignDatasetModel).order_by(SignDatasetModel.created_at.desc()).limit(20).all()
print('count', len(rows))
for r in rows:
    print('ID', r.id, '| label', r.label, '| status', r.status, '| progress', r.progress, '| video', bool(r.video_path), '| landmark', bool(r.landmark_path), '| quality', r.quality_score, '| meta', r.extraction_metadata)
db.close()
