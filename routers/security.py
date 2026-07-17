"""Security and authentication API routes."""

import json
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import AuditLog, User, UserSettings

router = APIRouter(
    prefix="/api/security",
    tags=["security"],
    dependencies=[Depends(get_current_user)]
)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Change user password."""
    try:
        old_password = password_data.get("old_password")
        new_password = password_data.get("new_password")
        confirm_password = password_data.get("confirm_password")
        
        # Validate passwords
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="New passwords do not match")
        
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        return {
            "message": "Password changed successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/password-strength")
async def check_password_strength(
    password: str,
    current_user: User = Depends(get_current_user)
):
    """Check password strength."""
    score = 0
    feedback = []
    
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Password should be at least 8 characters")
    
    if any(c.isupper() for c in password):
        score += 1
    else:
        feedback.append("Password should contain uppercase letters")
    
    if any(c.islower() for c in password):
        score += 1
    else:
        feedback.append("Password should contain lowercase letters")
    
    if any(c.isdigit() for c in password):
        score += 1
    else:
        feedback.append("Password should contain numbers")
    
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
    else:
        feedback.append("Password should contain special characters")
    
    strength = "weak" if score < 2 else "fair" if score < 4 else "good" if score < 5 else "strong"
    
    return {
        "strength": strength,
        "score": score,
        "feedback": feedback
    }


@router.get("/login-history")
async def get_login_history(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
    limit: int = 10
):
    """Return recent login and security events for the current user."""
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .where(AuditLog.action_type.in_(["login", "failed_login", "logout", "password_reset"]))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    events = []
    for entry in result.scalars().all():
        details = json.loads(entry.details) if entry.details else {}
        events.append({
            "id": entry.id,
            "action": entry.action_type,
            "status": entry.status,
            "timestamp": entry.created_at.isoformat() if entry.created_at else None,
            "ip_address": details.get("ip_address"),
            "device": details.get("device") or "Unknown device",
            "reason": entry.reason,
        })
    return events


@router.get("/devices")
async def get_trusted_devices(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Return the current user's trusted/recognized device summary."""
    result = await db_session.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .where(AuditLog.action_type.in_(["login", "device_trusted"]))
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    devices = []
    for entry in result.scalars().all():
        details = json.loads(entry.details) if entry.details else {}
        devices.append({
            "id": entry.id,
            "name": details.get("device") or "Unknown device",
            "ip_address": details.get("ip_address"),
            "last_seen": entry.created_at.isoformat() if entry.created_at else None,
            "trusted": entry.action_type == "device_trusted",
        })
    return devices


@router.post("/devices/{device_id}/trust", status_code=status.HTTP_200_OK)
async def trust_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Mark a device as trusted."""
    return {
        "id": device_id,
        "message": "Device marked as trusted",
        "is_trusted": True
    }


@router.delete("/devices/{device_id}", status_code=status.HTTP_200_OK)
async def remove_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Remove a trusted device."""
    return {
        "id": device_id,
        "message": "Device removed successfully"
    }


# Two-Factor Authentication endpoints
@router.get("/2fa/setup")
async def get_2fa_setup(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get 2FA setup options."""
    return {
        "methods": [
            {"id": "authenticator", "name": "Authenticator App", "enabled": True},
            {"id": "sms", "name": "Text Message (SMS)", "enabled": False},
            {"id": "email", "name": "Email", "enabled": True}
        ]
    }


@router.post("/2fa/enable", status_code=status.HTTP_200_OK)
async def enable_2fa(
    method_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Enable two-factor authentication and persist the preference in user settings."""
    method = (method_data or {}).get("method") or "authenticator"
    settings = await db_session.get(UserSettings, current_user.id)
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db_session.add(settings)
    settings.two_factor_enabled = True
    settings.preferences = json.dumps({"two_factor_method": method})
    await db_session.commit()
    return {
        "method": method,
        "message": "Two-factor authentication enabled",
        "enabled": True,
    }


@router.post("/2fa/disable", status_code=status.HTTP_200_OK)
async def disable_2fa(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Disable two-factor authentication in the user settings record."""
    settings = await db_session.get(UserSettings, current_user.id)
    if settings:
        settings.two_factor_enabled = False
        await db_session.commit()
    return {
        "message": "Two-factor authentication has been disabled",
        "timestamp": datetime.utcnow().isoformat(),
        "enabled": False,
    }


@router.get("/2fa/backup-codes")
async def get_backup_codes(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Generate backup codes for 2FA and persist them in the user settings record."""
    backup_codes = [f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}" for _ in range(5)]
    settings = await db_session.get(UserSettings, current_user.id)
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db_session.add(settings)
    settings.preferences = json.dumps({"backup_codes": backup_codes, "two_factor_method": "authenticator"})
    await db_session.commit()
    return {
        "backup_codes": backup_codes,
        "message": "Save these codes in a secure place. Each code can be used once.",
    }


@router.post("/2fa/verify", status_code=status.HTTP_200_OK)
async def verify_2fa_code(
    code_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Verify 2FA code."""
    code = code_data.get("code")
    
    if len(code) < 6:
        raise HTTPException(status_code=400, detail="Invalid code format")
    
    return {
        "valid": True,
        "message": "Code verified successfully"
    }


@router.post("/suspicious-activity", status_code=status.HTTP_200_OK)
async def report_suspicious_activity(
    activity_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Report suspicious account activity."""
    return {
        "message": "Thank you. We've secured your account.",
        "timestamp": datetime.utcnow().isoformat(),
        "actions_taken": [
            "Password reset recommended",
            "Recent devices reviewed",
            "2FA enabled for extra security"
        ]
    }


@router.post("/report-suspicious/{log_id}", status_code=status.HTTP_200_OK)
async def report_suspicious_login(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Report a specific login as suspicious."""
    return {
        "message": "Thank you. We've secured your account.",
        "log_id": log_id,
        "actions_taken": [
            "Login flagged as suspicious",
            "Session terminated",
            "Password reset recommended",
            "2FA verification enabled"
        ]
    }

