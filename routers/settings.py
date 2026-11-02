"""User & Admin Settings API endpoints."""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User
from crud import (
    get_or_create_user_settings,
    update_user_settings,
    update_user,
)
from schemas import (
    UserSettings,
    UserSettingsBase,
    UserUpdate,
)
from admin_settings_service import AdminSettingsService

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)]
)


def _normalize_user_settings(s: Any) -> Any:
    if getattr(s, "created_at", None) is None:
        s.created_at = datetime.utcnow()
    if getattr(s, "updated_at", None) is None:
        s.updated_at = s.created_at or datetime.utcnow()
    return s


@router.get("")
async def get_settings(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get current user's settings merged with system settings for admin portal compatibility."""
    user_settings = await get_or_create_user_settings(db_session, current_user.id)
    user_settings = _normalize_user_settings(user_settings)
    sys_settings = await AdminSettingsService.get_all_settings(db_session)
    return {
        "id": user_settings.id,
        "user_id": user_settings.user_id,
        "two_factor_enabled": bool(user_settings.two_factor_enabled),
        "email_notifications": bool(user_settings.email_notifications),
        "sms_notifications": bool(user_settings.sms_notifications),
        "phone_number": user_settings.phone_number,
        "address": user_settings.address,
        "preferences": user_settings.preferences,
        "created_at": user_settings.created_at.isoformat(),
        "updated_at": user_settings.updated_at.isoformat(),
        "success": True,
        **sys_settings,
    }


@router.put("")
@router.post("")
async def update_settings(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    payload: Dict[str, Any] = Body(default={}),
):
    """Update current user's settings and/or system settings."""
    user_fields = {"two_factor_enabled", "email_notifications", "sms_notifications", "phone_number", "address", "preferences"}
    user_updates = {k: v for k, v in payload.items() if k in user_fields}
    if user_updates:
        user_settings = await update_user_settings(db_session, current_user.id, user_updates)
    else:
        user_settings = await get_or_create_user_settings(db_session, current_user.id)
    user_settings = _normalize_user_settings(user_settings)

    if getattr(current_user, "is_admin", False) and payload:
        await AdminSettingsService.update_settings(db_session, current_user.id, payload)

    sys_settings = await AdminSettingsService.get_all_settings(db_session)
    return {
        "id": user_settings.id,
        "user_id": user_settings.user_id,
        "two_factor_enabled": bool(user_settings.two_factor_enabled),
        "email_notifications": bool(user_settings.email_notifications),
        "sms_notifications": bool(user_settings.sms_notifications),
        "phone_number": user_settings.phone_number,
        "address": user_settings.address,
        "preferences": user_settings.preferences,
        "created_at": user_settings.created_at.isoformat(),
        "updated_at": user_settings.updated_at.isoformat(),
        "success": True,
        "message": "Settings updated successfully",
        **sys_settings,
    }


@router.get("/maintenance-mode")
@router.post("/maintenance-mode")
async def settings_maintenance_mode(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    payload: Dict[str, Any] = Body(default={}),
):
    """Get or toggle maintenance mode."""
    enabled = payload.get("enabled", False)
    message = payload.get("message", "")
    if payload:
        await AdminSettingsService.update_maintenance_mode(db_session, current_user.id, enabled, message)
    else:
        enabled = await AdminSettingsService.get_setting(db_session, "maintenance_mode", False)
        message = await AdminSettingsService.get_setting(db_session, "maintenance_message", "")
    return {
        "success": True,
        "enabled": enabled,
        "maintenance_mode": enabled,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.put("/profile", response_model=dict)
async def update_profile(
    profile_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update user profile (full_name, email, etc.)."""
    allowed_fields = ["full_name"]
    filtered_data = {k: v for k, v in profile_data.items() if k in allowed_fields}
    
    if not filtered_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    user_update = UserUpdate(**filtered_data, password=None)
    await update_user(db_session, current_user.id, user_update)
    
    return {"message": "Profile updated successfully", "success": True}


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    password_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Change user password."""
    old_password = password_data.get("old_password")
    new_password = password_data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both old_password and new_password are required"
        )
    
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    from auth_utils import verify_password, get_password_hash
    
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old password is incorrect"
        )
    
    user_update = UserUpdate(password=new_password)
    user_update.hashed_password = get_password_hash(new_password)
    await update_user(db_session, current_user.id, user_update)


@router.put("/2fa/{action}", status_code=status.HTTP_204_NO_CONTENT)
async def toggle_two_factor_auth(
    action: str,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable two-factor authentication."""
    if action not in ["enable", "disable"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'enable' or 'disable'"
        )
    
    settings_data = {"two_factor_enabled": action == "enable"}
    await update_user_settings(db_session, current_user.id, settings_data)
