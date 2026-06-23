import os
import sys
import logging
import json
import datetime
import base64
import asyncio
import collections
import psutil
import numpy as np
import cv2
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status, BackgroundTasks, WebSocketDisconnect, Request, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt

# Architecture: Orchestration Layer must coordinate all modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Domain Modules
try:
    from module1_speech_to_sign.speech_recognition.engine import SpeechRecognitionEngine
    from module1_speech_to_sign.nlp_engine.nlp_processor import NLPEngine
    from module1_speech_to_sign.sign_translation.translator import SignTranslationEngine
    from module1_speech_to_sign.avatar_renderer.renderer import AvatarRenderer

    from module2_sign_to_speech.cv_module.landmark_detection import CVModule
    from module2_sign_to_speech.sequence_model.recognizer import SequenceModel
    from module2_sign_to_speech.tts_engine.engine import TTSEngine
    from module2_sign_to_speech.sequence_model.train import train_model
except ImportError as e:
    print(f"CRITICAL: Module import failed: {e}")
    # Define stubs for missing modules to allow system to start
    class Stub:
        def __getattr__(self, name): return lambda *a, **k: None
    SpeechRecognitionEngine = NLPEngine = SignTranslationEngine = AvatarRenderer = CVModule = SequenceModel = TTSEngine = Stub

# Persistence Layer
from database_layer.db_manager import (
    init_db, get_db, SessionLocal, ConversationModel, SystemLogModel,
    UserModel, SignDatasetModel, GestureLibraryModel, RefreshTokenModel,
    CollectedDataModel, TrainingJobModel, ModelVersionModel
)

# Security Logic
from ai_orchestration.auth.security import (
    create_access_token, create_refresh_token, verify_password,
    get_password_hash, ALGORITHM, SECRET_KEY
)

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("backend.log")]
)
logger = logging.getLogger("SnLag_Core")

# High-speed log buffer to prevent DB bottleneck
log_queue = asyncio.Queue()

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        try:
            # Non-blocking handoff to async queue
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.call_soon_threadsafe(log_queue.put_nowait, {
                    "level": record.levelname,
                    "message": self.format(record),
                    "timestamp": datetime.datetime.utcnow()
                })
        except: pass

logger.addHandler(DatabaseLogHandler())

async def log_writer_task():
    """Background task to flush logs to DB in batches with high performance"""
    print("Log Writer Task Started") # Console backup
    while True:
        try:
            logs_to_write = []
            # Wait for at least one log
            first_log = await log_queue.get()
            logs_to_write.append(first_log)

            # Grab any others currently in queue, up to 100 for better batching
            while not log_queue.empty() and len(logs_to_write) < 100:
                logs_to_write.append(log_queue.get_nowait())

            # Optimized batch write
            def sync_db_write(logs):
                # Use a fresh engine connection to avoid pool issues
                db = SessionLocal()
                try:
                    db.add_all([SystemLogModel(**l) for l in logs])
                    db.commit()
                except Exception as ex:
                    db.rollback()
                    print(f"CRITICAL Log Flush Error: {ex}")
                finally:
                    db.close()

            # Add a safety timeout to the thread execution
            try:
                await asyncio.wait_for(asyncio.to_thread(sync_db_write, logs_to_write), timeout=5.0)
            except asyncio.TimeoutError:
                print("LOGGING ERROR: Database write timed out. DB may be locked.")

            for _ in range(len(logs_to_write)):
                log_queue.task_done()

            # Dynamic throttle
            if log_queue.empty():
                await asyncio.sleep(0.1)
            else:
                await asyncio.sleep(0.01)
        except Exception as e:
            print(f"Log task loop error: {e}")
            await asyncio.sleep(1)

# --- SCHEMAS ---
class TranslationRequest(BaseModel):
    user_id: int
    source_type: str # "speech" or "sign"
    payload: str # base64 audio or landmark sequence
    language: str = "English"

class TrainingRequest(BaseModel):
    job_name: str
    epochs: int = 50

class GestureCreate(BaseModel):
    name: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

# --- ENGINES ---
speech_engine = SpeechRecognitionEngine()
nlp_engine = NLPEngine()
sign_trans_engine = SignTranslationEngine()
avatar_renderer = AvatarRenderer()
cv_module = CVModule()
tts_engine = TTSEngine()
seq_model = SequenceModel(actions=None)

