from datetime import datetime, timedelta
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import or_
import random

from ai_orchestration.core.config import REFRESH_TOKEN_EXPIRE_DAYS, PROJECT_NAME
from ai_orchestration.auth.security import create_access_token, create_refresh_token, verify_password, get_password_hash
from ai_orchestration.api.deps import get_db, get_current_user
from ai_orchestration.services.mail_service import send_verification_signal, send_welcome_signal
from database_layer.db_manager import UserModel, UserRefreshTokenModel, OTPModel, UserSessionModel, AdminModel, AdminSessionModel
import logging

router = APIRouter(tags=["User Authentication"])
logger = logging.getLogger("SnLag_UserAuth")

@router.get("/ping")
async def ping_auth():
    return {"status": "ok", "service": "UserAuth"}

@router.post("/request-otp")
async def request_otp(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    purpose = data.get("purpose")
    if not email: raise HTTPException(status_code=400, detail="Email is required")
    otp_code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)
    db.add(OTPModel(email=email, otp_code=otp_code, purpose=purpose, expires_at=expires))
    db.commit()

    logger.info(f"User OTP requested: {email} for {purpose}")
    await send_verification_signal(email, otp_code, purpose)
    return {"status": "success", "message": "OTP transmitted."}

@router.post("/register")
async def register(user_data: dict, bt: BackgroundTasks, db: Session = Depends(get_db)):
    otp_record = db.query(OTPModel).filter(
        OTPModel.email == user_data.get('email'),
        OTPModel.otp_code == user_data.get('otp'),
        OTPModel.purpose == "registration",
        OTPModel.expires_at > datetime.utcnow()
    ).first()
    if not otp_record: raise HTTPException(status_code=400, detail="Invalid OTP")
    if db.query(UserModel).filter(UserModel.username == user_data['username']).first():
        raise HTTPException(status_code=400, detail="Username taken")

    new_user = UserModel(
        username=user_data['username'],
        email=user_data.get('email'),
        name=user_data.get('fullname'),
        password_hash=get_password_hash(user_data['password']),
        role="user",
        is_active=True
    )
    db.add(new_user)
    db.delete(otp_record)
    db.commit()

    logger.info(f"New user registered: {new_user.username}")
    bt.add_task(send_welcome_signal, new_user.email, new_user.name)
    return {"status": "success"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Normalize input for search
    login_id = form_data.username.strip()
    print(f"DEBUG: Login attempt for {login_id}")

    # 1. SEARCH BOTH TABLES
    user = db.query(UserModel).filter(
        or_(UserModel.username.ilike(login_id), UserModel.email.ilike(login_id))
    ).first()

    admin = db.query(AdminModel).filter(
        or_(AdminModel.username.ilike(login_id), AdminModel.email.ilike(login_id))
    ).first()

    target = user or admin

    if not target:
        print(f"DEBUG: Account not found: {login_id}")
        logger.warning(f"Login failed: No account found for {login_id}")
        raise HTTPException(status_code=401, detail="Account not found. Please register first.")

    # 2. VERIFY PASSWORD
    if not verify_password(form_data.password, target.password_hash):
        print(f"DEBUG: Password mismatch for {login_id}")
        logger.warning(f"Login failed: Password mismatch for {login_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 3. OTP FLOW
    otp_code = str(random.randint(100000, 999999))
    expires = datetime.utcnow() + timedelta(minutes=10)
    db.add(OTPModel(email=target.email, otp_code=otp_code, purpose="login", expires_at=expires))
    db.commit()

    print(f"DEBUG: Login handshake successful for {target.username}. Sending OTP to {target.email}")
    logger.info(f"Login handshake successful for {target.username}. OTP sent to {target.email}")

    # Non-blocking fire-and-forget for the mail signal
    asyncio.create_task(send_verification_signal(target.email, otp_code, "login"))

    return {"status": "otp_required", "email": target.email}

@router.post("/verify-login")
async def verify_login(data: dict, db: Session = Depends(get_db)):
    otp_record = db.query(OTPModel).filter(
        OTPModel.email == data.get("email"),
        OTPModel.otp_code == data.get("otp"),
        OTPModel.purpose == "login",
        OTPModel.expires_at > datetime.utcnow()
    ).first()
    if not otp_record: raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check both tables
    user = db.query(UserModel).filter(UserModel.email == data.get("email")).first()
    admin = db.query(AdminModel).filter(AdminModel.email == data.get("email")).first()

    target = user or admin
    if not target:
        raise HTTPException(status_code=404, detail="Account vanished during handshake")

    scope = "admin" if admin else "user"
    access = create_access_token(data={"sub": target.username}, scope=scope)

    if user:
        session = UserSessionModel(
            user_id=user.id,
            jwt_token=access,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db.add(session)
    else:
        session = AdminSessionModel(
            admin_id=admin.id,
            jwt_token=access,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        db.add(session)

    db.delete(otp_record)
    db.commit()

    logger.info(f"Identity verified for: {target.username} (Role: {scope})")
    return {"access_token": access, "token_type": "bearer", "role": scope}

@router.post("/reset-password")
async def reset_password(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")

    otp_record = db.query(OTPModel).filter(
        OTPModel.email == email,
        OTPModel.otp_code == otp,
        OTPModel.purpose == "forgot_password",
        OTPModel.expires_at > datetime.utcnow()
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired recovery code")

    # Try to find in User table first
    account = db.query(UserModel).filter(UserModel.email == email).first()
    if not account:
        # Check Admin table
        account = db.query(AdminModel).filter(AdminModel.email == email).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found in system")

    account.password_hash = get_password_hash(new_password)
    db.delete(otp_record)
    db.commit()

    logger.info(f"Password reset successful for: {email} ({'Admin' if isinstance(account, AdminModel) else 'User'})")
    return {"status": "success", "message": "Password updated successfully."}

@router.post("/verify-otp")
async def verify_otp(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    otp = data.get("otp")
    purpose = data.get("purpose")

    otp_record = db.query(OTPModel).filter(
        OTPModel.email == email,
        OTPModel.otp_code == otp,
        OTPModel.purpose == purpose,
        OTPModel.expires_at > datetime.utcnow()
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    return {"status": "success", "message": "Code verified."}

@router.get("/me")
async def read_users_me(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    # Defensive data aggregation to prevent 500 errors during migration gaps
    onboarding_data = {"completed": False}
    try:
        # We query explicitly to avoid relationship load failures if columns are missing
        from database_layer.db_manager import OnboardingProfileModel
        profile = db.query(OnboardingProfileModel).filter(OnboardingProfileModel.user_id == current_user.id).first()
        if profile:
            onboarding_data = {
                "completed": bool(getattr(profile, 'completed', False)),
                "preferred_name": getattr(profile, 'preferred_name', None),
                "purpose": getattr(profile, 'purpose', None),
                "experience_level": getattr(profile, 'experience_level', None),
                "accessibility_needs": getattr(profile, 'accessibility_needs', None) or getattr(profile, 'accessibility_preferences', {}).get('needs')
            }
    except Exception as e:
        logger.error(f"Handshake Resilience: Onboarding query failed: {e}")

    # Ensure critical identifiers are stringified for JSON safety
    try:
        user_id_str = str(current_user.id)

        # Robust datetime handling
        created_at = getattr(current_user, 'created_at', None)
        if hasattr(created_at, 'isoformat'):
            created_at_str = created_at.isoformat()
        else:
            created_at_str = str(created_at) if created_at else None

        # Robust preferences handling
        prefs = getattr(current_user, 'preferences', {})
        if isinstance(prefs, str):
            try:
                import json
                prefs = json.loads(prefs)
            except:
                prefs = {}

        return {
            "id": user_id_str,
            "username": getattr(current_user, 'username', 'unknown'),
            "email": getattr(current_user, 'email', 'unknown'),
            "name": getattr(current_user, 'name', None),
            "role": getattr(current_user, 'role', 'user'),
            "bio": getattr(current_user, 'bio', None),
            "phone": getattr(current_user, 'phone', None),
            "avatar_url": getattr(current_user, 'avatar_url', None),
            "banner_url": getattr(current_user, 'banner_url', None),
            "preferences": prefs or {},
            "created_at": created_at_str,
            "onboarding": onboarding_data
        }
    except Exception as e:
        logger.critical(f"FATAL Identity Sync Failure: {e}")
        # Return a controlled error instead of crashing if possible
        return {
            "id": str(getattr(current_user, 'id', 'unknown')),
            "username": getattr(current_user, 'username', 'unknown'),
            "error": "Neural synchronization partial failure",
            "onboarding": {"completed": False}
        }

@router.put("/me")
async def update_user_me(data: dict, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        if "name" in data:
            current_user.name = data["name"]

        if "email" in data and data["email"] != current_user.email:
            # Check for collision
            existing = db.query(UserModel).filter(UserModel.email == data["email"]).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email address is already in use by another node.")
            current_user.email = data["email"]

        if "bio" in data:
            current_user.bio = data["bio"]
        if "phone" in data:
            current_user.phone = data["phone"]
        if "preferences" in data:
            # Merge preferences instead of overwrite if possible
            if isinstance(current_user.preferences, dict) and isinstance(data["preferences"], dict):
                current_user.preferences = {**current_user.preferences, **data["preferences"]}
            else:
                current_user.preferences = data["preferences"]

        db.commit()
        logger.info(f"Neural profile synchronized for: {current_user.username}")
        return {"status": "success", "message": "Profile updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update profile for {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal Neural Core failure during synchronization")

@router.delete("/me")
async def delete_user_me(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.is_deleted = True
    current_user.is_active = False
    db.commit()
    return {"status": "success"}
