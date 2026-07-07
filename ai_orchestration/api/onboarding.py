from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
from ai_orchestration.api.deps import get_db, get_current_user
from database_layer.db_manager import OnboardingProfileModel, UserModel

router = APIRouter(tags=["Onboarding"])

@router.get("/status")
async def get_onboarding_status(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(OnboardingProfileModel).filter(OnboardingProfileModel.user_id == current_user.id).first()
    if not profile:
        return {"completed": False, "last_step": 0, "data": {}}

    return {
        "completed": profile.completed,
        "last_step": profile.last_step,
        "data": {
            "preferred_name": profile.preferred_name,
            "country": profile.country,
            "preferred_language": profile.preferred_language,
            "experience_level": profile.experience_level,
            "purpose": profile.purpose,
            "primary_goal": profile.primary_goal,
            "usage_style": profile.usage_style,
            "interests": profile.interests,
            "workspace_preference": profile.workspace_preference,
            "recognition_preference": profile.recognition_preference,
            "accessibility_needs": profile.accessibility_needs,
            "learning_goals": profile.learning_goals
        }
    }

@router.post("")
async def submit_onboarding(data: dict, db: Session = Depends(get_db), current_user: UserModel = Depends(get_current_user)):
    profile = db.query(OnboardingProfileModel).filter(OnboardingProfileModel.user_id == current_user.id).first()
    if not profile:
        profile = OnboardingProfileModel(user_id=current_user.id, email=current_user.email)
        db.add(profile)

    # Permanent association linked to authenticated user ID/Email
    if "preferred_name" in data: profile.preferred_name = data.get("preferred_name")
    if "country" in data: profile.country = data.get("country")
    if "preferred_language" in data: profile.preferred_language = data.get("preferred_language")
    if "experience_level" in data: profile.experience_level = data.get("experience_level")
    if "purpose" in data: profile.purpose = data.get("purpose")
    if "primary_goal" in data: profile.primary_goal = data.get("primary_goal")
    if "usage_style" in data: profile.usage_style = data.get("usage_style")
    if "interests" in data: profile.interests = data.get("interests")
    if "workspace_preference" in data: profile.workspace_preference = data.get("workspace_preference")
    if "recognition_preference" in data: profile.recognition_preference = data.get("recognition_preference")

    if "last_step" in data: profile.last_step = data.get("last_step")

    # Handle both naming conventions for resilience
    if "accessibility_needs" in data:
        profile.accessibility_needs = data.get("accessibility_needs")
        profile.accessibility_preferences = {"needs": data.get("accessibility_needs")}
    if "accessibility_preferences" in data:
        profile.accessibility_preferences = data.get("accessibility_preferences")

    if "learning_goals" in data: profile.learning_goals = data.get("learning_goals")

    if data.get("completed") is True:
        profile.completed = True
        profile.completed_at = datetime.datetime.utcnow()

    profile.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"status": "success", "message": "Onboarding personalized.", "last_step": profile.last_step}