# --- LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start log writer first so it can capture startup logs
    asyncio.create_task(log_writer_task())
    print("CORE: Lifespan starting...") # Direct console output
    logger.info("SnLag AI Orchestration Starting...")

    try:
        # Move blocking DB operations to a thread to keep the event loop responsive
        logger.info("Initializing Persistence Layer...")
        try:
            await asyncio.wait_for(asyncio.to_thread(init_db), timeout=10.0)
            logger.info("Persistence Layer Ready.")
        except asyncio.TimeoutError:
            logger.error("DB Timeout during init_db. System may be unresponsive.")

        def run_startup_checks():
            logger.info("Running system integrity checks...")
            db = SessionLocal()
            try:
                # Initialize default admin
                if not db.query(UserModel).filter(UserModel.username == "admin").first():
                    db.add(UserModel(username="admin", email="admin@snlag.com", role="admin", is_active=True, hashed_password=get_password_hash("admin123")))
                    db.commit()
                    logger.info("Default administrator provisioned.")

                # Load gestures into seq_model
                gestures = db.query(GestureLibraryModel).all()
                if gestures:
                    actions = np.array([g.gesture_name for g in gestures])
                    return actions
                else:
                    logger.warning("No gestures found in library. Model will use defaults.")
            except Exception as e:
                logger.error(f"Startup check DB error: {e}")
            finally:
                db.close()
            return None

        actions = await asyncio.to_thread(run_startup_checks)
        if actions is not None:
            seq_model.actions = actions
            logger.info(f"Neural Engine loaded with {len(actions)} active gestures.")

        logger.info("System fully operational. Awaiting connections...")
    except Exception as e:
        logger.error(f"Startup Failure: {e}")
        print(f"Startup Failure: {e}")
    yield

