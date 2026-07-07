import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket, Query
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
from ai_orchestration.api import auth, admin_auth, admin, translation, onboarding, user, meeting
from ai_orchestration.api.user import router as user_profile_router
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
        # PERFORMANCE: Move heavy model loading to a thread to prevent event loop freeze
        logger.info("Synchronizing AI Orchestrator (Background)...")

        async def init_orchestrator_task():
            try:
                # Use to_thread to prevent blocking the event loop during heavy model loading
                def heavy_init():
                    from ai_orchestration.services.orchestrator import orchestrator
                    db = SessionLocal()
                    try:
                        orchestrator.sync_vocabulary(db)
                    finally:
                        db.close()
                    return orchestrator

                await asyncio.to_thread(heavy_init)
                logger.info("AI Orchestrator synchronization complete.")
            except Exception as e:
                logger.error(f"Async Orchestrator Init Failure: {e}")

        # Store loop for thread-safe broadcasting
        import ai_orchestration.core.config as config
        config.GLOBAL_LOOP = asyncio.get_running_loop()

        # Start Orchestrator init in background
        asyncio.create_task(init_orchestrator_task())

        # Initialize WebSocket Redis synchronization
        from ai_orchestration.websocket.handler import manager as ws_manager
        try:
            # Add timeout to prevent Redis hang from blocking startup
            await asyncio.wait_for(ws_manager.init_redis(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("WS: Redis Sync initialization timed out. Proceeding in standalone mode.")
        except Exception as e:
            logger.error(f"WS: Redis Sync initialization failed: {e}")

        db = SessionLocal()
        try:
            from database_layer.db_manager import SignDatasetModel, TrainingJobModel
            # CLEANUP: Mark any stuck processing jobs as failed on restart
            stuck_count = db.query(SignDatasetModel).filter(
                SignDatasetModel.status.in_(["QUEUED", "UPLOADED", "VALIDATING", "PREPROCESSING", "EXTRACTING", "GENERATING_EMBEDDINGS", "FINALIZING", "DECODING_VIDEO", "EXTRACTING_FRAMES", "TRACKING_HANDS"])
            ).update({SignDatasetModel.status: "FAILED", SignDatasetModel.progress: 0}, synchronize_session=False)

            stuck_training = db.query(TrainingJobModel).filter(
                TrainingJobModel.status.in_(["pending", "training", "evaluating"])
            ).update({TrainingJobModel.status: "failed"}, synchronize_session=False)

            if stuck_count > 0 or stuck_training > 0:
                logger.warning(f"Cleaned up {stuck_count} stuck extraction jobs and {stuck_training} stuck training jobs from previous session.")

            db.commit()
        finally:
            db.close()

        logger.info("Core architecture lifecycle initiated.")
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

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request Error: {e}")
        raise

# --- PUBLIC ROUTING (PRIORITY) ---
@app.get("/")
async def root():
    return RedirectResponse(url="/ui_layer/web_app/index.html")

@app.get("/login")
async def user_login_page():
    return RedirectResponse(url="/ui_layer/web_app/auth.html?view=login")

@app.get("/register")
async def user_register_page():
    return RedirectResponse(url="/ui_layer/web_app/auth.html?view=register")

@app.get("/signup")
async def user_signup_page():
    return RedirectResponse(url="/ui_layer/web_app/auth.html?view=register")

@app.get("/welcome")
async def welcome_page():
    return RedirectResponse(url="/ui_layer/web_app/welcome.html")

@app.get("/dashboard")
async def user_dashboard_page():
    return RedirectResponse(url="/ui_layer/web_app/workspace.html")

# --- API ROUTES ---
app.include_router(auth.router, prefix="/api/user/auth")
app.include_router(admin_auth.router, prefix="/api/admin/auth")
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administration"])
app.include_router(translation.router, prefix="/api/translation", tags=["Translation"])
app.include_router(meeting.router, prefix="/api/meeting", tags=["Meetings"])
app.include_router(user_profile_router, prefix="/api/user", tags=["User Profile"])

# WebSockets
@app.websocket("/ws/translate")
async def ws_route(websocket: WebSocket, token: str = Query(...)):
    await websocket_endpoint(websocket, token)

# --- STATIC FILES ---
# Priority: UI Layer
ui_path = os.path.join(PROJECT_ROOT, "ui_layer")
if os.path.exists(ui_path):
    app.mount("/ui_layer", StaticFiles(directory=ui_path, html=True), name="ui")

# Public assets
public_path = os.path.join(PROJECT_ROOT, "public")
if os.path.exists(public_path):
    app.mount("/public", StaticFiles(directory=public_path), name="public")

# --- ADMIN ROUTES ---
@app.get("/admin/login")
async def admin_login_page():
    return RedirectResponse(url="/ui_layer/admin_dashboard/login.html")

@app.get("/admin/dashboard")
async def admin_dashboard_page():
    return RedirectResponse(url="/ui_layer/admin_dashboard/dashboard.html")

@app.get("/admin/forgot-password")
async def admin_forgot_password_page():
    return RedirectResponse(url="/ui_layer/admin_dashboard/forgot-password.html")

@app.get("/admin/reset-password")
async def admin_reset_password_page():
    return RedirectResponse(url="/ui_layer/admin_dashboard/reset-password.html")

@app.get("/health")
async def health_check():
    from database_layer.db_manager import check_db_health
    db_ok = await asyncio.to_thread(check_db_health)
    return {
        "status": "ok" if db_ok else "degraded",
        "version": VERSION,
        "database": "connected" if db_ok else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    # Production-grade: reload=False prevents background task termination on file changes
    uvicorn.run("ai_orchestration.main:app", host="0.0.0.0", port=8000, reload=False)
