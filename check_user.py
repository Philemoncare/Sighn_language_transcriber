import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from database_layer.db_manager import SessionLocal, UserModel, AdminModel
from ai_orchestration.auth.security import verify_password, get_password_hash

def check():
    db = SessionLocal()
    email = "favmoms440@gmail.com"
    password = "philemon293"

    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user:
        print(f"User: {user.username}")
        print(f"Hash: {user.password_hash}")
        match = verify_password(password, user.password_hash)
        print(f"Match with 'philemon293': {match}")

        # Test hashing it now
        new_hash = get_password_hash(password)
        print(f"New Hash: {new_hash}")
        print(f"Match with new hash: {verify_password(password, new_hash)}")
    else:
        print("User not found")

    db.close()

if __name__ == "__main__":
    check()
