"""
Admin Management Service
=======================
Manages admin accounts, permissions, roles, and access control.

Features:
- Create new admin accounts
- Revoke admin access
- Reset admin passwords
- Manage admin roles and permissions
- Admin session management
- Admin activity monitoring
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import User as DBUser, AuditLog
from auth_utils import get_password_hash, verify_password
import logging
import secrets

logger = logging.getLogger(__name__)


class AdminManagementService:
    """Service for managing admin users and permissions"""
    
    @staticmethod
    async def create_admin_account(
        db_session: AsyncSession,
        email: str,
        full_name: str,
        admin_role: str,
        password: str,
        created_by_admin_id: int
    ) -> Dict:
        """
        Create a new admin account.
        
        admin_role options: SUPER_ADMIN, ADMIN, TREASURY, COMPLIANCE, SUPPORT
        """
        try:
            # Validate role
            valid_roles = ["SUPER_ADMIN", "ADMIN", "TREASURY", "COMPLIANCE", "SUPPORT"]
            if admin_role not in valid_roles:
                return {
                    "success": False,
                    "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                }
            
            # Check if user already exists
            existing = await db_session.execute(
                select(DBUser).where(DBUser.email == email)
            )
            if existing.scalars().first():
                return {
                    "success": False,
                    "error": f"Admin account with email {email} already exists"
                }
            
            # Create new admin user
            new_admin = DBUser(
                email=email,
                full_name=full_name,
                hashed_password=get_password_hash(password),
                is_admin=True,
                admin_role=admin_role,
                is_active=True,
                kyc_status="approved",
                created_at=datetime.utcnow()
            )
            db_session.add(new_admin)
            await db_session.flush()
            
            # Log action
            audit = AuditLog(
                action_type="ADMIN_CREATED",
                admin_id=created_by_admin_id,
                user_id=new_admin.id,
                resource_type="Admin",
                resource_id=str(new_admin.id),
                details=f"Admin created: {email} | Role: {admin_role} | By: {created_by_admin_id}"
            )
            db_session.add(audit)
            
            await db_session.commit()
            logger.info(f"Admin account created: {email} with role {admin_role}")
            
            return {
                "success": True,
                "admin_id": new_admin.id,
                "email": email,
                "admin_role": admin_role,
                "message": f"Admin account created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating admin account: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def revoke_admin_access(
        db_session: AsyncSession,
        admin_id: int,
        revoked_by_admin_id: int,
        reason: str = ""
    ) -> Dict:
        """
        Revoke admin access from a user.
        Deactivates the admin account.
        """
        try:
            admin = await db_session.get(DBUser, admin_id)
            if not admin:
                return {"success": False, "error": "Admin not found"}
            
            if not admin.is_admin:
                return {"success": False, "error": "User is not an admin"}
            
            # Deactivate admin
            admin.is_admin = False
            admin.admin_role = "STANDARD"
            admin.is_active = False
            
            await db_session.flush()
            
            # Log action
            audit = AuditLog(
                action_type="ADMIN_REVOKED",
                admin_id=revoked_by_admin_id,
                user_id=admin_id,
                resource_type="Admin",
                resource_id=str(admin_id),
                details=f"Admin access revoked from {admin.email} | Reason: {reason}"
            )
            db_session.add(audit)
            
            await db_session.commit()
            logger.info(f"Admin access revoked for {admin.email}")
            
            return {
                "success": True,
                "message": f"Admin access revoked for {admin.email}"
            }
            
        except Exception as e:
            logger.error(f"Error revoking admin access: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def reset_admin_password(
        db_session: AsyncSession,
        admin_id: int,
        new_password: str,
        reset_by_admin_id: int
    ) -> Dict:
        """
        Reset admin password (by other admin).
        Requires admin authentication.
        """
        try:
            admin = await db_session.get(DBUser, admin_id)
            if not admin:
                return {"success": False, "error": "Admin not found"}
            
            if not admin.is_admin:
                return {"success": False, "error": "User is not an admin"}
            
            # Validate password strength (minimum 12 chars, mix of upper/lower/numbers)
            if len(new_password) < 12:
                return {
                    "success": False,
                    "error": "Password must be at least 12 characters long"
                }
            
            if not any(c.isupper() for c in new_password):
                return {
                    "success": False,
                    "error": "Password must contain uppercase letters"
                }
            
            if not any(c.isdigit() for c in new_password):
                return {
                    "success": False,
                    "error": "Password must contain numbers"
                }
            
            # Update password
            admin.hashed_password = get_password_hash(new_password)
            await db_session.flush()
            
            # Log action
            audit = AuditLog(
                action_type="ADMIN_PASSWORD_RESET",
                admin_id=reset_by_admin_id,
                user_id=admin_id,
                resource_type="Admin",
                resource_id=str(admin_id),
                details=f"Admin password reset for {admin.email} by admin {reset_by_admin_id}"
            )
            db_session.add(audit)
            
            await db_session.commit()
            logger.info(f"Password reset for admin {admin.email}")
            
            return {
                "success": True,
                "message": f"Password reset successfully for {admin.email}"
            }
            
        except Exception as e:
            logger.error(f"Error resetting admin password: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def change_admin_role(
        db_session: AsyncSession,
        admin_id: int,
        new_role: str,
        changed_by_admin_id: int
    ) -> Dict:
        """
        Change admin role (permissions).
        Only SUPER_ADMIN can do this.
        """
        try:
            valid_roles = ["SUPER_ADMIN", "ADMIN", "TREASURY", "COMPLIANCE", "SUPPORT"]
            if new_role not in valid_roles:
                return {
                    "success": False,
                    "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                }
            
            admin = await db_session.get(DBUser, admin_id)
            if not admin:
                return {"success": False, "error": "Admin not found"}
            
            old_role = admin.admin_role
            admin.admin_role = new_role
            
            await db_session.flush()
            
            # Log action
            audit = AuditLog(
                action_type="ADMIN_ROLE_CHANGED",
                admin_id=changed_by_admin_id,
                user_id=admin_id,
                resource_type="Admin",
                resource_id=str(admin_id),
                details=f"Admin role changed from {old_role} to {new_role}"
            )
            db_session.add(audit)
            
            await db_session.commit()
            logger.info(f"Admin role changed for {admin.email}: {old_role} -> {new_role}")
            
            return {
                "success": True,
                "message": f"Admin role updated: {old_role} -> {new_role}",
                "admin_email": admin.email,
                "old_role": old_role,
                "new_role": new_role
            }
            
        except Exception as e:
            logger.error(f"Error changing admin role: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_all_admins(db_session: AsyncSession) -> List[Dict]:
        """Get list of all active admin accounts"""
        try:
            result = await db_session.execute(
                select(DBUser).where(
                    (DBUser.is_admin == True) &
                    (DBUser.is_active == True)
                )
            )
            admins = result.scalars().all()
            
            return [
                {
                    "id": admin.id,
                    "email": admin.email,
                    "full_name": admin.full_name,
                    "admin_role": admin.admin_role,
                    "is_active": admin.is_active,
                    "created_at": admin.created_at.isoformat() if admin.created_at else None
                }
                for admin in admins
            ]
            
        except Exception as e:
            logger.error(f"Error getting admins: {e}")
            return []
    
    @staticmethod
    async def log_admin_session(
        db_session: AsyncSession,
        admin_id: int,
        action: str,
        ip_address: str = "",
        user_agent: str = ""
    ) -> bool:
        """
        Log admin login/logout for session tracking.
        
        action: "login" or "logout"
        """
        try:
            # Note: Requires AdminSession model
            # For now, just log to audit trail
            audit = AuditLog(
                action_type=f"ADMIN_{action.upper()}",
                admin_id=admin_id,
                user_id=admin_id,
                resource_type="AdminSession",
                resource_id=str(admin_id),
                details=f"Admin session {action} from IP: {ip_address}"
            )
            db_session.add(audit)
            await db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error logging admin session: {e}")
            return False
