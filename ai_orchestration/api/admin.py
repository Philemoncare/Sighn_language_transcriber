import os
import psutil
import datetime
import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from ai_orchestration.api.deps import get_db, get_current_admin
from ai_orchestration.core.config import UPLOADS_DIR, PROJECT_ROOT
from database_layer.db_manager import (
    UserModel, ConversationModel, ModelVersionModel, SignDatasetModel,
    GestureLibraryModel, TrainingJobModel, SystemLogModel, CollectedDataModel,
    AppSettingModel, check_db_health
)

router = APIRouter(prefix="/admin", dependencies=[Depends(get_current_admin)])
logger = logging.getLogger("SnLag_Admin")

# --- REQUEST MODELS ---
class GestureCreate(BaseModel):
    name: str

class TrainingJobCreate(BaseModel):
    job_name: str
    epochs: int = 50

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    preferences: Optional[dict] = None

class AppSettingUpdate(BaseModel):
    value: dict
    description: Optional[str] = None

class ChunkUploadInit(BaseModel):
    filename: str
    total_size: int
    label: str
    category: Optional[str] = "Sign"
    language: Optional[str] = "English"
    description: Optional[str] = None
    tags: Optional[str] = None
    file_hash: Optional[str] = None

# --- ENDPOINTS ---

