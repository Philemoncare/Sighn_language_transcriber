from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean, Float, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy import create_engine
import datetime
import os
import uuid

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

Base = declarative_base()

# Architecture requirement: Support both production (Postgres) and local dev (SQLite)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Resolve project root strictly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "signly.db")
    DATABASE_URL = f"sqlite:///{db_path}"

engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    # STRICT CONNECTION POLICY: Increase timeout for concurrent writes and disable thread checking
    engine_args["connect_args"] = {"check_same_thread": False, "timeout": 60}

engine = create_engine(DATABASE_URL, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_uuid():
    return str(uuid.uuid4())

class AdminModel(Base):
    __tablename__ = "admins"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    avatar_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, default={"theme": "light"})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Isolated admin relations
    refresh_tokens = relationship("AdminRefreshTokenModel", back_populates="admin", cascade="all, delete-orphan")

class AdminRefreshTokenModel(Base):
    __tablename__ = "admin_refresh_tokens"
    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True, nullable=False)
    admin_id = Column(String, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    admin = relationship("AdminModel", back_populates="refresh_tokens")

class AdminSessionModel(Base):
    __tablename__ = "admin_sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    admin_id = Column(String, ForeignKey("admins.id", ondelete="CASCADE"), nullable=False)
    jwt_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    bio = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    banner_url = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user") # "admin" or "user"
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    preferences = Column(JSON, default={"theme": "dark", "notifications": True})
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # STRICT CONNECTIONS: Bidirectional relationships
    refresh_tokens = relationship("UserRefreshTokenModel", back_populates="user", cascade="all, delete-orphan")
    onboarding = relationship("OnboardingProfileModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("ConversationModel", back_populates="user", cascade="all, delete-orphan")
    data_points = relationship("CollectedDataModel", back_populates="user", cascade="all, delete-orphan")

class UserRefreshTokenModel(Base):
    __tablename__ = "user_refresh_tokens"
    id = Column(String, primary_key=True, default=generate_uuid)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("UserModel", back_populates="refresh_tokens")

class UserSessionModel(Base):
    __tablename__ = "user_sessions"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    jwt_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class OnboardingProfileModel(Base):
    __tablename__ = "onboarding_profiles"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email = Column(String, nullable=True)
    preferred_name = Column(String, nullable=True)
    country = Column(String, nullable=True)
    preferred_language = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    purpose = Column(String, nullable=True)
    primary_goal = Column(String, nullable=True)
    usage_style = Column(String, nullable=True)
    interests = Column(JSON, default=[])
    workspace_preference = Column(String, nullable=True)
    recognition_preference = Column(String, nullable=True)
    accessibility_needs = Column(String, nullable=True)
    accessibility_preferences = Column(JSON, default={})
    learning_goals = Column(JSON, default=[])
    last_step = Column(Integer, default=0)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("UserModel", back_populates="onboarding")

class OTPModel(Base):
    __tablename__ = "otps"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    purpose = Column(String, nullable=False) # "registration" | "login"
    expires_at = Column(DateTime, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ConversationModel(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    message_type = Column(String) # speech or sign
    original_content = Column(String)
    translated_content = Column(String)
    language = Column(String, default="English")
    confidence = Column(Float, default=0.0)

    user = relationship("UserModel", back_populates="conversations")

class CollectedDataModel(Base):
    __tablename__ = "collected_data"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    data_type = Column(String) # "sign" or "speech"
    payload = Column(JSON)
    label = Column(String, nullable=True)
    confidence = Column(Float, default=0.0)
    is_validated = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("UserModel", back_populates="data_points")

class SystemLogModel(Base):
    __tablename__ = "system_logs"
    id = Column(String, primary_key=True, default=generate_uuid)
    level = Column(String) # INFO, WARNING, ERROR, CRITICAL
    service = Column(String, default="kernel") # frontend, backend, ai_engine, extraction, db, auth
    category = Column(String, nullable=True) # startup, inference, upload, training, security
    message = Column(String)
    details = Column(JSON, nullable=True) # Full message, stack trace, etc.
    request_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    dataset_id = Column(String, nullable=True)
    duration = Column(Float, nullable=True) # Execution time in ms
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

class SignDatasetModel(Base):
    __tablename__ = "sign_datasets"
    id = Column(String, primary_key=True, default=generate_uuid)
    parent_id = Column(String, ForeignKey("sign_datasets.id"), nullable=True) # For segmented signs
    label = Column(String, nullable=False)
    language = Column(String, default="English")
    category = Column(String, nullable=True)
    description = Column(String, nullable=True)
    source_type = Column(String, default="video") # video, image, sequence, segmented
    version = Column(Integer, default=1)

    file_path = Column(String, nullable=True) # Original file
    video_path = Column(String, nullable=True) # Back-compat
    landmark_path = Column(String, nullable=True) # Processed data dir
    file_hash = Column(String, index=True, nullable=True)

    status = Column(String, default="pending")
    progress = Column(Integer, default=0)
    quality_score = Column(Float, default=0.0)
    extraction_metadata = Column(JSON, default={})

    is_augmented = Column(Boolean, default=False)
    is_validated = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Self-referential for segmented items
    sub_items = relationship("SignDatasetModel", backref=backref('parent', remote_side=[id]))

class DatasetVersionModel(Base):
    __tablename__ = "dataset_versions"
    id = Column(String, primary_key=True, default=generate_uuid)
    version_number = Column(Integer, nullable=False)
    snapshot_meta = Column(JSON) # List of dataset IDs included
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class TrainingJobModel(Base):
    __tablename__ = "training_jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    job_name = Column(String)
    status = Column(String, default="pending") # pending, training, evaluating, completed, failed
    progress = Column(Integer, default=0)
    current_epoch = Column(Integer, default=0)
    total_epochs = Column(Integer, default=0)
    metrics = Column(JSON, default={"accuracy": 0, "loss": 0, "val_accuracy": 0, "val_loss": 0})
    config = Column(JSON)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class ModelVersionModel(Base):
    __tablename__ = "model_versions"
    id = Column(String, primary_key=True, default=generate_uuid)
    version_tag = Column(String, unique=True)
    file_path = Column(String)
    is_active = Column(Boolean, default=False)
    metrics = Column(JSON) # accuracy, precision, recall, f1
    supported_languages = Column(JSON)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class GestureLibraryModel(Base):
    __tablename__ = "gesture_libraries"
    id = Column(String, primary_key=True, default=generate_uuid)
    gesture_name = Column(String)
    description = Column(String, nullable=True)
    category = Column(String, default="general") # general, greetings, emergency, local
    language_code = Column(String, default="en")
    is_pretrained = Column(Boolean, default=False)
    landmark_mapping = Column(JSON)
    is_deleted = Column(Boolean, default=False)

class AppSettingModel(Base):
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True)
    value = Column(JSON)
    description = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

def init_db():
    # STRICT MIGRATION ENFORCEMENT
    Base.metadata.create_all(bind=engine)

    # RESILIENCE: Ensure tables have required columns (Migration helper for dev)
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                # 1. Migrate users table
                user_cols = ["bio", "phone", "avatar_url", "banner_url", "role", "is_verified", "is_active", "is_deleted", "preferences"]
                for col in user_cols:
                    try:
                        if col == "preferences":
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} TEXT"))
                        elif col.startswith("is_"):
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} BOOLEAN DEFAULT 0"))
                        else:
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR"))
                    except:
                        pass

                # 2. Migrate onboarding_profiles table
                onboarding_cols = [
                    "email", "preferred_name", "country", "preferred_language",
                    "experience_level", "purpose", "primary_goal", "usage_style",
                    "workspace_preference", "recognition_preference", "accessibility_needs",
                    "last_step", "completed", "completed_at"
                ]
                for col in onboarding_cols:
                    try:
                        if col == "completed":
                            conn.execute(text(f"ALTER TABLE onboarding_profiles ADD COLUMN {col} BOOLEAN DEFAULT 0"))
                        elif col == "last_step":
                            conn.execute(text(f"ALTER TABLE onboarding_profiles ADD COLUMN {col} INTEGER DEFAULT 0"))
                        elif col == "completed_at":
                            conn.execute(text(f"ALTER TABLE onboarding_profiles ADD COLUMN {col} DATETIME"))
                        else:
                            conn.execute(text(f"ALTER TABLE onboarding_profiles ADD COLUMN {col} VARCHAR"))
                    except:
                        pass

                # Add JSON columns
                for col in ["accessibility_preferences", "learning_goals", "interests"]:
                    try:
                        conn.execute(text(f"ALTER TABLE onboarding_profiles ADD COLUMN {col} TEXT"))
                    except:
                        pass

                # 3. Migrate gesture_libraries
                try:
                    conn.execute(text("ALTER TABLE gesture_libraries ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
                except: pass

                # 4. Migrate sign_datasets
                try:
                    conn.execute(text("ALTER TABLE sign_datasets ADD COLUMN is_deleted BOOLEAN DEFAULT 0"))
                except: pass

                conn.commit()
        except Exception as e:
            print(f"Migration Warning: {e}")

def check_db_health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception:
        return False

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
