import logging
from ai_orchestration.core.config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL
from ai_orchestration.auth.security import get_password_hash
from database_layer.db_manager import SessionLocal, AdminModel

logger = logging.getLogger("SnLag_AuthInit")

def ensure_admin_exists():
    db = SessionLocal()
    try:
        if db.query(AdminModel).count() == 0:
            admin = AdminModel(
                username=ADMIN_USERNAME,
                email=ADMIN_EMAIL or f"{ADMIN_USERNAME}@signly.local",
                is_active=True,
                password_hash=get_password_hash(ADMIN_PASSWORD)
            )
            db.add(admin)
            db.commit()
            logger.info(f"Security: Default admin '{ADMIN_USERNAME}' created.")
    except Exception as e:
        logger.error(f"Failed to ensure admin exists: {e}")
    finally:
        db.close()
