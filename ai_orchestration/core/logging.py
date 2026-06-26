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
            # Non-blocking handoff to async queue with extended metadata
            loop = asyncio.get_event_loop()
            if loop.is_running():
                log_data = {
                    "level": record.levelname,
                    "service": getattr(record, "service", "kernel"),
                    "category": getattr(record, "category", None),
                    "message": record.getMessage(),
                    "details": {
                        "full_message": self.format(record),
                        "pathname": record.pathname,
                        "lineno": record.lineno,
                        "funcName": record.funcName,
                        "exc_info": record.exc_text if record.exc_info else None
                    },
                    "request_id": getattr(record, "request_id", None),
                    "user_id": getattr(record, "user_id", None),
                    "dataset_id": getattr(record, "dataset_id", None),
                    "duration": getattr(record, "duration", None),
                    "timestamp": datetime.datetime.utcnow()
                }
                loop.call_soon_threadsafe(log_queue.put_nowait, log_data)

                # Real-time broadcast via WebSocket
                try:
                    from ai_orchestration.websocket.handler import manager
                    import ai_orchestration.core.config as config

                    ws_loop = getattr(config, 'GLOBAL_LOOP', None)
                    if ws_loop:
                        # Convert datetime to string for JSON serialization
                        broadcast_data = log_data.copy()
                        broadcast_data["timestamp"] = broadcast_data["timestamp"].isoformat()
                        broadcast_data["type"] = "system_log"
                        asyncio.run_coroutine_threadsafe(manager.broadcast_json(broadcast_data), ws_loop)
                except: pass
        except: pass

def setup_logging():
    # Force immediate flushing for file logs to help debug crashes
    file_handler = logging.FileHandler("backend.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(), file_handler]
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
