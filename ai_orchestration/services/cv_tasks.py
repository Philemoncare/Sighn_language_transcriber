import os
import cv2
import numpy as np
import logging
from sqlalchemy.orm import Session
from ai_orchestration.core.config import PROJECT_ROOT, MP_DATA_ROOT
from database_layer.db_manager import SessionLocal, SignDatasetModel
from module2_sign_to_speech.cv_module.landmark_detection import CVModule

logger = logging.getLogger("SnLag_CVTasks")

def process_video_task(dataset_id: int):
    """
    Extracts landmarks from a dataset video and saves them as .npy files.
    """
    db = SessionLocal()
    try:
        ds = db.query(SignDatasetModel).filter(SignDatasetModel.id == dataset_id).first()
        if not ds or not ds.video_path or not os.path.exists(ds.video_path):
            logger.error(f"CV Task: Dataset #{dataset_id} invalid or video missing.")
            return

        target_dir = os.path.join(MP_DATA_ROOT, ds.label.strip(), str(ds.id))
        os.makedirs(target_dir, exist_ok=True)

        cap = cv2.VideoCapture(ds.video_path)
        if not cap.isOpened():
            logger.error(f"CV Task: Failed to open video {ds.video_path}")
            return

        cv_engine = CVModule()
        if not cv_engine.active:
            logger.error("CV Task: MediaPipe failed to initialize.")
            return

        count = 0
        while count < 30: # Limit to 30 frames for LSTM sequence consistency
            ret, frame = cap.read()
            if not ret: break

            landmarks = cv_engine.detect_landmarks(frame)
            np.save(os.path.join(target_dir, f"{count}.npy"), landmarks)
            count += 1

        cap.release()
        if hasattr(cv_engine, 'holistic') and cv_engine.holistic:
            cv_engine.holistic.close()

        if count > 0:
            ds.landmark_path = target_dir
            db.commit()
            logger.info(f"CV Task: Successfully processed {count} frames for dataset #{dataset_id}")
        else:
            logger.warning(f"CV Task: No frames processed for dataset #{dataset_id}")

    except Exception as e:
        logger.error(f"CV Task Failure: {e}")
    finally:
        db.close()
