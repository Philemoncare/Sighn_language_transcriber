from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ai_orchestration.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from ai_orchestration.auth.security import create_access_token, create_refresh_token, verify_password, get_password_hash
from ai_orchestration.api.deps import get_db, get_current_user
from database_layer.db_manager import UserModel, RefreshTokenModel

router = APIRouter()

@router.post("/register")
async def register(user_data: dict, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(UserModel).filter(UserModel.username == user_data['username']).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = UserModel(
        username=user_data['username'],
        email=user_data.get('email'),
        hashed_password=get_password_hash(user_data['password']),
        role="user",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"status": "success", "username": new_user.username}

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
        "full_name": current_user.full_name,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "banner_url": current_user.banner_url,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "preferences": current_user.preferences,
        "created_at": current_user.created_at
    }

@router.put("/users/me")
async def update_user_me(data: dict, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    if 'full_name' in data: current_user.full_name = data['full_name']
    if 'bio' in data: current_user.bio = data['bio']
    if 'email' in data: current_user.email = data['email']
    if 'preferences' in data:
        prefs = current_user.preferences or {}
        prefs.update(data['preferences'])
        current_user.preferences = prefs

    db.commit()
    return {"status": "success"}

@router.delete("/users/me")
async def delete_user_me(db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    current_user.is_deleted = True
    db.commit()
    return {"status": "success"}

@router.post("/users/me/password")
async def change_password(data: dict, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    if not verify_password(data['current_password'], current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    current_user.hashed_password = get_password_hash(data['new_password'])
    db.commit()
    return {"status": "success"}
