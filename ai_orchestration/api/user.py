import os
import shutil
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from ai_orchestration.api.deps import get_db, get_current_user, get_onboarded_user
from ai_orchestration.core.config import UPLOADS_DIR
from database_layer.db_manager import UserModel, ConversationModel, GestureLibraryModel

router = APIRouter(tags=["User Profile"])
logger = logging.getLogger("SnLag_UserAPI")

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None
    preferences: Optional[dict] = None

@router.get("/profile/me")
async def get_my_profile(current_user: UserModel = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "name": current_user.name,
        "email": current_user.email,
        "bio": current_user.bio,
        "phone": current_user.phone,
        "avatar_url": current_user.avatar_url,
        "banner_url": current_user.banner_url,
        "preferences": current_user.preferences,
        "role": current_user.role,
        "created_at": current_user.created_at
    }

@router.patch("/profile/me")
async def update_my_profile(
    data: ProfileUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.name is not None: current_user.name = data.name
    if data.bio is not None: current_user.bio = data.bio
    if data.phone is not None: current_user.phone = data.phone
    if data.preferences is not None:
        prefs = current_user.preferences or {}
        prefs.update(data.preferences)
        current_user.preferences = prefs

    db.commit()
    return {"status": "success", "message": "Profile updated successfully"}

@router.get("/history")
async def get_translation_history(
    current_user: UserModel = Depends(get_onboarded_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    history = db.query(ConversationModel).filter(
        ConversationModel.user_id == current_user.id
    ).order_by(ConversationModel.timestamp.desc()).limit(limit).all()

    return history

@router.get("/library")
async def get_sign_library(
    db: Session = Depends(get_db),
    category: Optional[str] = None
):
    query = db.query(GestureLibraryModel).filter(GestureLibraryModel.is_deleted == False)
    if category:
        query = query.filter(GestureLibraryModel.category == category)

    return query.all()

@router.get("/profile/ping")
async def ping_user_api():
    return {"status": "online", "service": "Neural User API"}

@router.post("/profile/upload")
async def upload_user_image(
    type: str = Form(...),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Neural Image Synchronization Endpoint
    Synchronizes local binary image data with the cloud storage core.
    """
    if type not in ["avatar", "banner"]:
        logger.warning(f"Rejected upload attempt for invalid type: {type}")
        raise HTTPException(status_code=400, detail="Invalid image type target")

    # Ensure directory exists in public space
    user_dir = os.path.join(UPLOADS_DIR, "users", str(current_user.id))
    try:
        os.makedirs(user_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create user directory {user_dir}: {e}")
        raise HTTPException(status_code=500, detail="Neural storage initialization failed")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.jpg', '.jpeg', '.png', '.webp']:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    filename = f"{type}{file_ext}"
    file_path = os.path.join(user_dir, filename)

    logger.info(f"Synchronizing {type} for user {current_user.username}...")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Public relative URL for the frontend mount
        url = f"/public/uploads/users/{current_user.id}/{filename}"

        if type == "avatar":
            current_user.avatar_url = url
        else:
            current_user.banner_url = url

        db.commit()
        logger.info(f"Successful synchronization of {type} at {url}")
        return {"status": "success", "url": url}
    except Exception as e:
        logger.error(f"Synchronization failure for {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Neural Core synchronization failed")
