import json
import base64
import asyncio
import time
import collections
import logging
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from database_layer.db_manager import SessionLocal, CollectedDataModel
from ai_orchestration.services.orchestrator import orchestrator

logger = logging.getLogger("SnLag_WS")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def broadcast_training_update(self, job_id: int, progress: int, status: str):
        message = json.dumps({
            "type": "training_progress",
            "job_id": job_id,
            "progress": progress,
            "status": status
        })
        for ws in self.active_connections.values():
            try:
                await ws.send_text(message)
            except:
                pass

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)

    # State and Buffers
    buffer = collections.deque(maxlen=30)
    inference_lock = asyncio.Lock()
    last_inference_time = 0
    state = {"language": "English"}
    MIN_INFERENCE_INTERVAL = 0.15 # 150ms

    try:
        while True:
            data = await websocket.receive()

            if "bytes" in data:
                # High-speed landmark processing
                landmarks = np.frombuffer(data["bytes"], dtype=np.float32).tolist()
                buffer.append(landmarks)

                now = time.time()
                if len(buffer) == 30 and not inference_lock.locked() and (now - last_inference_time) > MIN_INFERENCE_INTERVAL:
                    last_inference_time = now
                    asyncio.create_task(run_ws_inference(websocket, list(buffer), state, user_id, inference_lock))

            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "set_language":
                    state["language"] = msg.get("language", "English")
                elif msg.get("type") == "speech_text":
                    # Real-time Speech-to-Sign path
                    text = msg.get("text", "")
                    if text:
                        res = await orchestrator.speech_to_sign(text.encode(), language=state["language"])
                        await websocket.send_json({
                            "type": "translation_result",
                            "original_text": text,
                            "result": res.get("result")
                        })

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"WS: User {user_id} disconnected.")
    except Exception as e:
        logger.error(f"WS Error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id)

async def run_ws_inference(ws: WebSocket, buffer: list, state: dict, user_id: int, lock: asyncio.Lock):
    async with lock:
        try:
            res = await orchestrator.sign_to_speech(buffer, language=state["language"])
            if res["status"] == "success":
                sign = res["text"]
                conf = res["confidence"]

                # Active Learning: Harvest high-conf data
                if conf > 0.92:
                    harvest_data(user_id, buffer, sign, conf)

                await ws.send_json({
                    "type": "prediction",
                    "sign": sign,
                    "confidence": conf,
                    "audio_base64": base64.b64encode(res["audio"]).decode() if "audio" in res else None
                })
        except Exception as e:
            logger.error(f"WS Inference failure: {e}")

def harvest_data(user_id: int, landmarks: list, label: str, conf: float):
    db = SessionLocal()
    try:
        db.add(CollectedDataModel(
            user_id=user_id,
            data_type="sign",
            payload={"landmarks": landmarks},
            label=label,
            confidence=conf
        ))
        db.commit()
    except: pass
    finally: db.close()
