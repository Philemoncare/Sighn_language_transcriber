from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ai_orchestration.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from ai_orchestration.auth.security import create_access_token, create_refresh_token, verify_password
from ai_orchestration.api.deps import get_db, get_current_user
from database_layer.db_manager import UserModel, RefreshTokenModel

router = APIRouter()

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(
        UserModel.username == form_data.username,
        UserModel.is_deleted == False
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")


    access = create_access_token(data={"sub": user.username})
    refresh = create_refresh_token(data={"sub": user.username})

    # Update refresh token in DB
    db.query(RefreshTokenModel).filter(RefreshTokenModel.user_id == user.id).delete()
    db.add(RefreshTokenModel(
        token=refresh,
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    ))
    db.commit()

    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}

@router.get("/users/me")
async def read_users_me(current_user: UserModel = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }
