import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from database_layer.db_manager import SessionLocal, UserModel
from ai_orchestration.auth.security import get_password_hash

def fix():
    db = SessionLocal()
    email = "favmoms440@gmail.com"
    new_password = "philemon293"

    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user:
        user.password_hash = get_password_hash(new_password)
        db.commit()
        print(f"Password for {email} has been reset to '{new_password}' and saved to DB.")
    else:
        print("User not found.")
    db.close()

if __name__ == "__main__":
    fix()