@router.get("/system/health")
async def get_health(db: Session = Depends(get_db)):
    try:
        from ai_orchestration.services.orchestrator import orchestrator
        active_job = db.query(TrainingJobModel).filter(TrainingJobModel.status == "training", TrainingJobModel.is_deleted == False).first()

        # Safe psutil usage
        cpu = 0
        mem = 0
        disk = 0
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('.').percent
        except: pass

        return {
            "cpu": cpu,
            "mem": mem,
            "disk": disk,
            "db_connected": check_db_health(),
            "model_loaded": orchestrator.seq_model.model is not None if hasattr(orchestrator, 'seq_model') else False,
            "training_active": active_job is not None,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health Check Failure: {e}")
        return {
            "cpu": 0, "mem": 0, "disk": 0,
            "db_connected": False,
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Optimized cross-DB statistics engine"""
    try:
        total_convs = db.query(ConversationModel).count()
        total_users = db.query(UserModel).filter(UserModel.is_deleted == False).count()

        accuracy = 92.5
        active_model = db.query(ModelVersionModel).filter(ModelVersionModel.is_active == True, ModelVersionModel.is_deleted == False).order_by(ModelVersionModel.created_at.desc()).first()
        if active_model and active_model.metrics and isinstance(active_model.metrics, dict):
            accuracy = active_model.metrics.get("accuracy", 0.925) * 100

        today = datetime.date.today()
        labels, speech_counts, sign_counts = [], [], []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            labels.append(day.strftime("%b %d"))

            s_count = db.query(ConversationModel).filter(
                func.date(ConversationModel.timestamp) == day,
                ConversationModel.message_type == 'speech'
            ).count()

            sn_count = db.query(ConversationModel).filter(
                func.date(ConversationModel.timestamp) == day,
                ConversationModel.message_type == 'sign'
            ).count()

            speech_counts.append(s_count)
            sign_counts.append(sn_count)

        return {
            "total": total_convs,
            "total_users": total_users,
            "active_models": db.query(ModelVersionModel).filter(ModelVersionModel.is_active == True, ModelVersionModel.is_deleted == False).count(),
            "avg_accuracy": round(accuracy, 1),
            "traffic": {"labels": labels, "speech": speech_counts, "sign": sign_counts}
        }
    except Exception as e:
        logger.error(f"Stats Panic: {e}")
        return {"total": 0, "total_users": 0, "active_models": 0, "avg_accuracy": 0, "traffic": {"labels":[], "speech":[], "sign":[]}}

@router.get("/settings")
async def list_settings(db: Session = Depends(get_db)):
    return db.query(AppSettingModel).all()

@router.put("/settings/{key}")
async def update_setting(key: str, data: AppSettingUpdate, db: Session = Depends(get_db)):
    setting = db.query(AppSettingModel).filter(AppSettingModel.key == key).first()
    if not setting:
        setting = AppSettingModel(key=key)
        db.add(setting)

    setting.value = data.value
    if data.description:
        setting.description = data.description
    db.commit()
    logger.info(f"System: App setting '{key}' updated by admin.")
    return {"status": "ok"}

@router.post("/seed-gestures")
async def seed_gestures(db: Session = Depends(get_db)):
    from ai_orchestration.services.orchestrator import orchestrator
    vocab = ["hello", "thanks", "i_love_you", "please", "sorry"]
    for v in vocab:
        if not db.query(GestureLibraryModel).filter(GestureLibraryModel.gesture_name == v, GestureLibraryModel.is_deleted == False).first():
            db.add(GestureLibraryModel(gesture_name=v))
    db.commit()
    orchestrator.sync_vocabulary(db)
    return {"status": "ok", "message": "Vocabulary synchronized."}

@router.get("/gestures")
async def list_gestures(db: Session = Depends(get_db), q: Optional[str] = None):
    query = db.query(GestureLibraryModel).filter(GestureLibraryModel.is_deleted == False)
    if q:
        query = query.filter(GestureLibraryModel.gesture_name.ilike(f"%{q}%"))
    return query.all()

@router.post("/gestures")
async def add_gesture(data: GestureCreate, db: Session = Depends(get_db)):
    from ai_orchestration.services.orchestrator import orchestrator
    new_g = GestureLibraryModel(gesture_name=data.name)
    db.add(new_g)
    db.commit()
    orchestrator.sync_vocabulary(db)
    return {"status": "ok"}

@router.put("/gestures/{id}")
async def update_gesture(id: int, data: GestureCreate, db: Session = Depends(get_db)):
    from ai_orchestration.services.orchestrator import orchestrator
    g = db.query(GestureLibraryModel).filter(GestureLibraryModel.id == id, GestureLibraryModel.is_deleted == False).first()
    if not g: raise HTTPException(404, "Not found")
    g.gesture_name = data.name
    db.commit()
    orchestrator.sync_vocabulary(db)
    return {"status": "ok"}

@router.delete("/gestures/{id}")
async def delete_gesture(id: int, db: Session = Depends(get_db)):
    from ai_orchestration.services.orchestrator import orchestrator
    g = db.query(GestureLibraryModel).filter(GestureLibraryModel.id == id).first()
    if g:
        g.is_deleted = True
        db.commit()
    orchestrator.sync_vocabulary(db)
    return {"status": "ok"}

@router.get("/datasets")
async def list_datasets(db: Session = Depends(get_db), q: Optional[str] = None):
    query = db.query(SignDatasetModel).filter(SignDatasetModel.is_deleted == False)
    if q:
        query = query.filter(SignDatasetModel.label.ilike(f"%{q}%"))
    return query.all()

@router.post("/datasets")
async def register_dataset(
    bt: BackgroundTasks,
    label: str = Form(...),
    language: str = Form("English"),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    from ai_orchestration.services.cv_tasks import process_video_task
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    existing = db.query(SignDatasetModel).filter(
        SignDatasetModel.label == label.strip(),
        SignDatasetModel.status == "completed",
        SignDatasetModel.is_deleted == False
    ).first()

    if existing:
        raise HTTPException(400, detail=f"A validated dataset for '{label}' already exists.")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{timestamp}_{video.filename.replace(' ', '_')}"
    fpath = os.path.join(UPLOADS_DIR, fname)

    with open(fpath, "wb") as f:
        content = await video.read()
        f.write(content)

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    ds = SignDatasetModel(
        label=label.strip(),
        video_path=fpath,
        language=language,
        category=category,
        description=description,
        tags=tag_list,
        status="queued",
        progress=0
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    bt.add_task(process_video_task, ds.id)
    return ds

@router.post("/datasets/upload/init")
async def init_chunked_upload(data: ChunkUploadInit, db: Session = Depends(get_db)):
    """Requirement 1: Initialize chunked upload for stability"""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    logger.info(f"Init Upload: {data.filename} ({data.total_size} bytes) for {data.label}")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{timestamp}_{data.filename.replace(' ', '_')}"
    fpath = os.path.join(UPLOADS_DIR, fname)

    tag_list = [t.strip() for t in data.tags.split(",")] if data.tags else []

    ds = SignDatasetModel(
        label=data.label.strip(),
        video_path=fpath,
        language=data.language,
        category=data.category,
        description=data.description,
        tags=tag_list,
        status="uploading",
        progress=0,
        extraction_metadata={"filename": data.filename, "total_size": data.total_size, "expected_hash": data.file_hash}
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return {"upload_id": ds.id, "path": fpath}

@router.post("/datasets/upload/chunk/{upload_id}")
async def upload_chunk(
    upload_id: int,
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Requirement 1: Receive upload chunk"""
    ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == upload_id).first()
    if not ds:
        logger.error(f"Upload Chunk Failed: session {upload_id} not found")
        raise HTTPException(404, "Upload session not found")

    try:
        # Append chunk to file
        with open(ds.video_path, "ab") as f:
            content = await chunk.read()
            f.write(content)

        # Update progress based on file size vs total_size
        current_size = os.path.getsize(ds.video_path)
        meta = ds.extraction_metadata or {}
        total_size = meta.get("total_size", 1)
        ds.progress = int((current_size / total_size) * 100) if total_size > 0 else 0
        db.commit()

        logger.info(f"Upload Chunk {chunk_index} received for ID {upload_id}. Size: {current_size}/{total_size}")
        return {"status": "ok", "bytes_received": current_size}
    except Exception as e:
        logger.error(f"Chunk Upload Critical Failure for ID {upload_id}: {e}")
        raise HTTPException(500, str(e))

@router.post("/datasets/upload/finalize/{upload_id}")
async def finalize_upload(upload_id: int, bt: BackgroundTasks, db: Session = Depends(get_db)):
    """Requirement 1 & 8: Verify integrity and trigger extraction"""
    ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == upload_id).first()
    if not ds: raise HTTPException(404, "Upload session not found")

    logger.info(f"Finalizing Upload ID {upload_id} ('{ds.label}')")

    # Verify file existence and size
    if not os.path.exists(ds.video_path):
         raise HTTPException(400, "File missing on server")

    expected_size = ds.extraction_metadata.get("total_size")
    actual_size = os.path.getsize(ds.video_path)

    if expected_size and actual_size < expected_size:
        raise HTTPException(400, f"Incomplete upload. Expected {expected_size}, got {actual_size}")

    # Optional Hash Verification (Requirement 1)
    expected_hash = ds.extraction_metadata.get("expected_hash")
    if expected_hash:
        import hashlib
        sha256 = hashlib.sha256()
        with open(ds.video_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        if sha256.hexdigest() != expected_hash:
            raise HTTPException(400, "Integrity Check Failed: Checksum mismatch")

    ds.status = "queued"
    ds.progress = 0
    db.commit()

    from ai_orchestration.services.cv_tasks import process_video_task
    bt.add_task(process_video_task, ds.id)

    return {"status": "ok", "message": "Upload verified. Extraction queued."}

@router.post("/datasets/{id}/retry")
async def retry_extraction(id: int, bt: BackgroundTasks, db: Session = Depends(get_db)):
    """Requirement 5: Retry extraction only without full upload"""
    ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == id).first()
    if not ds: raise HTTPException(404, "Dataset not found")

    # Reset status and progress
    ds.status = "queued"
    ds.progress = 0
    ds.extraction_metadata = {}
    db.commit()

    from ai_orchestration.services.cv_tasks import process_video_task
    bt.add_task(process_video_task, ds.id)
    return {"status": "ok", "message": "Extraction task re-queued"}

