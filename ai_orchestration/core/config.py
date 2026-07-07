import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME = "Signly"
VERSION = "2.0.0"
API_V1_STR = ""

# Security
SECRET_KEY = os.getenv("SECRET_KEY") or "your-super-secret-key-change-it"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Database
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(project_root, "signly.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# Directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "public", "uploads")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MP_DATA_ROOT = os.path.join(PROJECT_ROOT, "MP_Data")

# Admin defaults
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# Site Context
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# Redis Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
REDIS_SOCKET_TIMEOUT = 30
REDIS_RETRY_ON_TIMEOUT = True

# Mail Settings
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_USER = "signly.dev@gmail.com"
SMTP_PASS = "snpi hmix tyvt siwz" # Managed via Google App Password
