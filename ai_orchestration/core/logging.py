import logging
import asyncio
import datetime

# High-speed log buffer to prevent DB bottleneck
log_queue = asyncio.Queue()

class DatabaseLogHandler(logging.Handler):
    def emit(self, record):
        # FAST EXIT: Don't let logging block the main thread
        try:
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

            # Put in queue for DB writer task (async)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(log_queue.put_nowait, log_data)
            except: pass

            # Real-time broadcast via WebSocket/Redis
            import ai_orchestration.core.config as config

            # Check for global loop first (preferred)
            loop = getattr(config, 'GLOBAL_LOOP', None)
            if loop and loop.is_running():
                try:
                    from ai_orchestration.websocket.handler import manager
                    broadcast_data = log_data.copy()
                    broadcast_data["timestamp"] = broadcast_data["timestamp"].isoformat()
                    broadcast_data["type"] = "system_log"
                    asyncio.run_coroutine_threadsafe(manager.broadcast_json(broadcast_data, scope="admin"), loop)
                except: pass
            else:
                # If no loop (startup/sync worker), don't block on Redis publish
                # Celery workers should not be broadcasting logs via Redis during high load
                pass
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
    # logger.addHandler(DatabaseLogHandler()) # Temporarily disabled to prevent event loop interference
    return logger

async def log_writer_task():
    """Background task to flush logs to DB in batches with high performance"""
    # DEFERRED IMPORT to break potential circularity or timing issues during startup
    from database_layer.db_manager import SessionLocal, SystemLogModel

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