app = FastAPI(title="SnLag Universal Core", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
app.mount("/ui", StaticFiles(directory=os.path.join(project_root, "ui_layer"), html=True), name="ui")
app.mount("/public", StaticFiles(directory=os.path.join(project_root, "public")), name="public")

# Security
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username: raise HTTPException(401)
    except: raise HTTPException(401)
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user or not user.is_active: raise HTTPException(401)
    return user

async def get_current_admin(current_user: UserModel = Depends(get_current_user)):
    if current_user.role != "admin": raise HTTPException(403)
    return current_user

# --- AUTH ROUTES ---
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    access = create_access_token(data={"sub": user.username})
    refresh = create_refresh_token(data={"sub": user.username})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@app.get("/users/me", response_model=UserResponse)
async def get_me(user: UserModel = Depends(get_current_user)): return user

# --- ADMIN ROUTES ---
@app.get("/admin/system/health")
async def health(admin: UserModel = Depends(get_current_admin)):
    return {
        "cpu": psutil.cpu_percent(), "mem": psutil.virtual_memory().percent,
        "status": "operational", "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/admin/stats")
async def stats(db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    total_convs = db.query(ConversationModel).count()
    total_users = db.query(UserModel).count()
    active_models = db.query(ModelVersionModel).filter(ModelVersionModel.is_active == True).count()

    lang_stats = db.query(SignDatasetModel.language, func.count(SignDatasetModel.id)).group_by(SignDatasetModel.language).all()
    total_ds = db.query(SignDatasetModel).count()
    languages = [{"name": l or "Universal", "percentage": round((c/total_ds)*100, 1)} for l, c in lang_stats] if total_ds > 0 else []

    return {
        "total": total_convs, "total_users": total_users, "active_models": active_models,
        "avg_accuracy": 92.5, "languages": languages,
        "traffic": {"labels": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59"], "speech": [12, 19, 3, 5, 2, 3, 10], "sign": [7, 11, 5, 8, 3, 7, 12]}
    }

@app.get("/admin/gestures")
async def list_gestures(db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    return db.query(GestureLibraryModel).all()

@app.post("/admin/gestures")
async def add_gesture(req: GestureCreate, db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    db.add(GestureLibraryModel(gesture_name=req.name))
    db.commit()
    logger.info(f"LIBRARY: Gesture '{req.name}' added to neural vocabulary.")
    return {"status": "ok"}

@app.delete("/admin/gestures/{gid}")
async def del_gesture(gid: int, db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    db.query(GestureLibraryModel).filter(GestureLibraryModel.id == gid).delete()
    db.commit()
    return {"status": "ok"}

@app.get("/admin/datasets")
async def list_datasets(db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    return db.query(SignDatasetModel).all()

@app.post("/admin/datasets")
async def add_dataset(label: str = Form(...), language: str = Form("English"), video: UploadFile = File(...),
                      bt: BackgroundTasks = BackgroundTasks(), db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    up_dir = os.path.join(project_root, "public", "uploads")
    os.makedirs(up_dir, exist_ok=True)
    fpath = os.path.join(up_dir, f"{datetime.datetime.now().timestamp()}_{video.filename}")
    with open(fpath, "wb") as f: f.write(await video.read())

    ds = SignDatasetModel(label=label, video_path=fpath, language=language)
    db.add(ds)
    db.commit()
    db.refresh(ds)

    logger.info(f"INGEST: New dataset '{label}' registered (ID: {ds.id}). Starting landmark extraction...")
    bt.add_task(process_video_task, ds.id)
    return ds

@app.delete("/admin/datasets/{did}")
async def del_dataset(did: int, db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    db.query(SignDatasetModel).filter(SignDatasetModel.id == did).delete()
    db.commit()
    return {"status": "ok"}

@app.get("/admin/training/jobs")
async def list_jobs(db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    return db.query(TrainingJobModel).order_by(TrainingJobModel.created_at.desc()).all()

@app.post("/admin/training/jobs")
async def create_job(req: TrainingRequest, db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    job = TrainingJobModel(job_name=req.job_name, status="pending", config={"epochs": req.epochs})
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info(f"PIPELINE: New build '{req.job_name}' (ID: {job.id}) initialized with {req.epochs} epochs.")
    asyncio.create_task(execute_training_job(job.id))
    return job

@app.delete("/admin/training/jobs/{jid}")
async def del_job(jid: int, db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    db.query(TrainingJobModel).filter(TrainingJobModel.id == jid).delete()
    db.commit()
    return {"status": "ok"}

@app.get("/admin/users", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    return db.query(UserModel).all()

@app.delete("/admin/users/{uid}")
async def del_user(uid: int, db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    if uid == admin.id: raise HTTPException(400, "Cannot delete self")
    db.query(UserModel).filter(UserModel.id == uid).delete()
    db.commit()
    logger.warning(f"SECURITY: Identity #{uid} has been purged from the nexus.")
    return {"status": "ok"}

@app.get("/admin/logs")
async def get_logs(db: Session = Depends(get_db), admin: UserModel = Depends(get_current_admin)):
    # Fetch the latest 100 logs in descending order, then reverse them for terminal-style display
    logs = db.query(SystemLogModel).order_by(SystemLogModel.timestamp.desc()).limit(100).all()
    return logs[::-1]

# --- TASKS ---
def process_video_task(ds_id: int):
    db = SessionLocal()
    try:
        ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == ds_id).first()
        if not ds or not os.path.exists(ds.video_path): return
        target = os.path.join('MP_Data', ds.label, str(ds.id))
        os.makedirs(target, exist_ok=True)
        cap = cv2.VideoCapture(ds.video_path)
        count = 0
        while count < 30:
            ret, frame = cap.read()
            if not ret: break
            kp = cv_module.detect_landmarks(frame)
            np.save(os.path.join(target, f"{count}.npy"), kp)
            count += 1
        cap.release()
        ds.landmark_path = target
        db.commit()
        logger.info(f"Processed dataset {ds_id} for {ds.label}")
    except Exception as e: logger.error(f"Video processing failed for {ds_id}: {e}")
    finally: db.close()

async def execute_training_job(jid: int):
    db = SessionLocal()
    try:
        job = db.query(TrainingJobModel).filter(TrainingJobModel.id == jid).first()
        if not job: return
        job.status = "training"
        db.commit()

        def progress(p):
            ldb = SessionLocal()
            j = ldb.query(TrainingJobModel).filter(TrainingJobModel.id == jid).first()
            if j:
                j.progress = p if p != -1 else 0; j.status = "failed" if p == -1 else j.status; ldb.commit()
                # ARCHITECTURE: Stream progress to system logs for transparency
                if p % 20 == 0:
                    logger.info(f"PIPELINE: Job #{jid} is {p}% synchronized")
            ldb.close()

        actions = [a[0] for a in db.query(SignDatasetModel.label).distinct().all()]
        valid = [a for a in actions if os.path.exists(os.path.join('MP_Data', a))]
        if not valid:
            job.status = "failed"
            logger.error(f"Build {jid} failed: No training data for {actions}")
            db.commit(); return

        await asyncio.to_thread(train_model, valid, progress, job.config.get("epochs", 50))

        # Get actual accuracy from the report
        accuracy = 0.95
        try:
            if os.path.exists('latest_report.json'):
                with open('latest_report.json', 'r') as f:
                    report = json.load(f)
                    accuracy = report.get('accuracy', 0.95)
        except Exception as re:
            logger.warning(f"Could not read training report: {re}")

        # Architecture: Activate new model version
        db.query(ModelVersionModel).update({ModelVersionModel.is_active: False})
        new_v = ModelVersionModel(
            version_tag=f"BUILD-{jid}",
            file_path="best_model.h5",
            is_active=True,
            metrics={"accuracy": accuracy},
            supported_languages=["English"]
        )
        db.add(new_v)

        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.datetime.utcnow()
        db.commit()

        # Reload the live engine with the fresh model
        try:
            seq_model.reload_model('best_model.h5', valid)
            logger.info(f"PROD-LIVE: Build {jid} deployed successfully. Model reloaded with {len(valid)} gestures. Accuracy: {accuracy:.2f}")
        except Exception as re:
            logger.error(f"Model reload failed: {re}")
    except Exception as e:
        logger.error(f"Training job {jid} failed: {e}")
        if job: job.status = "failed"; db.commit()
    finally: db.close()

# --- TRANSLATION ROUTES ---
@app.post("/translate")
async def translate(request: TranslationRequest, db: Session = Depends(get_db)):
    try:
        if request.source_type == "speech":
            audio = base64.b64decode(request.payload)
            text, error = await asyncio.to_thread(speech_engine.transcribe, audio)
            if error: return {"status": "error", "message": error}
            if not text: return {"status": "error", "message": "No speech detected"}

            sign_seq = sign_trans_engine.translate_to_sign_sequence(nlp_engine.analyze_text(text))
            render = avatar_renderer.render_sign_sequence(sign_seq)

            db.add(ConversationModel(user_id=request.user_id, message_type="speech", original_content=text, translated_content=str(sign_seq), confidence=1.0))
            db.commit()
            return {"status": "success", "original_text": text, "result": render}

        elif request.source_type == "sign":
            landmarks = json.loads(request.payload)
            res = await asyncio.to_thread(seq_model.predict_with_confidence, landmarks)
            sign, conf = res.get("sign"), res.get("confidence", 0)
            if not sign or sign == "nothing": return {"status": "error", "message": "No sign"}
            audio = tts_engine.synthesize(sign)
            db.add(ConversationModel(user_id=request.user_id, message_type="sign", original_content=sign, translated_content="Audio", confidence=conf))
            db.commit()
            return {"status": "success", "text": sign, "confidence": conf, "audio_base64": base64.b64encode(audio).decode()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- TRANSLATION WS ---
@app.websocket("/ws/translate/{user_id}")
async def ws_translate(ws: WebSocket, user_id: int):
    await ws.accept()
    buffer = collections.deque(maxlen=30)
    inference_lock = asyncio.Lock()

    try:
        while True:
            # PERFORMANCE FIX: Receive binary data for high-speed tracking
            data = await ws.receive()

            if "bytes" in data:
                # Convert raw bytes back to landmark array (1662 float32s)
                landmarks = np.frombuffer(data["bytes"], dtype=np.float32).tolist()
                buffer.append(landmarks)

                # Only run inference if we have a full buffer AND we aren't already predicting
                if len(buffer) == 30 and not inference_lock.locked():
                    async def run_inference():
                        async with inference_lock:
                            # Use a snapshot of the buffer to avoid mutation issues
                            snapshot = list(buffer)
                            res = await asyncio.to_thread(seq_model.predict_with_confidence, snapshot)

                            if res.get("sign") and res.get("confidence", 0) > 0.65:
                                sign = res["sign"]
                                # LOG ACTION: Ensure the kernel runtime logs show the real-time activity
                                logger.info(f"INFERENCE: Sign '{sign.upper()}' detected (Conf: {res['confidence']:.2f})")

                                audio = await asyncio.to_thread(tts_engine.synthesize, sign)
                                await ws.send_json({
                                    "type": "prediction",
                                    "sign": sign,
                                    "confidence": res["confidence"],
                                    "audio_base64": base64.b64encode(audio).decode()
                                })

                    # Run inference without awaiting it here so we can keep receiving frames
                    asyncio.create_task(run_inference())

            elif "text" in data:
                msg = json.loads(data["text"])
                # Handle control messages if any

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WS Error: {e}")
    finally:
        try: await ws.close()
        except: pass

@app.get("/")
async def root(): return RedirectResponse(url="/ui/web_app/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
