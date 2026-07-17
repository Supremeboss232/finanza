"""
Production-Ready Admin Settings API Endpoints
Exposes all settings management functionality with RBAC and audit logging.
"""

import logging
from typing import Dict, Optional, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_admin_user, SessionDep, CurrentAdminUserDep
from admin_settings_service import AdminSettingsService, RBACValidator
from models import User

log = logging.getLogger(__name__)

admin_settings_router = APIRouter(
    prefix="/api/v1/admin/settings",
    tags=["admin-settings"],
    dependencies=[Depends(get_current_admin_user)]
)

config_router = APIRouter(
    prefix="/api/v1/config",
    tags=["public-config"]
)


# ============================================================================
# SETTINGS MANAGEMENT ENDPOINTS
# ============================================================================

@admin_settings_router.get("", response_model=Dict[str, Any])
async def get_all_settings(
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Retrieve all system settings.
    Requires: settings:read permission
    """
    if not RBACValidator.has_permission(current_user.role, 'settings:read'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    settings = await AdminSettingsService.get_all_settings(db_session)
    
    # Mask sensitive fields
    for key in AdminSettingsService.SENSITIVE_FIELDS:
        if key in settings:
            settings[key] = "••••••••••••••••"

    return settings


@admin_settings_router.post("", response_model=Dict[str, Any])
async def update_settings(
    payload: Dict[str, Any],
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Update multiple system settings.
    Requires: settings:write permission
    
    Request body example:
    {
        "platform_name": "Finanza",
        "maintenance_mode": false,
        "allow_signups": true
    }
    """
    if not RBACValidator.has_permission(current_user.role, 'settings:write'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    try:
        updated = await AdminSettingsService.update_settings(
            db_session,
            current_user.id,
            payload,
            client_ip
        )
        return {
            "success": True,
            "updated_settings": updated,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Settings update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )


@admin_settings_router.get("/{setting_key}", response_model=Any)
async def get_setting(
    setting_key: str,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Get a single setting value.
    """
    if not RBACValidator.has_permission(current_user.role, 'settings:read'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    value = await AdminSettingsService.get_setting(db_session, setting_key)
    
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{setting_key}' not found"
        )

    # Mask sensitive fields
    if setting_key in AdminSettingsService.SENSITIVE_FIELDS:
        return {"value": "••••••••••••••••"}

    return {"key": setting_key, "value": value}


# ============================================================================
# MAINTENANCE & OPERATIONS
# ============================================================================

@admin_settings_router.post("/maintenance-mode")
async def toggle_maintenance_mode(
    payload: Dict[str, Any],
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Enable/disable maintenance mode globally.
    Takes effect immediately across all portals.
    Requires: settings:write permission
    
    Request body:
    {
        "enabled": true,
        "message": "System under maintenance. ETA: 2 hours"
    }
    """
    if not RBACValidator.has_permission(current_user.role, 'settings:write'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    client_ip = request.client.host if request.client else "unknown"

    try:
        result = await AdminSettingsService.update_maintenance_mode(
            db_session,
            current_user.id,
            payload.get('enabled', False),
            payload.get('message'),
            client_ip
        )
        return {
            "success": True,
            "maintenance_mode": payload.get('enabled', False),
            "message": payload.get('message'),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log.error(f"Maintenance mode toggle error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle maintenance mode"
        )


# ============================================================================
# API KEY & SECRET MANAGEMENT
# ============================================================================

@admin_settings_router.post("/rotate-api-keys")
async def rotate_api_keys(
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Rotate API keys and webhook secrets.
    Invalidates all old keys.
    Requires: settings:api_management permission
    
    WARNING: This operation will break all integrations using old keys.
    """
    if not RBACValidator.has_permission(current_user.role, 'settings:api_management'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Management permission denied"
        )

    client_ip = request.client.host if request.client else "unknown"

    try:
        new_keys = await AdminSettingsService.rotate_api_keys(
            db_session,
            current_user.id,
            client_ip
        )
        return {
            "success": True,
            "api_key": new_keys['api_key'],
            "webhook_secret": new_keys['webhook_secret'],
            "expires_in_seconds": new_keys['expires_in_seconds'],
            "warning": "Keys visible for 60 seconds. Save them securely."
        }
    except Exception as e:
        log.error(f"API key rotation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API keys"
        )


# ============================================================================
# BACKUP MANAGEMENT
# ============================================================================

@admin_settings_router.post("/backup")
async def trigger_manual_backup(
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
    background_tasks: BackgroundTasks,
):
    """
    Trigger asynchronous database backup.
    Returns task ID for polling backup status.
    Requires: backup:manage permission
    """
    if not RBACValidator.has_permission(current_user.role, 'backup:manage'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backup management permission denied"
        )

    client_ip = request.client.host if request.client else "unknown"

    try:
        result = await AdminSettingsService.trigger_backup(
            db_session,
            current_user.id,
            client_ip,
            background_tasks
        )
        return {
            "success": True,
            "task_id": result['task_id'],
            "status": "queued",
            "poll_url": f"/api/v1/admin/settings/backup/{result['task_id']}"
        }
    except Exception as e:
        log.error(f"Backup trigger error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger backup"
        )


@admin_settings_router.get("/backup/{task_id}")
async def get_backup_status(
    task_id: str,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Poll backup task status and progress.
    Use for monitoring asynchronous backup.
    """
    if not RBACValidator.has_permission(current_user.role, 'backup:manage'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    try:
        status_info = await AdminSettingsService.get_backup_status(db_session, task_id)
        return status_info
    except Exception as e:
        log.error(f"Backup status error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get backup status"
        )


@admin_settings_router.get("/backup/status")
async def get_last_backup_info(
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
):
    """
    Get information about last completed backup.
    """
    if not RBACValidator.has_permission(current_user.role, 'backup:manage'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    try:
        from models import BackupTask
        from sqlalchemy import select, desc

        result = await db_session.execute(
            select(BackupTask)
            .where(BackupTask.status == 'completed')
            .order_by(desc(BackupTask.completed_at))
            .limit(1)
        )
        last_backup = result.scalar_one_or_none()

        if not last_backup:
            return {
                "last_backup_time": None,
                "backup_file_size": None
            }

        import os
        file_size = None
        if last_backup.backup_file_path and os.path.exists(last_backup.backup_file_path):
            file_size = os.path.getsize(last_backup.backup_file_path)

        return {
            "last_backup_time": last_backup.completed_at.isoformat() if last_backup.completed_at else None,
            "backup_file_size": file_size
        }
    except Exception as e:
        log.error(f"Backup info error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get backup info"
        )


# ============================================================================
# AUDIT LOGS
# ============================================================================

@admin_settings_router.get("/audit-logs")
async def get_audit_logs(
    db_session: SessionDep,
    current_user: CurrentAdminUserDep,
    limit: int = 50,
    offset: int = 0,
):
    """
    Retrieve audit logs of all settings changes.
    Required for compliance and security review.
    Requires: audit:read permission
    """
    if not RBACValidator.has_permission(current_user.role, 'audit:read'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access denied"
        )

    try:
        logs = await AdminSettingsService.get_audit_logs(
            db_session,
            limit=limit,
            offset=offset
        )
        return logs
    except Exception as e:
        log.error(f"Audit logs error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


# ============================================================================
# ADMIN INFO & VERIFICATION
# ============================================================================

@admin_settings_router.get("/me")
async def get_current_admin_info(
    current_user: CurrentAdminUserDep,
    db_session: SessionDep,
):
    """
    Get current admin user info and permissions.
    Used by frontend for RBAC checks.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": getattr(current_user, 'role', 'admin'),
        "is_superadmin": getattr(current_user, 'is_superadmin', False),
        "scopes": RBACValidator.PERMISSIONS.get(getattr(current_user, 'role', 'admin'), []),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }


# ============================================================================
# PUBLIC CONFIG ENDPOINTS (NO AUTH REQUIRED)
# ============================================================================

@config_router.get("", response_model=Dict[str, Any])
async def get_public_config(db_session: SessionDep):
    """
    Get public system configuration.
    Used by user portal for UI state (signups enabled, maintenance mode, etc).
    NO AUTHENTICATION REQUIRED.
    """
    try:
        all_settings = await AdminSettingsService.get_all_settings(db_session)
        
        # Return only public settings
        public_config = {
            "maintenance_mode": all_settings.get('maintenance_mode', False),
            "maintenance_message": all_settings.get('maintenance_message', ''),
            "allow_signups": all_settings.get('allow_signups', True),
            "min_deposit_amount": all_settings.get('min_deposit_amount', 10),
            "max_withdrawal_amount": all_settings.get('max_withdrawal_amount', 100000),
            "enable_deposits": all_settings.get('enable_deposits', True),
            "enable_withdrawals": all_settings.get('enable_withdrawals', True),
            "require_kyc_deposits": all_settings.get('require_kyc_deposits', True),
            "require_kyc_transfers": all_settings.get('require_kyc_transfers', True),
        }
        return public_config
    except Exception as e:
        log.error(f"Public config error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve configuration"
        )


@config_router.get("/allow-signups")
async def get_signup_status(db_session: SessionDep):
    """Check if new signups are allowed."""
    allow_signups = await AdminSettingsService.get_setting(
        db_session, 'allow_signups', True
    )
    return {"allow_signups": allow_signups}


@config_router.get("/maintenance-mode")
async def get_maintenance_status(db_session: SessionDep):
    """Check maintenance mode status."""
    enabled = await AdminSettingsService.get_setting(
        db_session, 'maintenance_mode', False
    )
    message = await AdminSettingsService.get_setting(
        db_session, 'maintenance_message', ''
    )
    return {
        "enabled": enabled,
        "message": message
    }


from datetime import datetime
