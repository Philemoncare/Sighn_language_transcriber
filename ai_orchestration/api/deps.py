from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from ai_orchestration.core.config import SECRET_KEY, ALGORITHM
from database_layer.db_manager import SessionLocal, UserModel, get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print(f"DEBUG AUTH: sub is missing in token")
            raise credentials_exception
    except JWTError as e:
        print(f"DEBUG AUTH: Token decode failed: {e}")
        raise credentials_exception

    user = db.query(UserModel).filter(UserModel.username == username, UserModel.is_deleted == False).first()
    if user is None:
        print(f"DEBUG AUTH: User '{username}' not found or deleted")
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive node")

    return user

async def get_current_admin(current_user: UserModel = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user
