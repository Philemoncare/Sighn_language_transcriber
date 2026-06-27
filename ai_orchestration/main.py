import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Project setup
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Internal Imports
from ai_orchestration.core.config import PROJECT_NAME, VERSION, PROJECT_ROOT
from ai_orchestration.core.logging import setup_logging, log_writer_task
from ai_orchestration.core.auth_init import ensure_admin_exists
from ai_orchestration.api import auth, admin, translation
from ai_orchestration.websocket.handler import websocket_endpoint
from database_layer.db_manager import init_db, SessionLocal

# --- LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Start Logging
    asyncio.create_task(log_writer_task())
    logger.info(f"--- {PROJECT_NAME} Lifecycle Startup ---")

    # 2. Initialize Database & Global Services
    try:
        logger.info("Initializing Database...")
        await asyncio.to_thread(init_db)

        logger.info("Ensuring Admin exists...")
        await asyncio.to_thread(ensure_admin_exists)

        # 3. Initialize Orchestrator properly within lifespan
        logger.info("Synchronizing AI Orchestrator...")
        from ai_orchestration.services.orchestrator import orchestrator

        # Store loop for thread-safe broadcasting
        import ai_orchestration.core.config as config
        config.GLOBAL_LOOP = asyncio.get_running_loop()

        db = SessionLocal()
        try:
            from database_layer.db_manager import SignDatasetModel
            # CLEANUP: Mark any stuck processing jobs as failed on restart
            stuck_count = db.query(SignDatasetModel).filter(
                SignDatasetModel.status.in_(["queued", "uploading", "validating", "decoding", "extracting_features", "generating_context", "finalizing"])
            ).update({SignDatasetModel.status: "failed", SignDatasetModel.progress: 0}, synchronize_session=False)
            if stuck_count > 0:
                logger.warning(f"Cleaned up {stuck_count} stuck extraction jobs from previous session.")

            db.commit()
            orchestrator.sync_vocabulary(db)
        finally:
            db.close()

        logger.info("Core architecture fully integrated and synchronized.")
    except Exception as e:
        logger.error(f"CRITICAL Lifecycle Failure: {e}")
        import traceback
        logger.error(traceback.format_exc())

    yield
    logger.info(f"--- {PROJECT_NAME} Lifecycle Shutdown ---")

# --- APPLICATION SETUP ---
app = FastAPI(
    title=PROJECT_NAME,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)
logger = setup_logging()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, tags=["Authentication"])
app.include_router(admin.router, tags=["Administration"])
app.include_router(translation.router, tags=["Translation"])

# WebSockets
@app.websocket("/ws/translate/{user_id}")
async def ws_route(websocket: WebSocket, user_id: int):
    await websocket_endpoint(websocket, user_id)

# Static Files
# Priority: UI Layer
ui_path = os.path.join(PROJECT_ROOT, "ui_layer")
if os.path.exists(ui_path):
    app.mount("/ui_layer", StaticFiles(directory=ui_path, html=True), name="ui")

# Public assets
public_path = os.path.join(PROJECT_ROOT, "public")
if os.path.exists(public_path):
    app.mount("/public", StaticFiles(directory=public_path), name="public")

@app.get("/")
async def root():
    return RedirectResponse(url="/ui_layer/web_app/index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": VERSION}

if __name__ == "__main__":
    import uvicorn
    # Production-grade: reload=False prevents background task termination on file changes
    uvicorn.run("ai_orchestration.main:app", host="0.0.0.0", port=8000, reload=False)
