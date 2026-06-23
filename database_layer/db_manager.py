from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
import datetime
import os

Base = declarative_base()

# Architecture requirement: Support both production (Postgres) and local dev (SQLite)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Use absolute path for SQLite to avoid multi-file confusion
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(project_root, "snlag.db")
    DATABASE_URL = f"sqlite:///{db_path}"

engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

try:
    engine = create_engine(DATABASE_URL, **engine_args)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    # Final fallback if Postgres string was provided but failed
    DATABASE_URL = "sqlite:///./snlag.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # "admin" or "user"
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, default={"theme": "light"})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SignDatasetModel(Base):
    __tablename__ = "sign_datasets"
    id = Column(Integer, primary_key=True, index=True)
    label = Column(String)
    language = Column(String, default="English") # English, French, Portuguese, GSL, Twi
    video_path = Column(String, nullable=True)
    landmark_path = Column(String, nullable=True)
    is_augmented = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TrainingJobModel(Base):
    __tablename__ = "training_jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String)
    status = Column(String, default="pending") # pending, training, completed, failed
    progress = Column(Integer, default=0)
    config = Column(JSON) # epochs, batch_size, learning_rate, model_type
    accuracy = Column(String, nullable=True)
    loss = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class ModelVersionModel(Base):
    __tablename__ = "model_versions"
    id = Column(Integer, primary_key=True, index=True)
    version_tag = Column(String, unique=True)
    file_path = Column(String)
    is_active = Column(Boolean, default=False)
    metrics = Column(JSON) # accuracy, precision, recall, f1
    supported_languages = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ConversationModel(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    message_type = Column(String) # speech or sign
    original_content = Column(String)
    translated_content = Column(String)
    confidence = Column(Float, default=0.0)

class SystemLogModel(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class GestureLibraryModel(Base):
    __tablename__ = "gesture_libraries"
    id = Column(Integer, primary_key=True, index=True)
    gesture_name = Column(String)
    landmark_mapping = Column(JSON)

class CollectedDataModel(Base):
    __tablename__ = "collected_data"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    data_type = Column(String) # "sign" or "speech"
    payload = Column(JSON) # Landmark sequence or audio reference
    label = Column(String, nullable=True) # Predicted or user-corrected label
    confidence = Column(Float, default=0.0)
    is_validated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
