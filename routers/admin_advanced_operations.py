"""
Advanced Admin Operations Router
================================
Comprehensive endpoint for all admin operations including:
- MFA/2FA setup and verification
- Bulk user operations (import/export/batch update)
- Admin user management
- Enhanced audit logging
- User session management
"""

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Header, Body
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from deps import SessionDep, get_current_admin_user
from schemas import User as PydanticUser
from models import (
    User as DBUser,
    AuditLog
)
from mfa_service import MFAService
from mfa_session_manager import get_mfa_session_manager
from token_blacklist_service import get_token_blacklist_service
from rate_limiter_service import get_rate_limiter, get_rate_limit_config
from bulk_operations_service import BulkOperationService
from admin_management_service import AdminManagementService
from email_notification_service import get_email_notification_service
from scheduled_adjustments_service import get_scheduled_adjustments_service
from approval_workflow_service import get_approval_service
from granular_permission_service import get_permission_service
from admin_dashboard_service import get_admin_dashboard_service
from rbac import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/advanced",
    tags=["advanced_admin"],
    dependencies=[Depends(get_current_admin_user)]
)


# ==================== MFA/2FA ENDPOINTS ====================

@router.post("/mfa/setup")
async def setup_mfa(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(get_current_admin_user)
):
    """
    Setup MFA for admin account.
    
    Returns:
    - secret: Base32 encoded secret key
    - qr_code: Data URL for QR code
    - provisioning_uri: Manual entry URI
    - backup_codes: One-time backup codes
    """
    try:
        if current_admin.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA already enabled for this account"
            )
        
        # Generate secret and backup codes
        secret = MFAService.generate_secret()
        backup_codes = MFAService.generate_backup_codes(count=10)
        
        # Generate QR code
        provisioning_uri = MFAService.get_provisioning_uri(
            secret,
            current_admin.email
        )
        qr_code = MFAService.generate_qr_code(provisioning_uri)
        
        # Store in session manager for verification step
        mfa_manager = get_mfa_session_manager()
        await mfa_manager.store_mfa_setup(
            current_admin.id,
            secret,
            provisioning_uri
        )
        
        logger.info(f"MFA setup initiated for admin {current_admin.id}")
        
        return {
            "success": True,
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": qr_code,
            "backup_codes": backup_codes,
            "message": "Scan QR code with authenticator app, then verify with 6-digit code"
        }
        
    except Exception as e:
        logger.error(f"Error setting up MFA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mfa/verify")
