from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from typing import Optional

from ai_orchestration.core.config import SECRET_KEY, ALGORITHM
from database_layer.db_manager import SessionLocal, UserModel, AdminModel, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/auth/login")
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/admin/auth/login")

async def get_current_user_ws(token: Optional[str] = None, db: Session = Depends(get_db)):
    if token is None:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scope: str = payload.get("scope")
        if username is None or scope != "user":
            return None
        user = db.query(UserModel).filter(UserModel.username == username, UserModel.is_active == True, UserModel.is_deleted == False).first()
        return user
    except:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scope: str = payload.get("scope")
        if username is None or scope != "user":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user = db.query(UserModel).filter(UserModel.username == username, UserModel.is_deleted == False).first()
    except Exception:
        # Fallback for during migrations
        user = db.query(UserModel).filter(UserModel.username == username).first()

    if user is None:
        raise credentials_exception
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")

    return user

async def get_current_admin(token: str = Depends(admin_oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate admin credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        scope: str = payload.get("scope")
        if username is None or scope != "admin":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    admin = db.query(AdminModel).filter(AdminModel.username == username, AdminModel.is_active == True).first()
    if admin is None:
        raise credentials_exception

    return admin

async def get_onboarded_user(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    from database_layer.db_manager import OnboardingProfileModel
    profile = db.query(OnboardingProfileModel).filter(OnboardingProfileModel.user_id == current_user.id).first()
    if not profile or not profile.completed:
        raise HTTPException(status_code=403, detail="Onboarding mandatory for this operation")
    return current_user
