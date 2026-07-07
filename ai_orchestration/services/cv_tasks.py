import os
import cv2
import shutil
import re
import numpy as np
import logging
import threading
import time
import zipfile
import datetime
import hashlib
import traceback
import redis
import json
from sqlalchemy.orm import Session
from ai_orchestration.core.config import PROJECT_ROOT, MP_DATA_ROOT, UPLOADS_DIR, CELERY_BROKER_URL
from ai_orchestration.core.celery_app import celery_app
from database_layer.db_manager import SessionLocal, SignDatasetModel, TrainingJobModel
from module2_sign_to_speech.cv_module.landmark_detection import CVModule

logger = logging.getLogger("SnLag_ExtractionEngine")
cv_semaphore = threading.Semaphore(1)

# Global CV instances for resource reuse (Requirement: Initialize only once)
_cv_instance_static = None
_cv_instance_video = None
_cv_lock = threading.Lock()

def get_cv_module(static_mode=False):
    global _cv_instance_static, _cv_instance_video
    with _cv_lock:
        if static_mode:
            if _cv_instance_static is None:
                _cv_instance_static = CVModule(static_mode=True)
            return _cv_instance_static
        else:
            if _cv_instance_video is None:
                _cv_instance_video = CVModule(static_mode=False)
            return _cv_instance_video

def sanitize_folder_name(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9\s-]', '', name)
    return clean.strip() or "unnamed_dataset"

def _broadcast_status(dataset_id: str, progress: int, stage: str, metadata: dict = None):
    """
    Broadcast status to all connected admins via Redis Pub/Sub.
    """
    try:
        message = {
            "type": "dataset_update",
            "id": dataset_id,
            "progress": int(progress),
            "stage": stage,
            "status": stage.upper(),
            "_ws_scope": "admin",
            "metadata": metadata or {}
        }

        # Force protocol=2 for compatibility
        r = redis.from_url(CELERY_BROKER_URL, protocol=2, socket_timeout=5)
        r.publish("snlag_broadcast", json.dumps(message))
    except Exception as e:
        logger.debug(f"Broadcast Failure [DS#{dataset_id}]: {e}")

def cleanup_dataset_files(dataset_id: str, label: str, landmark_path: str = None):
    """Safety cleanup of all physical assets associated with a dataset"""
    try:
        target_dir = landmark_path or os.path.join(MP_DATA_ROOT, sanitize_folder_name(label), str(dataset_id))
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)

        extract_to = os.path.join(UPLOADS_DIR, f"bulk_{dataset_id}")
        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)
    except Exception as e:
        logger.error(f"Cleanup Error: {e}")

@celery_app.task(
    name="ai_orchestration.services.cv_tasks.process_ingestion_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    time_limit=3600
)
def process_ingestion_task(self, dataset_id: str):
    db = SessionLocal()
    try:
        ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == dataset_id).first()
        if not ds: return

        file_path = ds.file_path or ds.video_path
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file missing on disk: {file_path}")

        ext = os.path.splitext(file_path.lower())[1]

        if ext == '.zip':
            _handle_zip_ingestion(ds, db)
        elif ext in {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}:
            pipeline = NeuralForgeImagePipeline(ds.id)
            pipeline.execute()
        else:
            pipeline = NeuralForgeVideoPipeline(ds.id)
            pipeline.execute()

    except Exception as e:
        logger.exception(f"Forge CRASH [DS#{dataset_id}]: {e}")
        db.query(SignDatasetModel).filter(SignDatasetModel.id == dataset_id).update({
            "status": "FAILED",
            "extraction_metadata": {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "stage": "TASK_ROOT"
            }
        })
        db.commit()
        _broadcast_status(dataset_id, 0, "FAILED", {"error": str(e)})
    finally:
        db.close()

def _handle_zip_ingestion(ds, db):
    extract_to = os.path.join(UPLOADS_DIR, f"bulk_{ds.id}")
    os.makedirs(extract_to, exist_ok=True)
    try:
        _broadcast_status(ds.id, 5, "PREPARING_DATASET", {"info": "Decompressing archive..."})
        with zipfile.ZipFile(ds.file_path or ds.video_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)

        all_files = []
        for root, _, files in os.walk(extract_to):
            for f in files: all_files.append(os.path.join(root, f))

        img_files = sorted([f for f in all_files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.bmp'))])
        vid_files = sorted([f for f in all_files if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))])

        if vid_files:
            pipeline = NeuralForgeVideoPipeline(ds.id, batch_files=vid_files)
            pipeline.execute()
        elif img_files:
            pipeline = NeuralForgeImagePipeline(ds.id, batch_files=img_files)
            pipeline.execute()
        else:
            raise ValueError("No supported media files found in ZIP archive.")
    finally:
        if os.path.exists(extract_to):
            try: shutil.rmtree(extract_to)
            except Exception as e: logger.debug(f"Cleanup skip: {e}")

class BaseNeuralForgePipeline:
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        self.db = SessionLocal()
        self.ds = self.db.query(SignDatasetModel).filter(SignDatasetModel.id == dataset_id).first()
        self.metadata = {
            "frames_processed": 0,
            "hands_detected": 0,
            "quality": 0,
            "checkpoint_idx": 0,
            "error": None,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        if self.ds and self.ds.extraction_metadata:
            self.metadata.update(self.ds.extraction_metadata)

        self.current_stage = self.ds.status if self.ds else "INITIALIZING"
        self.last_update_time = 0

        if self.ds:
            self.file_path = self.ds.file_path or self.ds.video_path
            self.target_dir = os.path.join(MP_DATA_ROOT, sanitize_folder_name(self.ds.label), str(dataset_id))

    def _update_state(self, stage: str, progress: int, metadata: dict = None, force: bool = False):
        now = time.time()
        # Throttling to 1.5s for stability
        prog_changed = self.ds and (progress != self.ds.progress)
        should_update_db = force or (stage != self.current_stage) or (now - self.last_update_time > 1.5) or (prog_changed and abs(progress - self.ds.progress) >= 10)

        if metadata: self.metadata.update(metadata)

        if should_update_db and self.ds:
            try:
                self.ds.status = stage
                self.ds.progress = progress
                self.ds.extraction_metadata = self.metadata
                self.db.commit()
                self.last_update_time = now
            except Exception as e:
                logger.error(f"DB Sync Error: {e}")
                self.db.rollback()

        self.current_stage = stage
        _broadcast_status(self.dataset_id, progress, stage, self.metadata)

    def finalize_success(self):
        self._update_state("SAVING_DATASET", 98)

        quality = 0
        if self.metadata["frames_processed"] > 0:
            quality = int((self.metadata["hands_detected"] / self.metadata["frames_processed"]) * 100)

        self.ds.landmark_path = self.target_dir
        self.ds.is_validated = True
        self.ds.quality_score = float(quality) / 100.0
        self.ds.status = "COMPLETED"
        self.ds.progress = 100
        self.metadata["quality"] = quality
        self.metadata["status"] = "SUCCESS"
        self.metadata["timestamp"] = datetime.datetime.utcnow().isoformat()
        self.ds.extraction_metadata = self.metadata
        self.db.commit()

        logger.info(f"Forge SUCCESS [DS#{self.dataset_id}] - Quality: {quality}%")
        self._update_state("COMPLETED", 100, force=True)

    def handle_failure(self, e):
        err_msg = str(e)
        logger.error(f"Forge FAILURE [DS#{self.dataset_id}]: {err_msg}")
        self.metadata["error"] = err_msg
        self.metadata["status"] = "FAILED"
        self.metadata["traceback"] = traceback.format_exc()
        self.metadata["timestamp"] = datetime.datetime.utcnow().isoformat()

        # Immediate sync of failure state to DB
        try:
            self.ds.status = "FAILED"
            self.ds.progress = 0
            self.ds.extraction_metadata = self.metadata
            self.db.commit()
        except:
            self.db.rollback()

        self._update_state("FAILED", 0, force=True)

    def close(self): self.db.close()

class NeuralForgeImagePipeline(BaseNeuralForgePipeline):
    def __init__(self, dataset_id: str, batch_files: list = None):
        super().__init__(dataset_id)
        self.batch_files = batch_files or [self.file_path]

    def execute(self):
        if not self.ds: return self.close()
        try:
            with cv_semaphore:
                self._update_state("PREPARING_DATASET", 10)
                cv = get_cv_module(static_mode=True)
                if not cv.active: raise RuntimeError("MediaPipe Engine failed to initialize")

                os.makedirs(self.target_dir, exist_ok=True)

                start_idx = self.metadata.get("checkpoint_idx", 0)
                total = len(self.batch_files)

                self._update_state("LOADING_VIDEO", 15)

                for idx in range(start_idx, total):
                    f_path = self.batch_files[idx]
                    if not os.path.exists(f_path): continue

                    try:
                        # PRODUCTION ROBUSTNESS: Use PIL as a bridge to avoid Numpy/OpenCV buffer mismatches
                        from PIL import Image
                        with Image.open(f_path) as pil_img:
                            # Convert to RGB and then to standard numpy array
                            img = np.array(pil_img.convert('RGB'))
                            # OpenCV expects BGR
                            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                        if img is None: continue

                        # Stage update
                        self._update_state("MEDIAPIPE_DETECTION", 15 + int((idx + 1) / total * 75))

                        lms = cv.detect_landmarks(img)
                        # Hand check: LH is 1536-1598, RH is 1599-1661
                        if not np.all(lms[1536:] == 0):
                            self.metadata["hands_detected"] += 1

                        np.save(os.path.join(self.target_dir, f"{idx}.npy"), lms)
                        self.metadata["frames_processed"] += 1
                        self.metadata["checkpoint_idx"] = idx + 1
                    except Exception as e:
                        logger.warning(f"Image Error {f_path}: {e}")
                        continue

                if self.metadata["frames_processed"] == 0:
                    raise ValueError("No landmarks detected in any images.")

                self._update_state("VALIDATING_DATASET", 95)
                self.finalize_success()
        except Exception as e:
            self.handle_failure(e)
        finally:
            self.close()

class NeuralForgeVideoPipeline(BaseNeuralForgePipeline):
    def __init__(self, dataset_id: str, batch_files: list = None):
        super().__init__(dataset_id)
        self.video_files = batch_files or [self.file_path]

    def execute(self):
        if not self.ds: return self.close()
        try:
            with cv_semaphore:
                self._update_state("PREPARING_DATASET", 10)
                cv = get_cv_module(static_mode=False)
                if not cv.active: raise RuntimeError("MediaPipe Engine failed to initialize")

                all_lms = []
                TARGET_FRAMES = 30

                start_v_idx = self.metadata.get("checkpoint_idx", 0)

                for v_idx in range(start_v_idx, len(self.video_files)):
                    v_path = self.video_files[v_idx]
                    if not os.path.exists(v_path): continue

                    self._update_state("LOADING_VIDEO", 20)
                    cap = cv2.VideoCapture(v_path)
                    if not cap.isOpened(): continue

                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    if total_frames < 5:
                        cap.release()
                        continue

                    # Stage: Extracting Frames (25% - 45%)
                    self._update_state("EXTRACTING_FRAMES", 25)

                    SAMPLE_SIZE = min(120, total_frames)
                    indices = np.linspace(0, total_frames - 1, SAMPLE_SIZE).astype(int)

                    frames_to_process = []
                    for i, idx in enumerate(indices):
                        # FIX: Cast idx to int to avoid 'can not be treated as a double' error
                        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                        ret, frame = cap.read()
                        if not ret: continue

                        # QUALITY GATE: Blurry check
                        try:
                            if cv.is_blurry(frame, threshold=60.0): continue
                        except: pass

                        frames_to_process.append(frame)

                        if i % 10 == 0:
                            prog = 25 + int((i + 1) / SAMPLE_SIZE * 20)
                            self._update_state("EXTRACTING_FRAMES", prog)

                    cap.release()

                    # Stage: MediaPipe Detection (45% - 80%)
                    self._update_state("MEDIAPIPE_DETECTION", 45)

                    candidates = []
                    total_f = len(frames_to_process)
                    for i, frame in enumerate(frames_to_process):
                        try:
                            lms = cv.detect_landmarks(frame)
                            # Hand check
                            hand_score = 0
                            if not np.all(lms[1536:1599] == 0): hand_score += 1
                            if not np.all(lms[1599:] == 0): hand_score += 1

                            candidates.append((lms, hand_score))
                        except Exception as e:
                            logger.warning(f"Frame Detection Skip: {e}")

                        if i % 5 == 0:
                            prog = 45 + int((i + 1) / total_f * 35)
                            self._update_state("MEDIAPIPE_DETECTION", prog)

                    # Select best 30 based on hand detection and temporal spread
                    if len(candidates) < 5:
                        logger.warning(f"Insufficient landmarks in {v_path}")
                        continue

                    final_indices = np.linspace(0, len(candidates)-1, TARGET_FRAMES).astype(int)
                    for idx in final_indices:
                        lms, score = candidates[int(idx)]
                        all_lms.append(lms)
                        if score > 0: self.metadata["hands_detected"] += 1
                        self.metadata["frames_processed"] += 1

                    self.metadata["checkpoint_idx"] = v_idx + 1

                if len(all_lms) < 5:
                    raise ValueError("Insufficient landmarks detected. Ensure hands are clearly visible.")

                # Stage: Feature Extraction (85%)
                self._update_state("FEATURE_EXTRACTION", 85)

                if len(all_lms) != TARGET_FRAMES:
                    resample = np.linspace(0, len(all_lms)-1, TARGET_FRAMES).astype(int)
                    all_lms = [all_lms[int(i)] for i in resample]

                os.makedirs(self.target_dir, exist_ok=True)
                for i, lms in enumerate(all_lms):
                    np.save(os.path.join(self.target_dir, f"{i}.npy"), lms)

                self._update_state("VALIDATING_DATASET", 95)
                self.finalize_success()

        except Exception as e:
            self.handle_failure(e)
        finally:
            self.close()