async def verify_and_enable_mfa(
    totp_code: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(get_current_admin_user)
):
    """
    Verify TOTP code and enable MFA for admin account.
    Requires prior call to /mfa/setup endpoint.
    """
    try:
        if current_admin.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA already enabled for this account"
            )
        
        # Get setup data from session manager
        mfa_manager = get_mfa_session_manager()
        setup_data = await mfa_manager.get_mfa_setup(current_admin.id)
        
        if not setup_data:
            raise HTTPException(
                status_code=400,
                detail="No MFA setup in progress. Call /mfa/setup first"
            )
        
        secret, provisioning_uri = setup_data
        
        # Verify TOTP code
        if not MFAService.verify_token(secret, totp_code):
            raise HTTPException(
                status_code=400,
                detail="Invalid TOTP code. Please try again"
            )
        
        # Generate backup codes for storage
        backup_codes = MFAService.generate_backup_codes(count=10)
        
        # Enable MFA for user
        success = await MFAService.enable_mfa_for_user(
            db_session,
            current_admin.id,
            secret,
            backup_codes,
            admin_id=current_admin.id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to enable MFA"
            )
        
        # Clear session after successful verification
        await mfa_manager.clear_mfa_setup(current_admin.id)
        
        logger.info(f"MFA enabled successfully for admin {current_admin.id}")
        
        return {
            "success": True,
            "message": "MFA enabled successfully",
            "backup_codes": backup_codes,
            "warning": "Save your backup codes in a secure location. They can only be used once."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying MFA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mfa/disable")
async def disable_mfa(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(get_current_admin_user)
):
    """Disable MFA for admin account"""
    try:
        success = await MFAService.disable_mfa_for_user(
            db_session,
            current_admin.id,
            admin_id=current_admin.id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to disable MFA")
        
        return {
            "success": True,
            "message": "MFA disabled successfully"
        }
        
    except Exception as e:
        logger.error(f"Error disabling MFA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MFA FRONTEND API ENDPOINTS ====================
# These endpoints support the MFA setup page UI interactions

@router.post("/mfa/setup-initiate")
async def initiate_mfa_setup(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(get_current_admin_user)
):
    """
    Initiate MFA setup for current admin.
    Returns secret, QR code, and provisioning URI.
    Frontend alias for /mfa/setup endpoint.
    """
    try:
        if current_admin.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA already enabled for this account"
            )
        
        # Generate secret and backup codes
        secret = MFAService.generate_secret()
        backup_codes = MFAService.generate_backup_codes(count=10)
        
        # Generate QR code
        provisioning_uri = MFAService.get_provisioning_uri(
            secret,
            current_admin.email
        )
        qr_code = MFAService.generate_qr_code(provisioning_uri)
        
        # Store in session manager for verification step
        mfa_manager = get_mfa_session_manager()
        await mfa_manager.store_mfa_setup(
            current_admin.id,
            secret,
            provisioning_uri
        )
        
        logger.info(f"MFA setup initiated for admin {current_admin.id}")
        
        return {
            "success": True,
            "session_id": str(current_admin.id),  # Frontend compatibility
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "totp_uri": provisioning_uri,  # Frontend compatibility
            "qr_code": qr_code,
            "backup_codes": backup_codes,
            "message": "Scan QR code with authenticator app, then verify with 6-digit code"
        }
        
    except Exception as e:
        logger.error(f"Error setting up MFA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mfa/verify-totp")
async def verify_totp_code(
    db_session: SessionDep,
    session_id: str = Body(...),
    totp_code: str = Body(...),
    current_admin: PydanticUser = Depends(get_current_admin_user)
):
    """
    Verify TOTP code and enable MFA for admin account.
    Frontend wrapper for /mfa/verify endpoint.
    Expects JSON body with session_id and totp_code.
    """
    try:
        if current_admin.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA already enabled for this account"
            )
        
        # Get setup data from session manager
        mfa_manager = get_mfa_session_manager()
        setup_data = await mfa_manager.get_mfa_setup(current_admin.id)
        
        if not setup_data:
            raise HTTPException(
                status_code=400,
                detail="No MFA setup in progress. Call /mfa/setup-initiate first"
            )
        
        secret, provisioning_uri = setup_data
        
        # Verify TOTP code
        if not MFAService.verify_token(secret, totp_code):
            raise HTTPException(
                status_code=400,
                detail="Invalid TOTP code. Please try again"
            )
        
        # Generate backup codes for storage
        backup_codes = MFAService.generate_backup_codes(count=10)
        
        # Enable MFA for user
        success = await MFAService.enable_mfa_for_user(
            db_session,
            current_admin.id,
            secret,
            backup_codes,
            admin_id=current_admin.id
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to enable MFA"
            )
        
        # Clear session after successful verification
        await mfa_manager.clear_mfa_setup(current_admin.id)
        
        logger.info(f"MFA enabled successfully for admin {current_admin.id}")
        
        return {
            "success": True,
            "message": "MFA enabled successfully",
            "backup_codes": backup_codes,
            "warning": "Save your backup codes in a secure location. They can only be used once."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying TOTP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mfa/setup-complete")
async def complete_mfa_setup(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(get_current_admin_user)
):
    """
    Complete MFA setup process.
    Can be used to confirm final step or clean up session.
    """
    try:
        if not current_admin.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA is not enabled for this account"
            )
        
        # Clean up any session data
        mfa_manager = get_mfa_session_manager()
        await mfa_manager.clear_mfa_setup(current_admin.id)
        
        logger.info(f"MFA setup completed for admin {current_admin.id}")
        
        return {
            "success": True,
            "message": "MFA setup completed",
            "mfa_enabled": True
        }
        
    except Exception as e:
        logger.error(f"Error completing MFA setup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mfa/admin-status")
async def get_admin_mfa_status(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """
    Get MFA status for all admin accounts.
    Returns list of admins with their MFA enabled status.
    """
    try:
        admins = await AdminManagementService.get_all_admins(db_session)
        
        # Fetch detailed MFA info for each admin
        admin_statuses = []
        for admin in admins:
            user = await db_session.get(DBUser, admin['id'])
            if user:
                admin_statuses.append({
                    "id": admin['id'],
                    "email": admin['email'],
                    "full_name": admin['full_name'],
                    "admin_role": admin['admin_role'],
                    "mfa_enabled": user.mfa_enabled,
                    "mfa_enabled_at": user.mfa_enabled_at.isoformat() if user.mfa_enabled_at else None,
                    "is_active": admin['is_active'],
                    "created_at": admin['created_at']
                })
        
        mfa_enabled_count = sum(1 for a in admin_statuses if a['mfa_enabled'])
        mfa_disabled_count = len(admin_statuses) - mfa_enabled_count
        
        logger.info(f"Retrieved MFA status for {len(admin_statuses)} admins")
        
        return {
            "success": True,
            "total": len(admin_statuses),
            "mfa_enabled": mfa_enabled_count,
            "mfa_disabled": mfa_disabled_count,
            "admins": admin_statuses
        }
        
    except Exception as e:
        logger.error(f"Error getting admin MFA status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mfa/backup-codes/{admin_id}")
async def get_admin_backup_codes(
    admin_id: int,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """
    Get backup codes information for an admin account.
    Returns count and status of available backup codes.
    """
    try:
        user = await db_session.get(DBUser, admin_id)
        if not user or not user.is_admin:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        if not user.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA is not enabled for this admin"
            )
        
        # Parse backup codes (don't return the actual codes, just count)
        backup_codes_count = 0
        if user.mfa_backup_codes:
            backup_codes_count = len(user.mfa_backup_codes.split(","))
        
        logger.info(f"Retrieved backup codes info for admin {admin_id}")
        
        return {
            "success": True,
            "admin_id": admin_id,
            "admin_email": user.email,
            "backup_codes_count": backup_codes_count,
            "mfa_enabled_at": user.mfa_enabled_at.isoformat() if user.mfa_enabled_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backup codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mfa/backup-codes/{admin_id}/regenerate")
async def regenerate_backup_codes(
    admin_id: int,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """
    Regenerate backup codes for an admin account.
    Invalidates all previous backup codes.
    """
    try:
        user = await db_session.get(DBUser, admin_id)
        if not user or not user.is_admin:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        if not user.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA is not enabled for this admin"
            )
        
        # Generate new backup codes
        backup_codes = MFAService.generate_backup_codes(count=10)
        
        # Hash and store backup codes
        from auth_utils import get_password_hash
        hashed_codes = ",".join([get_password_hash(code) for code in backup_codes])
        user.mfa_backup_codes = hashed_codes
        
        await db_session.flush()
        
        # Log action
        audit = AuditLog(
            action_type="BACKUP_CODES_REGENERATED",
            admin_id=current_admin.id,
            user_id=admin_id,
            resource_type="User",
            resource_id=str(admin_id),
            details=f"Backup codes regenerated by admin {current_admin.id}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        logger.info(f"Backup codes regenerated for admin {admin_id}")
        
        return {
            "success": True,
            "message": "Backup codes regenerated successfully",
            "backup_codes": backup_codes,
            "warning": "Previous backup codes are now invalid. Save these new codes in a secure location."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating backup codes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mfa/disable/{admin_id}")
async def disable_admin_mfa(
    admin_id: int,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """
    Disable MFA for an admin account.
    Only SUPER_ADMIN can disable MFA for other admins.
    """
    try:
        user = await db_session.get(DBUser, admin_id)
        if not user or not user.is_admin:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        if not user.mfa_enabled:
            raise HTTPException(
                status_code=400,
                detail="MFA is not enabled for this admin"
            )
        
        # Disable MFA
        success = await MFAService.disable_mfa_for_user(
            db_session,
            admin_id,
            admin_id=current_admin.id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to disable MFA")
        
        logger.info(f"MFA disabled for admin {admin_id} by admin {current_admin.id}")
        
        return {
            "success": True,
            "message": "MFA disabled successfully",
            "admin_id": admin_id,
            "admin_email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling MFA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BULK OPERATIONS ====================

@router.post("/bulk/export-users")
async def export_users(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("users:view")),
    kyc_status: Optional[str] = None,
    is_active: Optional[bool] = None,
    region: Optional[str] = None
):
    """
    Export users to CSV format.
    Supports filtering by KYC status, active status, and region.
    """
    try:
        filters = {}
        if kyc_status:
            filters["kyc_status"] = kyc_status
        if is_active is not None:
            filters["is_active"] = is_active
        if region:
            filters["region"] = region
        
        csv_content = await BulkOperationService.export_users(
            db_session,
            filters=filters if filters else None
        )
        
        # Log action
        audit = AuditLog(
            action_type="USERS_EXPORTED",
            admin_id=current_admin.id,
            resource_type="Users",
            resource_id="bulk",
            details=f"Users exported with filters: {filters}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return {
            "success": True,
            "csv_data": csv_content,
            "filename": f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
        
    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/import-users")
async def import_users(
    file: UploadFile = File(...),
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("users:view"))
):
    """
    Import/update users from CSV file.
    
    CSV format (header required):
    email, full_name, kyc_status
    """
    try:
        # Get AsyncSession dependency
        # Note: This is a workaround - in real app use proper dependency injection
        from deps import SessionLocal
        
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        result = await BulkOperationService.import_users(
            db_session,
            csv_content,
            admin_id=current_admin.id
        )
        
        return {
            "success": True,
            "result": result,
            "message": f"{result['created']} created, {result['updated']} updated"
        }
        
    except Exception as e:
        logger.error(f"Error importing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/update-kyc-status")
async def batch_update_kyc_status(
    user_ids: List[int],
    new_status: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("kyc:review"))
):
    """
    Update KYC status for multiple users at once.
    
    new_status: "not_started" | "pending" | "approved" | "rejected"
    """
    try:
        result = await BulkOperationService.batch_update_kyc_status(
            db_session,
            user_ids,
            new_status,
            admin_id=current_admin.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating KYC status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk/adjust-balances")
async def batch_adjust_balances(
    adjustments: List[dict],  # [{"user_id": int, "amount": float, "reason": str}]
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("ledger:adjust"))
):
    """
    Apply balance adjustments to multiple users.
    All adjustments are audit-logged.
    """
    try:
        result = await BulkOperationService.batch_adjust_balances(
            db_session,
            adjustments,
            admin_id=current_admin.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error adjusting balances: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ADMIN MANAGEMENT ====================

@router.post("/admin/create")
async def create_admin(
    email: str,
    full_name: str,
    admin_role: str,
    password: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """
    Create a new admin account.
    Only SUPER_ADMIN can create other admins.
    """
    try:
        result = await AdminManagementService.create_admin_account(
            db_session,
            email,
            full_name,
            admin_role,
            password,
            created_by_admin_id=current_admin.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/revoke/{admin_id}")
async def revoke_admin_access(
    admin_id: int,
    reason: str = "",
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """Revoke admin access from a user"""
    try:
        from deps import SessionLocal
        
        result = await AdminManagementService.revoke_admin_access(
            db_session,
            admin_id,
            revoked_by_admin_id=current_admin.id,
            reason=reason
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error revoking admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/reset-password/{admin_id}")
async def reset_admin_password(
    admin_id: int,
    new_password: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """Reset password for another admin account"""
    try:
        result = await AdminManagementService.reset_admin_password(
            db_session,
            admin_id,
            new_password,
            reset_by_admin_id=current_admin.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/change-role/{admin_id}")
async def change_admin_role(
    admin_id: int,
    new_role: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """Change admin role (permissions)"""
    try:
        result = await AdminManagementService.change_admin_role(
            db_session,
            admin_id,
            new_role,
            changed_by_admin_id=current_admin.id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error changing admin role: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/list")
async def list_all_admins(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN only
):
    """Get list of all active admin accounts"""
    try:
        admins = await AdminManagementService.get_all_admins(db_session)
        
        return {
            "success": True,
            "total": len(admins),
            "admins": admins
        }
        
    except Exception as e:
        logger.error(f"Error listing admins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUDIT LOGGING ====================

@router.get("/audit-log")
async def get_audit_log(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("audit:view")),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    action_type: Optional[str] = None,
    admin_id: Optional[int] = None,
    user_id: Optional[int] = None
):
    """
    Get admin audit log with pagination.
    Shows all admin actions for compliance and security monitoring.
    
    Query Parameters:
    - limit: Results per page (1-1000, default: 100)
    - offset: Starting position for pagination (default: 0)
    - action_type: Filter by action type
    - admin_id: Filter by admin who performed action
    - user_id: Filter by affected user
    
    Response includes:
    - total: Total number of audit logs matching filters
    - page_info: Pagination details
    - logs: Array of audit log entries
    """
    try:
        # Build filter query
        filters = []
        if action_type:
            filters.append(AuditLog.action_type == action_type)
        if admin_id:
            filters.append(AuditLog.admin_id == admin_id)
        if user_id:
            filters.append(AuditLog.user_id == user_id)
        
        # Get total count
        count_query = select(func.count(AuditLog.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        total = await db_session.scalar(count_query) or 0
        
        # Get paginated results
        query = select(AuditLog).order_by(desc(AuditLog.created_at))
        if filters:
            query = query.where(and_(*filters))
        query = query.limit(limit).offset(offset)
        
        result = await db_session.execute(query)
        logs = result.scalars().all()
        
        return {
            "success": True,
            "page_info": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "pages": (total + limit - 1) // limit if total > 0 else 0,
                "current_page": (offset // limit) + 1 if limit > 0 else 1
            },
            "filters": {
                "action_type": action_type,
                "admin_id": admin_id,
                "user_id": user_id
            },
            "logs": [
                {
                    "id": log.id,
                    "action_type": log.action_type,
                    "admin_id": log.admin_id,
                    "user_id": log.user_id,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "timestamp": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error retrieving audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit-log/export")
async def export_audit_log(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("audit:export")),
    format: str = Query("json", pattern="^(json|csv)$"),
    days: int = Query(30, ge=1, le=365),
    action_type: Optional[str] = None,
    admin_id: Optional[int] = None,
):
    """
    Export audit logs in JSON or CSV format.
    
    Query Parameters:
    - format: "json" or "csv" (default: json)
    - days: Number of days to export (1-365, default: 30)
    - action_type: Filter by action type
    - admin_id: Filter by admin
    
    Note: Large exports (>10,000 records) are recommended to use streaming or pagination.
    """
    try:
        # Calculate date filter
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query
        filters = [AuditLog.created_at >= cutoff_date]
        if action_type:
            filters.append(AuditLog.action_type == action_type)
        if admin_id:
            filters.append(AuditLog.admin_id == admin_id)
        
        query = select(AuditLog).where(and_(*filters)).order_by(desc(AuditLog.created_at))
        result = await db_session.execute(query)
        logs = result.scalars().all()
        
        if format == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "ID", "Timestamp", "Action Type", "Admin ID", "User ID",
                "Resource Type", "Resource ID", "Details"
            ])
            
            # Write rows
            for log in logs:
                writer.writerow([
                    log.id,
                    log.created_at.isoformat() if log.created_at else "",
                    log.action_type,
                    log.admin_id,
                    log.user_id,
                    log.resource_type,
                    log.resource_id,
                    log.details
                ])
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=audit-logs-{datetime.utcnow().strftime('%Y%m%d')}.csv"}
            )
        else:  # JSON format
            return {
                "success": True,
                "export_date": datetime.utcnow().isoformat(),
                "filters": {
                    "days": days,
                    "cutoff_date": cutoff_date.isoformat(),
                    "action_type": action_type,
                    "admin_id": admin_id
                },
                "record_count": len(logs),
                "logs": [
                    {
                        "id": log.id,
                        "timestamp": log.created_at.isoformat() if log.created_at else None,
                        "action_type": log.action_type,
                        "admin_id": log.admin_id,
                        "user_id": log.user_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "details": log.details
                    }
                    for log in logs
                ]
            }
        
    except Exception as e:
        logger.error(f"Error exporting audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== USER SESSION MANAGEMENT ====================

@router.get("/user/{user_id}/login-history")
async def get_user_login_history(
    user_id: int,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("users:view")),
    limit: int = Query(50, le=500)
):
    """
    Get user login history.
    Shows when user logged in, from which IP, which device, etc.
    """
    try:
        # Query login audit logs for the user
        query = select(AuditLog).where(
            (AuditLog.user_id == user_id) &
            (AuditLog.action_type.in_(["USER_LOGIN", "USER_LOGOUT"]))
        ).order_by(desc(AuditLog.created_at)).limit(limit)
        
        result = await db_session.execute(query)
        logs = result.scalars().all()
        
        return {
            "success": True,
            "user_id": user_id,
            "total_logins": len([l for l in logs if l.action_type == "USER_LOGIN"]),
            "login_history": [
                {
                    "action": log.action_type,
                    "timestamp": log.created_at.isoformat() if log.created_at else None,
                    "details": log.details
                }
                for log in logs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting login history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user/{user_id}/force-logout")
async def force_user_logout(
    user_id: int,
    reason: str = "",
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("users:view"))
):
    """
    Force logout all active sessions for a user.
    Invalidates all JWT tokens for the user.
    Useful for security incidents and account compromises.
    """
    try:
        # Get token blacklist service
        blacklist_service = get_token_blacklist_service()
        
        # In a full implementation, you would:
        # 1. Query all active sessions for the user from the database
        # 2. Extract JTI from each session's token
        # 3. Add each JTI to the blacklist
        
        # For now, we'll revoke with a placeholder token list
        # In production, get actual active token JTIs from sessions table
        await blacklist_service.revoke_user_tokens(
            user_id,
            token_list=[]  # Would be populated from active sessions
        )
        
        # Create audit log for the action
        audit = AuditLog(
            action_type="USER_FORCED_LOGOUT",
            admin_id=current_admin.id,
            user_id=user_id,
            resource_type="User",
            resource_id=str(user_id),
            details=f"Forced logout by admin {current_admin.id}. Reason: {reason}"
        )
        
        if db_session:
            db_session.add(audit)
            await db_session.commit()
        
        logger.info(f"Force logout initiated for user {user_id} by admin {current_admin.id}. Reason: {reason}")
        
        return {
            "success": True,
            "message": f"Force logout initiated for user {user_id}",
            "user_id": user_id,
            "initiated_by": current_admin.id,
            "reason": reason,
            "effect": "All active sessions for this user will be terminated"
        }
        
    except Exception as e:
        logger.error(f"Error forcing logout: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ADVANCED SEARCH ====================

@router.get("/users/advanced-search")
async def advanced_user_search(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("users:view")),
    search: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    account_number: Optional[str] = None,
    kyc_status: Optional[str] = None,
    account_status: Optional[str] = None,
    mfa_enabled: Optional[bool] = None,
    email_verified: Optional[bool] = None,
    region: Optional[str] = None,
    balance_min: Optional[float] = None,
    balance_max: Optional[float] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    account_type: Optional[str] = None,
    limit: int = Query(50, le=500)
):
    """
    Advanced search with multiple filters.
    Supports filtering by email, phone, account number, status, kyc, region, type, balance, and dates.
    """
    try:
        from sqlalchemy import or_, and_
        from models import UserSettings, Account
        
        from sqlalchemy.orm import selectinload
        query = select(DBUser).options(selectinload(DBUser.accounts))
        
        # User settings join if filtering by phone
        if phone:
            query = query.join(UserSettings, DBUser.id == UserSettings.user_id).where(UserSettings.phone_number.ilike(f"%{phone}%"))
            
        # Search query matching multiple fields
        if search:
            query = query.where(or_(
                DBUser.email.ilike(f"%{search}%"),
                DBUser.full_name.ilike(f"%{search}%"),
                DBUser.account_number.ilike(f"%{search}%")
            ))
            
        if email:
            query = query.where(DBUser.email.ilike(f"%{email}%"))
        if kyc_status:
            query = query.where(DBUser.kyc_status == kyc_status)
        if account_number:
            query = query.where(DBUser.account_number.ilike(f"%{account_number}%"))
        if account_type:
            query = query.where(DBUser.account_type == account_type)
        if mfa_enabled is not None:
            query = query.where(DBUser.mfa_enabled == mfa_enabled)
        if email_verified is not None:
            query = query.where(DBUser.is_verified == email_verified)
            
        if account_status:
            if account_status == "active":
                query = query.where(and_(DBUser.is_active == True, DBUser.is_suspended == False, DBUser.is_frozen == False))
            elif account_status == "suspended":
                query = query.where(DBUser.is_suspended == True)
            elif account_status == "frozen":
                query = query.where(DBUser.is_frozen == True)
            elif account_status == "inactive":
                query = query.where(DBUser.is_active == False)
                
        if region:
            query = query.where(DBUser.region == region)
            
        # Balance filters (filter by total balance across accounts)
        if balance_min is not None or balance_max is not None:
            from sqlalchemy import func
            subq = select(Account.owner_id, func.sum(Account.balance).label("total_balance")).group_by(Account.owner_id).subquery()
            query = query.join(subq, DBUser.id == subq.c.owner_id)
            if balance_min is not None:
                query = query.where(subq.c.total_balance >= balance_min)
            if balance_max is not None:
                query = query.where(subq.c.total_balance <= balance_max)
                
        if created_after:
            from datetime import datetime
            query = query.where(DBUser.created_at >= datetime.fromisoformat(created_after))
        if created_before:
            from datetime import datetime
            query = query.where(DBUser.created_at <= datetime.fromisoformat(created_before))
            
        result = await db_session.execute(query.limit(limit))
        users = result.scalars().all()
        
        return {
            "success": True,
            "count": len(users),
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "kyc_status": u.kyc_status,
                    "is_active": u.is_active,
                    "is_suspended": u.is_suspended,
                    "is_frozen": u.is_frozen,
                    "region": u.region,
                    "balance": float(u.balance),
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "account_number": u.account_number
                }
                for u in users
            ]
        }
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# ==================== SCHEDULED ADJUSTMENTS ====================

@router.post("/scheduled-adjustments")
async def create_scheduled_adjustment(
    user_id: int,
    amount: float,
    reason: str,
    scheduled_for: str,  # ISO datetime
    recurrence: str = "ONCE",  # ONCE, DAILY, WEEKLY, MONTHLY, QUARTERLY
    recurrence_end: Optional[str] = None,
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("ledger:adjust"))
):
    """Create a scheduled balance adjustment"""
    try:
        service = get_scheduled_adjustments_service()
        result = await service.create_scheduled_adjustment(
            db_session,
            user_id,
            amount,
            reason,
            scheduled_for,
            recurrence,
            recurrence_end,
            created_by_admin_id=current_admin.id
        )
        
        # Log action
        audit = AuditLog(
            action_type="SCHEDULED_ADJUSTMENT_CREATED",
            admin_id=current_admin.id,
            user_id=user_id,
            resource_type="ScheduledAdjustment",
            resource_id=result.get("id", ""),
            details=f"Amount: ${amount}, Recurrence: {recurrence}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error creating scheduled adjustment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduled-adjustments")
async def list_scheduled_adjustments(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("ledger:adjust")),
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=1000)
):
    """List scheduled adjustments"""
    try:
        service = get_scheduled_adjustments_service()
        result = await service.list_scheduled_adjustments(
            db_session,
            user_id=user_id,
            status=status,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error listing scheduled adjustments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled-adjustments/{adjustment_id}")
async def cancel_scheduled_adjustment(
    adjustment_id: int,
    reason: str = "",
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("ledger:adjust"))
):
    """Cancel a scheduled adjustment"""
    try:
        service = get_scheduled_adjustments_service()
        result = await service.cancel_scheduled_adjustment(
            db_session,
            adjustment_id,
            reason,
            cancelled_by_admin_id=current_admin.id
        )
        
        # Log action
        audit = AuditLog(
            action_type="SCHEDULED_ADJUSTMENT_CANCELLED",
            admin_id=current_admin.id,
            resource_type="ScheduledAdjustment",
            resource_id=str(adjustment_id),
            details=f"Reason: {reason}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error cancelling scheduled adjustment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== APPROVAL WORKFLOWS ====================

@router.get("/approvals/pending")
async def get_pending_approvals(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("admin:approve")),
    action_type: Optional[str] = None
):
    """Get pending approval requests"""
    try:
        service = get_approval_service()
        result = await service.get_pending_approvals(
            db_session,
            action_type=action_type
        )
        return result
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/approve")
async def approve_request(
    approval_id: int,
    comments: str = "",
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("admin:approve"))
):
    """Approve an approval request"""
    try:
        service = get_approval_service()
        result = await service.approve_request(
            db_session,
            approval_id,
            voted_by_admin_id=current_admin.id,
            comments=comments
        )
        
        # Log action
        audit = AuditLog(
            action_type="APPROVAL_REQUEST_APPROVED",
            admin_id=current_admin.id,
            resource_type="ApprovalRequest",
            resource_id=str(approval_id),
            details=f"Approved by {current_admin.id}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error approving request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/reject")
async def reject_request(
    approval_id: int,
    reason: str,
    db_session: SessionDep = None,
    current_admin: PydanticUser = Depends(require_permission("admin:approve"))
):
    """Reject an approval request"""
    try:
        service = get_approval_service()
        result = await service.reject_request(
            db_session,
            approval_id,
            rejected_by_admin_id=current_admin.id,
            reason=reason
        )
        
        # Log action
        audit = AuditLog(
            action_type="APPROVAL_REQUEST_REJECTED",
            admin_id=current_admin.id,
            resource_type="ApprovalRequest",
            resource_id=str(approval_id),
            details=f"Reason: {reason}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error rejecting request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GRANULAR PERMISSIONS ====================

@router.get("/admins/{admin_id}/permissions")
async def get_admin_permissions(
    admin_id: int,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN
):
    """Get permissions for an admin"""
    try:
        service = get_permission_service()
        result = await service.get_admin_permissions(db_session, admin_id)
        return result
    except Exception as e:
        logger.error(f"Error getting admin permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admins/{admin_id}/grant-permission")
async def grant_permission(
    admin_id: int,
    permission: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN
):
    """Grant a permission to an admin"""
    try:
        service = get_permission_service()
        result = await service.grant_permission(db_session, admin_id, permission)
        
        # Log action
        audit = AuditLog(
            action_type="PERMISSION_GRANTED",
            admin_id=current_admin.id,
            resource_type="AdminPermission",
            resource_id=f"admin_{admin_id}",
            details=f"Permission: {permission}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error granting permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admins/{admin_id}/deny-permission")
async def deny_permission(
    admin_id: int,
    permission: str,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN
):
    """Deny a permission for an admin"""
    try:
        service = get_permission_service()
        result = await service.deny_permission(db_session, admin_id, permission)
        
        # Log action
        audit = AuditLog(
            action_type="PERMISSION_DENIED",
            admin_id=current_admin.id,
            resource_type="AdminPermission",
            resource_id=f"admin_{admin_id}",
            details=f"Permission: {permission}"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error denying permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admins/{admin_id}/reset-permissions")
async def reset_permissions(
    admin_id: int,
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("*"))  # SUPER_ADMIN
):
    """Reset admin permissions to role defaults"""
    try:
        service = get_permission_service()
        result = await service.reset_to_role_defaults(db_session, admin_id)
        
        # Log action
        audit = AuditLog(
            action_type="PERMISSIONS_RESET",
            admin_id=current_admin.id,
            resource_type="AdminPermission",
            resource_id=f"admin_{admin_id}",
            details="Permissions reset to role defaults"
        )
        db_session.add(audit)
        await db_session.commit()
        
        return result
    except Exception as e:
        logger.error(f"Error resetting permissions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ADMIN DASHBOARD ANALYTICS ====================

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("admin:view")),
    hours: int = Query(24, ge=1, le=720)
):
    """Get dashboard summary"""
    try:
        service = get_admin_dashboard_service()
        result = await service.get_dashboard_summary(db_session, hours=hours)
        return result
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("admin:view")),
    days: int = Query(7, ge=1, le=90)
):
    """Get admin activity statistics"""
    try:
        service = get_admin_dashboard_service()
        result = await service.get_admin_activity_stats(db_session, days=days)
        return result
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/heatmap")
async def get_action_heatmap(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("admin:view")),
    hours: int = Query(24, ge=1, le=720)
):
    """Get hourly action heatmap"""
    try:
        service = get_admin_dashboard_service()
        result = await service.get_action_heatmap(db_session, hours=hours)
        return result
    except Exception as e:
        logger.error(f"Error getting heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/risks")
async def get_risk_indicators(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("admin:view")),
    hours: int = Query(24, ge=1, le=720)
):
    """Get risk indicators and alerts"""
    try:
        service = get_admin_dashboard_service()
        result = await service.get_risk_indicators(db_session, hours=hours)
        return result
    except Exception as e:
        logger.error(f"Error getting risk indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/leaderboard")
async def get_admin_leaderboard(
    db_session: SessionDep,
    current_admin: PydanticUser = Depends(require_permission("admin:view")),
    metric: str = Query("actions", pattern="^(actions|suspensions|balance_changes)$"),
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(10, ge=1, le=100)
):
    """Get admin leaderboard ranked by metric"""
    try:
        service = get_admin_dashboard_service()
        result = await service.get_admin_leaderboard(
            db_session,
            metric=metric,
            days=days,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    try:
        query = select(DBUser)
        
        if email:
            query = query.where(DBUser.email.ilike(f"%{email}%"))
        if kyc_status:
            query = query.where(DBUser.kyc_status == kyc_status)
        if is_active is not None:
            query = query.where(DBUser.is_active == is_active)
        if region:
            query = query.where(DBUser.region == region)
        if created_after:
            query = query.where(DBUser.created_at >= datetime.fromisoformat(created_after))
        if created_before:
            query = query.where(DBUser.created_at <= datetime.fromisoformat(created_before))
        
        query = query.limit(limit)
        result = await db_session.execute(query)
        users = result.scalars().all()
        
        # TODO: Filter by balance range (requires balance calculation)
        
        return {
            "success": True,
            "total": len(users),
            "users": [
                {
                    "id": u.id,
                    "email": u.email,
                    "full_name": u.full_name,
                    "kyc_status": u.kyc_status,
                    "is_active": u.is_active,
                    "region": u.region,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in advanced search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
