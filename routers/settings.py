"""User Settings API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user)]
)

@router.get("", response_model=UserSettings)
async def get_settings(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get current user's settings."""
    return await get_or_create_user_settings(db_session, current_user.id)

@router.put("", response_model=UserSettings)
async def update_settings(
    settings: UserSettingsBase,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update current user's settings."""
    settings_dict = settings.model_dump(exclude_unset=True)
    return await update_user_settings(db_session, current_user.id, settings_dict)

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
    
    return {"message": "Profile updated successfully"}

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
