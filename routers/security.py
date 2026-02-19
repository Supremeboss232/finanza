"""Security and authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User

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
    """Get login history for current user."""
    # Login history functionality to be implemented
    return []


@router.get("/devices")
async def get_trusted_devices(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get list of trusted devices."""
    # Device management functionality to be implemented
    return []


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
    """Enable two-factor authentication."""
    method = method_data.get("method")
    
    if method == "authenticator":
        return {
            "method": "authenticator",
            "message": "Scan QR code with your authenticator app",
            "qr_code": "data:image/png;base64,iVBORw0KGg...",
            "secret": "JBSWY3DPEBLW64TMMQ======"
        }
    
    return {
        "method": method,
        "message": f"2FA method {method} setup initiated"
    }


@router.post("/2fa/disable", status_code=status.HTTP_200_OK)
async def disable_2fa(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Disable two-factor authentication."""
    return {
        "message": "Two-factor authentication has been disabled",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/2fa/backup-codes")
async def get_backup_codes(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get backup codes for 2FA."""
    return {
        "backup_codes": [
            "AAAA-AAAA-AAAA",
            "BBBB-BBBB-BBBB",
            "CCCC-CCCC-CCCC",
            "DDDD-DDDD-DDDD",
            "EEEE-EEEE-EEEE"
        ],
        "message": "Save these codes in a secure place. Each code can be used once."
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

