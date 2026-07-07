import base64
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ai_orchestration.api.deps import get_db, get_current_user, get_onboarded_user
from ai_orchestration.services.orchestrator import orchestrator
from database_layer.db_manager import UserModel, ConversationModel

router = APIRouter()

class TranslationRequest(BaseModel):
    source_type: str # "speech" or "sign"
    payload: str # base64 audio or landmark sequence
    language: str = "English"

@router.post("/translate")
async def translate(request: TranslationRequest, current_user: UserModel = Depends(get_onboarded_user), db: Session = Depends(get_db)):
    if request.source_type == "speech":
        audio = base64.b64decode(request.payload)
        res = await orchestrator.speech_to_sign(audio, language=request.language)
        if res["status"] == "success":
             db.add(ConversationModel(
                user_id=current_user.id,
                message_type="speech",
                original_content=res["original_text"],
                translated_content=str(res["result"].get("sequence", [])),
                language=request.language,
                confidence=1.0
            ))
             db.commit()
        return res

    elif request.source_type == "sign":
        landmarks = json.loads(request.payload)
        res = await orchestrator.sign_to_speech(landmarks, language=request.language)
        if res["status"] == "success":
            db.add(ConversationModel(
                user_id=current_user.id,
                message_type="sign",
                original_content=res["text"],
                translated_content="Audio",
                language=request.language,
                confidence=res["confidence"]
            ))
            db.commit()
            return {
                "status": "success",
                "text": res["text"],
                "confidence": res["confidence"],
                "audio_base64": base64.b64encode(res["audio"]).decode()
            }
        return res

    raise HTTPException(status_code=400, detail="Invalid source type")
