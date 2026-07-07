import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from jose import jwt
from ai_orchestration.core.config import SECRET_KEY, ALGORITHM
from database_layer.db_manager import SessionLocal, UserModel

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJRdWFzb24iLCJleHAiOjE3ODI2NDAzNDYsInNjb3BlIjoidXNlciJ9.ehNsIJaSKD5sUw44urzFK8M_wrg4bw6h7sRLIdCdW1M"

try:
    print(f"SECRET_KEY: {SECRET_KEY}")
    print(f"ALGORITHM: {ALGORITHM}")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"Decoded payload: {payload}")
    username = payload.get("sub")
    scope = payload.get("scope")
    print(f"username: {username}, scope: {scope}")
    
    db = SessionLocal()
    user = db.query(UserModel).filter(UserModel.username == username, UserModel.is_deleted == False).first()
    print(f"Found user in DB: {user}")
    if user:
        print(f"  username: {user.username}")
        print(f"  is_active: {user.is_active}")
        print(f"  is_deleted: {user.is_deleted}")
    db.close()
except Exception as e:
    print(f"Error: {e}")
