import uuid
import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ai_orchestration.api.deps import get_db, get_current_user, get_onboarded_user
from database_layer.db_manager import UserModel
from ai_orchestration.websocket.handler import manager

router = APIRouter()

# In-memory session tracking for room metadata
# Note: Persistent metadata could be moved to DB if needed
ROOM_METADATA: Dict[str, dict] = {}

class ParticipantInfo(BaseModel):
    user_id: str
    username: str
    joined_at: str
    is_muted: bool = False
    camera_on: bool = True
    hand_raised: bool = False

class RoomInfo(BaseModel):
    room_id: str
    room_name: str
    host_id: str # Fixed: host_id should be string to match UUID id
    created_at: str
    participants: List[ParticipantInfo]

class CreateRoomRequest(BaseModel):
    room_name: Optional[str] = "Discussion Room"

@router.post("/rooms", response_model=RoomInfo)
async def create_room(request: CreateRoomRequest, current_user: UserModel = Depends(get_onboarded_user)):
    room_id = str(uuid.uuid4())[:8].upper()
    room_name = request.room_name or f"{current_user.username}'s Room"

    room_data = {
        "room_id": room_id,
        "room_name": room_name,
        "host_id": current_user.id,
        "created_at": datetime.datetime.now().isoformat(),
    }

    ROOM_METADATA[room_id] = room_data
    return RoomInfo(**room_data, participants=[])

@router.get("/rooms/{room_id}", response_model=RoomInfo)
async def get_room_details(room_id: str, current_user: UserModel = Depends(get_onboarded_user)):
    if room_id not in ROOM_METADATA:
        raise HTTPException(status_code=404, detail="Meeting room not found")

    metadata = ROOM_METADATA[room_id]
    # Get active participants from ConnectionManager
    participants = []
    member_ids = manager.room_members.get(room_id, set())
    for uid in member_ids:
        # We need participant details. For now we use basic info.
        # In a real app, we'd store participant state in manager.room_members_info[room_id][uid]
        p_info = manager.get_participant_info(uid)
        if p_info:
            participants.append(p_info)

    return RoomInfo(**metadata, participants=participants)

@router.delete("/rooms/{room_id}")
async def close_room(room_id: str, current_user: UserModel = Depends(get_current_user)):
    if room_id not in ROOM_METADATA:
        raise HTTPException(status_code=404, detail="Room not found")

    if ROOM_METADATA[room_id]["host_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Only host can terminate meeting")

    # Notify everyone and close
    await manager.broadcast_to_room(room_id, {"type": "room_closed"})
    del ROOM_METADATA[room_id]
    return {"status": "success", "message": "Room closed"}
