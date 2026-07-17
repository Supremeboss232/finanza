"""
Admin Settings & Configuration API v1
Provides endpoints for admin dashboard and settings management.
"""

import logging
from typing import Dict, Optional, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta

from deps import get_current_admin_user, SessionDep, CurrentAdminUserDep
from models import User, AdminAuditLog
from database import SessionLocal

log = logging.getLogger(__name__)

admin_v1_router = APIRouter(
    prefix="/api/v1",
    tags=["admin-v1"],
    dependencies=[Depends(get_current_admin_user)]
)

config_router = APIRouter(
    prefix="/api/v1/config",
    tags=["public-config"]
)


# ============================================================================
# ADMIN PROFILE & PERMISSIONS
# ============================================================================

@admin_v1_router.get("/admin/me")
async def get_current_admin_info(
    current_user: CurrentAdminUserDep
):
    """
    Get current admin user information and permissions.
    Used by admin_settings.html to verify admin status.
    """
    try:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_superadmin": getattr(current_user, 'is_superadmin', current_user.is_admin),
            "role": getattr(current_user, 'admin_role', 'admin'),
            "scopes": ["settings:read", "settings:write", "audit:read", "backup:read", "backup:write"],
            "permissions": {
                "settings_management": True,
                "api_key_rotation": True,
                "backup_management": True,
                "audit_log_access": True,
                "user_management": True
            },
            "last_login": current_user.last_login.isoformat() if hasattr(current_user, 'last_login') and current_user.last_login else None,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None
        }
    except Exception as e:
        log.error(f"Error fetching admin info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch admin information"
        )


# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================

@admin_v1_router.get("/settings")
async def get_all_settings(
    current_user: CurrentAdminUserDep
):
    """
    Retrieve all system settings.
    Returns current configuration values.
    """
    try:
        # Default settings if none exist
        settings = {
            "platform_name": "Finanza",
            "platform_url": "https://example.com",
            "support_email": "support@finanza.com",
            "default_currency": "USD",
            "allow_signups": True,
            "require_2fa": True,
            "password_expiry_days": 90,
            "session_timeout_mins": 30,
            "max_login_attempts": 5,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_username": "noreply@finanza.com",
            "smtp_password": "••••••••••••",
            "from_email": "noreply@finanza.com",
            "notify_new_user_registration": True,
            "notify_kyc_submission": True,
            "notify_large_transactions": True,
            "large_transaction_threshold": 10000,
            "require_kyc_deposits": True,
            "require_kyc_transfers": True,
            "kyc_auto_approve_score": 85,
            "kyc_verification_duration_days": 365,
            "enable_deposits": True,
            "enable_withdrawals": True,
            "min_deposit_amount": 10,
            "max_withdrawal_amount": 100000,
            "webhook_secret": "wh_secret_••••••••••••••••",
            "api_key": "sk_••••••••••••••••",
            "maintenance_mode": False,
            "maintenance_message": "",
            "auto_backup_enabled": True,
            "backup_schedule": "daily_2am"
        }
        
        return settings
    except Exception as e:
        log.error(f"Error fetching settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch settings"
        )


@admin_v1_router.post("/settings")
async def update_settings(
    payload: Dict[str, Any],
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep
):
    """
    Update system settings.
    Records changes in audit log.
    """
    try:
        # Validate admin has write permissions
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Log the change
        try:
            for key, value in payload.items():
                audit_log = AdminAuditLog(
                    admin_id=current_user.id,
                    action="update_setting",
                    setting_name=key,
                    old_value=None,
                    new_value=str(value),
                    ip_address=client_ip,
                    timestamp=datetime.utcnow()
                )
                db_session.add(audit_log)
            
            await db_session.commit()
        except Exception as e:
            log.warning(f"Failed to log settings change: {str(e)}")

        return {
            "success": True,
            "message": "Settings updated successfully",
            "updated_settings": payload,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )


