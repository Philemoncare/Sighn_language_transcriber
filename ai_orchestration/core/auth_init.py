import logging
from ai_orchestration.core.config import ADMIN_USERNAME, ADMIN_PASSWORD
from ai_orchestration.auth.security import get_password_hash
from database_layer.db_manager import SessionLocal, UserModel

logger = logging.getLogger("SnLag_AuthInit")

def ensure_admin_exists():
    db = SessionLocal()
    try:
        if db.query(UserModel).filter(UserModel.role == "admin").count() == 0:
            admin = UserModel(
                username=ADMIN_USERNAME,
                email=f"{ADMIN_USERNAME}@snlag.local",
                role="admin",
                is_active=True,
                hashed_password=get_password_hash(ADMIN_PASSWORD)
            )
            db.add(admin)
            db.commit()
            logger.info(f"Security: Default admin '{ADMIN_USERNAME}' created.")
    except Exception as e:
        logger.error(f"Failed to ensure admin exists: {e}")
    finally:
        db.close()
