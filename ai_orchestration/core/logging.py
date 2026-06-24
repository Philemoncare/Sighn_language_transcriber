import logging
import asyncio
import datetime
from sqlalchemy.orm import Session
from database_layer.db_manager import SessionLocal, SystemLogModel

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

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(), logging.FileHandler("backend.log")]
    )
    logger = logging.getLogger("SnLag_Core")
    logger.addHandler(DatabaseLogHandler())
    return logger

async def log_writer_task():
    """Background task to flush logs to DB in batches with high performance"""
    while True:
        try:
            logs_to_write = []
            first_log = await log_queue.get()
            logs_to_write.append(first_log)

            while not log_queue.empty() and len(logs_to_write) < 100:
                logs_to_write.append(log_queue.get_nowait())

            def sync_db_write(logs):
                db = SessionLocal()
                try:
                    db.add_all([SystemLogModel(**l) for l in logs])
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()

            await asyncio.to_thread(sync_db_write, logs_to_write)
            for _ in range(len(logs_to_write)):
                log_queue.task_done()

            await asyncio.sleep(0.1 if log_queue.empty() else 0.01)
        except Exception:
            await asyncio.sleep(1)
