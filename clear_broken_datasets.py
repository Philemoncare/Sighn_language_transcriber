import os
import shutil
from database_layer.db_manager import SessionLocal, SignDatasetModel, TrainingJobModel
from ai_orchestration.services.cv_tasks import cleanup_dataset_files

def clear_broken():
    db = SessionLocal()
    try:
        # Find datasets that are broken or 0 quality
        broken = db.query(SignDatasetModel).filter(
            (SignDatasetModel.quality_score == 0) |
            (SignDatasetModel.status == "failed") |
            (SignDatasetModel.is_deleted == True)
        ).all()

        print(f"Found {len(broken)} broken or deleted datasets to purge.")

        for ds in broken:
            print(f"Purging DS#{ds.id} ({ds.label})...")

            # 1. Physical Cleanup
            try:
                cleanup_dataset_files(ds.id, ds.label, ds.landmark_path)
                if ds.video_path and os.path.exists(ds.video_path):
                    os.remove(ds.video_path)
                    print(f"  - Removed asset: {ds.video_path}")
            except Exception as e:
                print(f"  - Physical cleanup error: {e}")

            # 2. Hard DB Delete (to stop 'counting' them)
            db.delete(ds)

        # Also clear any failed training jobs to start clean
        failed_jobs = db.query(TrainingJobModel).filter(TrainingJobModel.status == "failed").all()
        for job in failed_jobs:
            print(f"Removing failed training job: {job.job_name}")
            db.delete(job)

        db.commit()
        print("\nCleanup Complete. System is now clean for fresh training.")

    except Exception as e:
        print(f"CRITICAL ERROR during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_broken()
