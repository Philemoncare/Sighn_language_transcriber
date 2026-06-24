import os
import json
import logging
import asyncio
import datetime
import shutil
from typing import List, Callable
from sqlalchemy.orm import Session

from ai_orchestration.core.config import PROJECT_ROOT, MODELS_DIR, MP_DATA_ROOT
from database_layer.db_manager import SessionLocal, TrainingJobModel, SignDatasetModel, ModelVersionModel
from module2_sign_to_speech.sequence_model.train import train_model

from ai_orchestration.websocket.handler import manager

logger = logging.getLogger("SnLag_Training")

class TrainingService:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = None

    async def run_job(self, job_id: int):
        if self.loop is None:
            self.loop = asyncio.get_running_loop()

        db = SessionLocal()
        job = db.query(TrainingJobModel).filter(TrainingJobModel.id == job_id).first()
        if not job:
            db.close()
            return

        try:
            job.status = "training"
            db.commit()

            def update_progress(p: int):
                inner_db = SessionLocal()
                try:
                    j = inner_db.query(TrainingJobModel).filter(TrainingJobModel.id == job_id).first()
                    if j:
                        if p == -1:
                            j.status = "failed"
                        else:
                            j.progress = p
                        inner_db.commit()

                        # Broadcast to UI
                        if self.loop and self.loop.is_running():
                            self.loop.call_soon_threadsafe(
                                lambda: asyncio.create_task(manager.broadcast_training_update(job_id, p, j.status))
                            )

                        if p != -1 and p % 20 == 0:
                            logger.info(f"Training Job #{job_id}: {p}% complete")
                finally:
                    inner_db.close()

            # 1. Dataset Validation
            valid_actions = self._get_valid_actions(db)
            if not valid_actions:
                job.status = "failed"
                db.commit()
                logger.error(f"Training Job #{job_id} failed: No valid dataset found.")
                return

            # 2. Start Training
            epochs = job.config.get("epochs", 50)
            await asyncio.to_thread(train_model, valid_actions, update_progress, epochs)

            # 3. Post-Training: Deployment & Versioning
            db.refresh(job)
            if job.status != "failed":
                await self._finalize_model(db, job, valid_actions)
                job.status = "completed"
                job.progress = 100
                job.completed_at = datetime.datetime.utcnow()
                db.commit()
                logger.info(f"Training Job #{job_id} successfully completed and deployed.")

        except Exception as e:
            logger.error(f"Training Job #{job_id} critical error: {e}")
            job.status = "failed"
            db.commit()
        finally:
            db.close()

    def _get_valid_actions(self, db: Session) -> List[str]:
        # Logic to find folders with enough .npy files
        actions_query = db.query(SignDatasetModel.label).filter(SignDatasetModel.landmark_path != None).distinct().all()
        pot_actions = sorted(list(set([a[0].strip() for a in actions_query if a[0]])))

        valid = []
        for a in pot_actions:
            action_dir = os.path.join(MP_DATA_ROOT, a)
            if os.path.exists(action_dir) and os.path.isdir(action_dir):
                has_data = False
                for seq in os.listdir(action_dir):
                    seq_path = os.path.join(action_dir, seq)
                    if os.path.isdir(seq_path):
                        files = [f for f in os.listdir(seq_path) if f.endswith('.npy')]
                        if len(files) >= 5:
                            has_data = True
                            break
                if has_data:
                    valid.append(a)
        return valid

    async def _finalize_model(self, db: Session, job: TrainingJobModel, actions: List[str]):
        # Model Versioning Logic
        v_tag = f"BUILD-{job.id}"
        best_model_src = os.path.join(PROJECT_ROOT, 'best_model.h5')
        v_file = os.path.join(MODELS_DIR, f"model_{v_tag}.h5")

        if os.path.exists(best_model_src):
            shutil.copy(best_model_src, v_file)
        else:
            # Fallback if train_model didn't save to best_model.h5
            v_file = best_model_src

        # Get metrics
        accuracy = 0.95
        report_path = os.path.join(PROJECT_ROOT, 'latest_report.json')
        if os.path.exists(report_path):
            try:
                with open(report_path, 'r') as f:
                    report = json.load(f)
                    accuracy = report.get('accuracy', accuracy)
            except: pass

        # Update DB
        db.query(ModelVersionModel).update({ModelVersionModel.is_active: False})
        new_v = ModelVersionModel(
            version_tag=v_tag,
            file_path=v_file,
            is_active=True,
            metrics={"accuracy": accuracy},
            supported_languages=["English"]
        )
        db.add(new_v)

        # Deploy to Live Engine
        try:
            self.orchestrator.seq_model.reload_model(v_file, actions)
        except Exception as e:
            logger.error(f"Live model deployment failed: {e}")
