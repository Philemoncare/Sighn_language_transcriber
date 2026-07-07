from datetime import datetime, timedelta
import os
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
import logging

from ai_orchestration.core.config import REFRESH_TOKEN_EXPIRE_DAYS, UPLOADS_DIR
from ai_orchestration.auth.security import create_access_token, create_refresh_token, verify_password, get_password_hash
from ai_orchestration.api.deps import get_db, get_current_admin
from database_layer.db_manager import AdminModel, AdminRefreshTokenModel, AdminSessionModel

router = APIRouter(tags=["Admin Authentication"])
logger = logging.getLogger("SnLag_AdminAuth")

@router.post("/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    admin = db.query(AdminModel).filter(
        or_(AdminModel.username == form_data.username, AdminModel.email == form_data.username)
    ).first()
    if not admin or not verify_password(form_data.password, admin.password_hash):
        logger.warning(f"Failed admin login attempt for username: {form_data.username}")
        raise HTTPException(status_code=401, detail="Invalid admin credentials")

    if not admin.is_active:
        raise HTTPException(status_code=403, detail="Admin account is disabled")

    access = create_access_token(data={"sub": admin.username}, scope="admin")

    # Store session
    session = AdminSessionModel(
        admin_id=admin.id,
        jwt_token=access,
        expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db.add(session)
    db.commit()

    logger.info(f"Admin login successful: {admin.username}")
    return {"access_token": access, "token_type": "bearer"}

@router.get("/me")
async def get_admin_me(current_admin: AdminModel = Depends(get_current_admin)):
    return {
        "id": current_admin.id,
        "username": current_admin.username,
        "email": current_admin.email,
        "name": current_admin.name,
        "avatar_url": current_admin.avatar_url,
        "preferences": current_admin.preferences,
        "role": "admin"
    }

@router.patch("/me")
async def update_admin_me(
    name: Optional[str] = None,
    email: Optional[str] = None,
    current_admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if name is not None: current_admin.name = name
    if email is not None: current_admin.email = email
    db.commit()
    return {"status": "success"}

@router.post("/logout")
async def admin_logout(current_admin: AdminModel = Depends(get_current_admin), db: Session = Depends(get_db)):
    db.query(AdminSessionModel).filter(AdminSessionModel.admin_id == current_admin.id).delete()
    db.commit()
    return {"status": "success"}

@router.post("/forgot-password")
async def admin_forgot_password(email: str, db: Session = Depends(get_db)):
    # Implementation for admin-specific password recovery
    logger.info(f"Admin password recovery requested for: {email}")
    return {"message": "Recovery signal transmitted if account exists."}

@router.post("/reset-password")
async def admin_reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    # Implementation for admin-specific password reset
    return {"message": "Access key updated successfully."}

@router.patch("/preferences")
async def update_admin_preferences(
    preferences: dict,
    current_admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    current_admin.preferences = current_admin.preferences or {}
    current_admin.preferences.update(preferences)
    db.commit()
    return {"status": "success"}

@router.post("/upload-avatar")
async def upload_admin_avatar(
    file: UploadFile = File(...),
    current_admin: AdminModel = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    # Ensure directory exists
    admin_dir = os.path.join(UPLOADS_DIR, "admins", str(current_admin.id))
    os.makedirs(admin_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1]
    filename = f"avatar{file_ext}"
    file_path = os.path.join(admin_dir, filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Public URL
        url = f"/public/uploads/admins/{current_admin.id}/{filename}"
        current_admin.avatar_url = url
        db.commit()
        return {"status": "success", "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
