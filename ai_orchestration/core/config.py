import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_NAME = "SnLag Universal Core"
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
    db_path = os.path.join(project_root, "snlag.db")
    DATABASE_URL = f"sqlite:///{db_path}"

# Directories
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "public", "uploads")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
MP_DATA_ROOT = os.path.join(PROJECT_ROOT, "MP_Data")

# Admin defaults
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
