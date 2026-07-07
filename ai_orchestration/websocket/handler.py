import json
import base64
import asyncio
import time
import collections
import logging
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from jose import jwt, JWTError
from ai_orchestration.core.config import SECRET_KEY, ALGORITHM, CELERY_BROKER_URL
from database_layer.db_manager import SessionLocal, CollectedDataModel, UserModel, AdminModel

logger = logging.getLogger("SnLag_WS")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.admin_connections: dict[str, WebSocket] = {}
        self.room_members: dict[str, set[str]] = {} # room_id -> set(user_id)
        self.user_rooms: dict[str, str] = {} # user_id -> room_id
        self.participant_states: dict[str, dict] = {} # user_id -> {state}
        self.redis_client = None

    async def init_redis(self):
        """Enable cross-process/cross-node broadcast sync via Redis"""
        try:
            import redis.asyncio as redis
            self.redis_client = redis.from_url(CELERY_BROKER_URL, protocol=2)
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("snlag_broadcast")
            await self.pubsub.subscribe("snlag_signaling")
            asyncio.create_task(self._redis_listener())
            logger.info("WS: Redis Synchronization Active (RESP2)")
        except Exception as e:
            logger.warning(f"WS: Redis Sync Unavailable (Standalone Mode): {e}")

    async def _redis_listener(self):
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                    payload = json.loads(message["data"])

                    if channel == "snlag_broadcast":
                        scope = payload.pop("_ws_scope", "user")
                        await self._local_broadcast(payload, scope)
                    elif channel == "snlag_signaling":
                        target_id = str(payload.get("target_id"))
                        if target_id in self.active_connections:
                            await self.active_connections[target_id].send_text(json.dumps(payload))
                except Exception as e:
                    logger.debug(f"WS: Sync Decode Error: {e}")

    async def connect(self, websocket: WebSocket, user_id: str, scope: str = "user"):
        await websocket.accept()
        user_id = str(user_id)
        if scope == "admin":
            self.admin_connections[user_id] = websocket
        else:
            self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        user_id = str(user_id)
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.admin_connections:
            del self.admin_connections[user_id]

        # Remove from room
        if user_id in self.user_rooms:
            room_id = self.user_rooms.pop(user_id)
            if room_id in self.room_members:
                self.room_members[room_id].discard(user_id)
                if not self.room_members[room_id]:
                    del self.room_members[room_id]
                else:
                    # Notify others that this user left
                    asyncio.create_task(self.broadcast_to_room(room_id, {
                        "type": "participant_left",
                        "user_id": user_id
                    }))

        if user_id in self.participant_states:
            del self.participant_states[user_id]

    async def join_room(self, user_id: str, room_id: str, user_info: dict):
        user_id = str(user_id)
        self.user_rooms[user_id] = room_id
        if room_id not in self.room_members:
            self.room_members[room_id] = set()

        self.room_members[room_id].add(user_id)

        # Initialize participant state
        self.participant_states[user_id] = {
            "user_id": user_id,
            "username": user_info.get("username", "Unknown"),
            "joined_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "is_muted": False,
            "camera_on": True,
            "hand_raised": False,
            "is_mirrored": False
        }

        # Notify others in the room
        await self.broadcast_to_room(room_id, {
            "type": "participant_joined",
            "user_id": user_id,
            "info": self.participant_states[user_id]
        }, exclude_user=user_id)

        # Send current members to the joining user
        members = []
        for member_id in self.room_members[room_id]:
            if member_id != user_id:
                members.append(self.participant_states.get(member_id, {"user_id": member_id}))

        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json({
                "type": "room_state",
                "room_id": room_id,
                "participants": members
            })

    def get_participant_info(self, user_id: str) -> dict:
        return self.participant_states.get(user_id)

    async def broadcast_to_room(self, room_id: str, data: dict, exclude_user: str = None):
        if room_id not in self.room_members:
            return

        message = json.dumps(data)
        for member_id in list(self.room_members[room_id]):
            if member_id == str(exclude_user):
                continue
            if member_id in self.active_connections:
                try:
                    await self.active_connections[member_id].send_text(message)
                except Exception:
                    pass

    async def send_signaling(self, target_id: str, data: dict):
        target_id = str(target_id)
        if target_id in self.active_connections:
            await self.active_connections[target_id].send_json(data)
        elif self.redis_client:
            await self.redis_client.publish("snlag_signaling", json.dumps(data))

    async def _local_broadcast(self, data: dict, scope: str = "user"):
        message = json.dumps(data)
        target_connections = self.active_connections if scope == "user" else self.admin_connections
        for ws in list(target_connections.values()):
            try:
                await ws.send_text(message)
            except Exception:
                pass

    async def broadcast_json(self, data: dict, scope: str = "user"):
        if self.redis_client:
            try:
                payload = data.copy()
                payload["_ws_scope"] = scope
                await self.redis_client.publish("snlag_broadcast", json.dumps(payload))
                return
            except Exception as e:
                logger.error(f"WS: Redis Publish Failed: {e}")

        await self._local_broadcast(data, scope)

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket, token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scope: str = payload.get("scope")
        if username is None:
            await websocket.close(code=4001)
            return

        db = SessionLocal()
        if scope == "admin":
            user = db.query(AdminModel).filter(AdminModel.username == username, AdminModel.is_active == True).first()
        else:
            user = db.query(UserModel).filter(UserModel.username == username, UserModel.is_active == True).first()
        db.close()

        if not user:
            await websocket.close(code=4001)
            return

        user_id = str(user.id)
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id, scope=scope)

    buffer = collections.deque(maxlen=30)
    inference_lock = asyncio.Lock()
    last_inference_time = 0
    state = {"language": "English"}
    MIN_INFERENCE_INTERVAL = 0.15

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                data_bytes = message["bytes"]
                landmarks = np.frombuffer(data_bytes, dtype=np.float32).tolist()
                buffer.append(landmarks)

                now = time.time()
                if len(buffer) == 30 and not inference_lock.locked() and (now - last_inference_time) > MIN_INFERENCE_INTERVAL:
                    last_inference_time = now
                    asyncio.create_task(run_ws_inference(websocket, list(buffer), state, user_id, inference_lock))

            elif "text" in message:
                data_text = message["text"]
                msg = json.loads(data_text)
                msg_type = msg.get("type")

                if msg_type == "set_language":
                    state["language"] = msg.get("language", "English")
                elif msg_type == "join_room":
                    room_id = msg.get("room_id")
                    if room_id:
                        await manager.join_room(user_id, room_id, {"username": username})
                elif msg_type in ["webrtc_offer", "webrtc_answer", "webrtc_ice_candidate"]:
                    target_id = msg.get("target_id")
                    if target_id:
                        msg["sender_id"] = user_id
                        await manager.send_signaling(str(target_id), msg)
                elif msg_type == "meeting_action":
                    room_id = manager.user_rooms.get(user_id)
                    if room_id:
                        action = msg.get("action")
                        value = msg.get("value")
                        if action in ["mute", "camera", "hand_raise", "mirror"]:
                            state_key = {
                                "mute": "is_muted",
                                "camera": "camera_on",
                                "hand_raise": "hand_raised",
                                "mirror": "is_mirrored"
                            }[action]
                            if user_id in manager.participant_states:
                                manager.participant_states[user_id][state_key] = value

                        msg["user_id"] = user_id
                        await manager.broadcast_to_room(room_id, msg, exclude_user=user_id)
                elif msg_type == "speech_text":
                    text_val = msg.get("text", "")
                    if text_val:
                        from ai_orchestration.services.orchestrator import orchestrator
                        res = await orchestrator.speech_to_sign(text_val.encode(), language=state["language"])
                        await websocket.send_json({
                            "type": "translation_result",
                            "original_text": text_val,
                            "result": res.get("result")
                        })

            elif message.get("type") == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        logger.info(f"WS: User {user_id} disconnected.")
    except Exception as e:
        if "disconnect" not in str(e).lower():
            logger.error(f"WS Error for user {user_id}: {e}")
    finally:
        manager.disconnect(user_id)
        try:
            await websocket.close()
        except:
            pass