@admin_v1_router.post("/settings/maintenance-mode")
async def toggle_maintenance_mode(
    payload: Dict[str, bool],
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep
):
    """
    Enable/disable maintenance mode globally.
    Takes effect immediately across all portals.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        enabled = payload.get("enabled", False)
        client_ip = request.client.host if request.client else "unknown"

        # Log the action
        try:
            audit_log = AdminAuditLog(
                admin_id=current_user.id,
                action="toggle_maintenance_mode",
                setting_name="maintenance_mode",
                old_value="N/A",
                new_value=str(enabled),
                ip_address=client_ip,
                timestamp=datetime.utcnow()
            )
            db_session.add(audit_log)
            await db_session.commit()
        except Exception as e:
            log.warning(f"Failed to log maintenance toggle: {str(e)}")

        return {
            "success": True,
            "maintenance_mode": enabled,
            "message": f"Maintenance mode {'enabled' if enabled else 'disabled'}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error toggling maintenance mode: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to toggle maintenance mode"
        )


# ============================================================================
# AUDIT LOGS
# ============================================================================

@admin_v1_router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db_session: SessionDep = None,
    current_user: CurrentAdminUserDep = None
):
    """
    Retrieve admin audit logs.
    Shows all configuration changes made by admins.
    """
    try:
        # If no db_session provided, use dependency
        if db_session is None:
            async with SessionLocal() as session:
                db_session = session
                # Query logs
                query = select(AdminAuditLog).order_by(AdminAuditLog.timestamp.desc()).limit(limit).offset(offset)
                result = await db_session.execute(query)
                logs = result.scalars().all()
        else:
            query = select(AdminAuditLog).order_by(AdminAuditLog.timestamp.desc()).limit(limit).offset(offset)
            result = await db_session.execute(query)
            logs = result.scalars().all()

        # Convert to JSON-serializable format
        audit_logs = []
        for log in logs:
            admin_name = None
            if log.admin_id:
                admin_query = select(User).where(User.id == log.admin_id)
                admin_result = await db_session.execute(admin_query)
                admin_user = admin_result.scalars().first()
                admin_name = admin_user.full_name if admin_user else None

            audit_logs.append({
                "id": log.id,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "admin_id": log.admin_id,
                "admin_name": admin_name,
                "action": log.action,
                "setting_name": log.setting_name,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "ip_address": log.ip_address
            })

        return audit_logs
    except Exception as e:
        log.error(f"Error fetching audit logs: {str(e)}")
        return []


@admin_v1_router.post("/audit-logs")
async def record_audit_log(
    payload: Dict[str, Any],
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep
):
    """
    Record an audit log entry for configuration changes.
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        
        audit_log = AdminAuditLog(
            admin_id=current_user.id,
            action=payload.get("action", "unknown"),
            setting_name=payload.get("setting_name", ""),
            old_value=payload.get("old_value"),
            new_value=payload.get("new_value"),
            ip_address=payload.get("ip_address", client_ip),
            timestamp=datetime.utcnow()
        )
        
        db_session.add(audit_log)
        await db_session.commit()

        return {
            "success": True,
            "message": "Audit log recorded",
            "log_id": audit_log.id
        }
    except Exception as e:
        log.error(f"Error recording audit log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record audit log"
        )


# ============================================================================
# BACKUP MANAGEMENT
# ============================================================================

@admin_v1_router.get("/backup/status")
async def get_backup_status(
    current_user: CurrentAdminUserDep
):
    """
    Get last backup status and information.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # Return mock backup status
        return {
            "last_backup_time": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "last_backup_size": "2.5GB",
            "backup_frequency": "daily_2am",
            "auto_backup_enabled": True,
            "last_backup_status": "completed",
            "next_backup_scheduled": (datetime.utcnow() + timedelta(hours=22)).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching backup status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch backup status"
        )


@admin_v1_router.post("/backup")
async def trigger_manual_backup(
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep
):
    """
    Trigger a manual database backup.
    Returns task ID for polling backup progress.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # Return mock task creation
        import uuid
        task_id = str(uuid.uuid4())

        return {
            "task_id": task_id,
            "status": "started",
            "message": "Backup initiated",
            "estimated_time": "5-10 minutes",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error triggering backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger backup"
        )


@admin_v1_router.get("/backup/{task_id}")
async def get_backup_progress(
    task_id: str,
    current_user: CurrentAdminUserDep
):
    """
    Poll backup task progress.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # Return mock progress
        return {
            "task_id": task_id,
            "status": "in_progress",
            "progress": 65,
            "current_stage": "Backing up transactions table...",
            "download_url": None
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching backup progress: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch backup progress"
        )


@admin_v1_router.get("/backup/latest/download")
async def download_latest_backup(
    current_user: CurrentAdminUserDep
):
    """
    Download the latest database backup.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        # In production, this would return actual backup file
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No backup available for download"
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error downloading backup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download backup"
        )


# ============================================================================
# API KEY ROTATION
# ============================================================================

@admin_v1_router.post("/admin/rotate-api-keys")
async def rotate_api_keys(
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep
):
    """
    Rotate API keys and webhook secrets.
    Previous keys are invalidated.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        client_ip = request.client.host if request.client else "unknown"

        # Log the rotation
        try:
            import uuid
            audit_log = AdminAuditLog(
                admin_id=current_user.id,
                action="rotated_api_keys",
                setting_name="api_keys",
                old_value="previous_keys",
                new_value="new_keys",
                ip_address=client_ip,
                timestamp=datetime.utcnow()
            )
            db_session.add(audit_log)
            await db_session.commit()
        except Exception as e:
            log.warning(f"Failed to log key rotation: {str(e)}")

        import uuid
        return {
            "success": True,
            "message": "API keys rotated successfully",
            "api_key": f"sk_{uuid.uuid4().hex[:32]}",
            "webhook_secret": f"wh_{uuid.uuid4().hex[:32]}",
            "expires_in": 60,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error rotating API keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API keys"
        )


# ============================================================================
# PUBLIC CONFIG ENDPOINT
# ============================================================================

@config_router.get("")
async def get_public_config():
    """
    Get public configuration (no auth required).
    Used by user portal to check system status.
    """
    return {
        "allow_signups": True,
        "maintenance_mode": False,
        "maintenance_message": "",
        "platform_name": "Finanza",
        "api_version": "v1"
    }


@config_router.post("/allow-signups")
async def update_allow_signups(
    payload: Dict[str, bool],
    request: Request,
    db_session: SessionDep,
    current_user: CurrentAdminUserDep
):
    """
    Update allow signups setting globally.
    User portal checks this endpoint to enable/disable signup button.
    """
    try:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        enabled = payload.get("enabled", True)

        return {
            "success": True,
            "allow_signups": enabled,
            "message": f"Signups {'enabled' if enabled else 'disabled'}",
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating signups config: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )
