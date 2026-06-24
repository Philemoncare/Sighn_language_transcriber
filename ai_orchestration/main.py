import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# COMPATIBILITY HACK: Bypass broken MediaPipe/TensorFlow/NumPy dependency chain
from types import ModuleType
import numpy as np

# Fix NumPy/JAX/TensorFlow friction
if not hasattr(np, "dtypes"):
    np.dtypes = ModuleType("dtypes")
if not hasattr(np.dtypes, "StringDType"):
    # Some JAX versions expect StringDType in newer NumPy, but we can shim it
    class MockStringDType:
        def __call__(self, *args, **kwargs): return np.str_
    np.dtypes.StringDType = MockStringDType()

try:
    import tensorflow.tools.docs.doc_controls as dc
except (ImportError, ModuleNotFoundError, AttributeError):
    try:
        class DecoratorStub:
            def __call__(self, *args, **kwargs):
                if args and callable(args[0]): return args[0]
                return lambda x: x
            def __getattr__(self, name): return self
        stub = DecoratorStub()
        for pkg in ["tensorflow", "tensorflow.tools", "tensorflow.tools.docs", "tensorflow.tools.docs.doc_controls"]:
            if pkg not in sys.modules:
                mod = ModuleType(pkg)
                if pkg != "tensorflow.tools.docs.doc_controls": mod.__path__ = []
                sys.modules[pkg] = mod
        m = sys.modules["tensorflow.tools.docs.doc_controls"]
        m.header = m.do_not_generate_docs = m.do_not_doc_in_subclasses = stub
        if "tensorflow.tools.docs" in sys.modules: sys.modules["tensorflow.tools.docs"].doc_controls = m
    except: pass

# Project setup
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Internal Imports
from ai_orchestration.core.config import PROJECT_NAME, VERSION, PROJECT_ROOT
from ai_orchestration.core.logging import setup_logging, log_writer_task
from ai_orchestration.core.auth_init import ensure_admin_exists
from ai_orchestration.api import auth, admin, translation
from ai_orchestration.websocket.handler import websocket_endpoint
from ai_orchestration.services.orchestrator import orchestrator
from database_layer.db_manager import init_db, SessionLocal

# --- LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Start Logging
    asyncio.create_task(log_writer_task())
    logger.info(f"{PROJECT_NAME} starting...")

    # 2. Initialize Database
    try:
        await asyncio.to_thread(init_db)
        await asyncio.to_thread(ensure_admin_exists)

        # 3. Synchronize AI Orchestrator
        db = SessionLocal()
        try:
            orchestrator.sync_vocabulary(db)
        finally:
            db.close()

        logger.info("Core architecture initialized and synchronized.")
    except Exception as e:
        logger.error(f"Initialization failure: {e}")

    yield
    logger.info(f"{PROJECT_NAME} shutting down.")

# --- APPLICATION SETUP ---
app = FastAPI(title=PROJECT_NAME, version=VERSION, lifespan=lifespan)
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
app.mount("/ui", StaticFiles(directory=os.path.join(PROJECT_ROOT, "ui_layer"), html=True), name="ui")
app.mount("/public", StaticFiles(directory=os.path.join(PROJECT_ROOT, "public")), name="public")

@app.get("/")
async def root():
    return RedirectResponse(url="/ui/web_app/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ai_orchestration.main:app", host="0.0.0.0", port=8000, reload=True)
