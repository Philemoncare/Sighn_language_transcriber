import os
import logging
import sys
import redis
from celery import Celery, signals
from kombu import Queue, Exchange

# Requirement 4: Centralized Redis Connection Manager
from ai_orchestration.core.redis_manager import redis_manager
from ai_orchestration.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Requirement 2 & 4: Safe Redis Compatibility Refactor
# Instead of unsafe monkey-patching of Connection methods, we use a
# specialized ConnectionPool that respects our audited protocol selection.
_OriginalConnectionPool = redis.ConnectionPool

class SignlySafeConnectionPool(_OriginalConnectionPool):
    def __init__(self, *args, **kwargs):
        # Requirement 1 & 6: Guarantee protocol compatibility
        # If protocol is not specified, force it to our audited version.
        # This prevents the library from defaulting to RESP3 (protocol=3).
        if 'protocol' not in kwargs:
            kwargs['protocol'] = redis_manager.negotiated_protocol

        # Requirement 2: Ensure RESP3-only features are disabled for Redis 5.
        # Setting protocol=2 above automatically suppresses default maintenance
        # notifications in modern redis-py versions.
        # We explicitly ensure maint_notifications_config is None to avoid TypeErrors.
        if redis_manager.negotiated_protocol == 2:
            kwargs['maint_notifications_config'] = None

        super().__init__(*args, **kwargs)

# Requirement 4: Globally apply the compatibility manager
redis.ConnectionPool = SignlySafeConnectionPool

# Requirement 9: Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] [%(process)d] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("SnLag_Orchestrator")

def show_startup_diagnostics():
    """Requirement 5: Startup Diagnostics"""
    import kombu
    import celery

    diag = redis_manager.get_diagnostics()

    print("\n" + "="*60)
    print("      SIGNLY NEURAL FORGE STARTUP DIAGNOSTICS")
    print("="*60)
    print(f"✓ Redis Server:    {diag['redis_server']}")
    print(f"✓ Redis Client:    {diag['redis_client']}")
    print(f"✓ Negotiated RESP: {diag['negotiated_resp']}")
    print(f"✓ Celery Version:  {celery.__version__}")
    print(f"✓ Kombu Version:   {kombu.__version__}")
    print(f"✓ Broker Status:   {'CONNECTED' if redis_manager.check_health() else 'FAILED'}")
    print("="*60 + "\n")

def validate_environment():
    """Requirement 3 & 11: Startup Validation"""
    if not redis_manager.check_health():
        logger.critical("VALIDATION FAILED: Redis is unreachable.")
        return False

    # Requirement 3: Version Compatibility Check
    diag = redis_manager.get_diagnostics()
    if "Unknown" in diag['redis_server']:
        logger.warning("WARNING: Could not verify Redis version. Proceeding with RESP2.")

    return True

# Initialize Celery App
celery_app = Celery(
    "SnLag_Orchestrator",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Requirement 8 & 12: Queue Isolation & Performance
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,

    # Requirement 6: Transport Safety
    broker_transport_options={
        'global_keyprefix': 'snlag:',
        'socket_timeout': 30,
        'socket_connect_timeout': 30,
        'visibility_timeout': 3600,
    },

    # Isolation:Dedicated queues for workload separation
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
        Queue('ai_processing', Exchange('ai_processing'), routing_key='ai_processing'),
        Queue('training', Exchange('training'), routing_key='training'),
        Queue('maintenance', Exchange('maintenance'), routing_key='maintenance'),
    ),
    task_routes={
        'ai_orchestration.services.mail_service.*': {'queue': 'high_priority'},
        'ai_orchestration.services.cv_tasks.process_ingestion_task': {'queue': 'default'},
        'ai_orchestration.services.training_pipeline.*': {'queue': 'training'},
        'ai_orchestration.services.cv_tasks.sync_unprocessed_datasets_task': {'queue': 'maintenance'},
    }
)

celery_app.autodiscover_tasks(['ai_orchestration.services'])

@signals.worker_process_init.connect
def setup_worker_context(*args, **kwargs):
    logger.info("Worker Node initialized. Using Protocol: %s", redis_manager.negotiated_protocol)
    import ai_orchestration.services.cv_tasks
    import ai_orchestration.services.training_pipeline
    import ai_orchestration.services.mail_service

@celery_app.task(name="ai_orchestration.core.celery_app.heartbeat")
def heartbeat():
    import datetime
    return {
        "status": "online",
        "timestamp": str(datetime.datetime.now()),
        "diagnostics": redis_manager.get_diagnostics()
    }

# Automated Maintenance Schedule
celery_app.conf.beat_schedule = {
    'maintenance-sync-unprocessed-5m': {
        'task': 'ai_orchestration.services.cv_tasks.sync_unprocessed_datasets_task',
        'schedule': 300.0,
        'options': {'queue': 'maintenance'}
    },
    'system-heartbeat-1m': {
        'task': 'ai_orchestration.core.celery_app.heartbeat',
        'schedule': 60.0,
        'options': {'queue': 'maintenance'}
    }
}

if __name__ == '__main__':
    show_startup_diagnostics()
    if validate_environment():
        celery_app.start()
    else:
        sys.exit(1)