async def run_ws_inference(ws: WebSocket, buffer: list, state: dict, user_id: str, lock: asyncio.Lock):
    async with lock:
        try:
            from ai_orchestration.services.orchestrator import orchestrator
            res = await orchestrator.sign_to_speech(buffer, language=state["language"])
            if res["status"] == "success":
                sign = res["text"]
                conf = res["confidence"]

                if conf > 0.92:
                    harvest_data(user_id, buffer, sign, conf)

                await ws.send_json({
                    "type": "prediction",
                    "sign": sign,
                    "confidence": conf,
                    "meaning": res.get("meaning"),
                    "sign_type": res.get("sign_type"),
                    "audio_base64": base64.b64encode(res["audio"]).decode() if "audio" in res else None
                })

                # Also broadcast translation to the room if in a meeting
                room_id = manager.user_rooms.get(user_id)
                if room_id:
                    await manager.broadcast_to_room(room_id, {
                        "type": "remote_translation",
                        "user_id": user_id,
                        "sign": sign,
                        "confidence": conf
                    }, exclude_user=user_id)

        except Exception as e:
            logger.error(f"WS Inference failure: {e}")

def harvest_data(user_id: str, landmarks: list, label: str, conf: float):
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
    except Exception as e:
        logger.error(f"Harvest failure: {e}")
    finally: db.close()