@router.delete("/datasets/{id}")
async def delete_dataset(id: int, bt: BackgroundTasks, db: Session = Depends(get_db)):
    from ai_orchestration.services.cv_tasks import cleanup_dataset_files
    ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == id).first()
    if not ds: return {"status": "error", "message": "Not found"}

    ds.is_deleted = True
    db.commit()

    if ds.video_path and os.path.exists(ds.video_path):
        try: os.remove(ds.video_path)
        except: pass

    bt.add_task(cleanup_dataset_files, ds.id, ds.label)
    return {"status": "ok"}

@router.get("/harvest")
async def list_harvest(db: Session = Depends(get_db)):
    return db.query(CollectedDataModel).filter(CollectedDataModel.is_validated == False, CollectedDataModel.is_deleted == False).all()

@router.get("/models")
async def list_models(db: Session = Depends(get_db)):
    return db.query(ModelVersionModel).filter(ModelVersionModel.is_deleted == False).order_by(ModelVersionModel.created_at.desc()).all()

@router.get("/training/jobs")
async def list_jobs(db: Session = Depends(get_db)):
    return db.query(TrainingJobModel).filter(TrainingJobModel.is_deleted == False).order_by(TrainingJobModel.created_at.desc()).all()

@router.delete("/training/jobs/{id}")
async def delete_job(id: int, db: Session = Depends(get_db)):
    job = db.query(TrainingJobModel).filter(TrainingJobModel.id == id).first()
    if job:
        job.is_deleted = True
        db.commit()
    return {"status": "ok"}

@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    return db.query(UserModel).filter(UserModel.is_deleted == False).all()

@router.put("/users/{id}")
async def update_user(id: int, data: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == id, UserModel.is_deleted == False).first()
    if not user: raise HTTPException(404, "Not found")

    if data.role: user.role = data.role
    if data.is_active is not None: user.is_active = data.is_active
    if data.preferences:
        prefs = user.preferences or {}
        prefs.update(data.preferences)
        user.preferences = prefs

    db.commit()
    return {"status": "ok"}

@router.delete("/users/{id}")
async def delete_user(id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if user:
        user.is_deleted = True
        db.commit()
    return {"status": "ok"}

@router.get("/logs")
async def get_logs(
    db: Session = Depends(get_db),
    level: Optional[str] = None,
    service: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    query = db.query(SystemLogModel)

    if level:
        query = query.filter(SystemLogModel.level == level.upper())
    if service:
        query = query.filter(SystemLogModel.service == service.lower())
    if q:
        query = query.filter(SystemLogModel.message.ilike(f"%{q}%"))

    logs = query.order_by(SystemLogModel.timestamp.desc()).offset(offset).limit(limit).all()
    return logs

@router.delete("/logs")
async def clear_logs(db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM system_logs"))
    db.commit()
    return {"status": "ok"}
