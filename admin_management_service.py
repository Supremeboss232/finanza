"""
Admin Management Service
=======================
Manages admin accounts, permissions, roles, and access control.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import User as DBUser, AuditLog, Account
from auth_utils import get_password_hash, verify_password
def generate_account_number() -> str:
    return str(1000000000 + secrets.randbelow(9000000000))
import rbac
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
        Create or promote an admin account.
        admin_role options: SUPER_ADMIN, ADMIN, TREASURY, COMPLIANCE, SUPPORT
        """
        try:
            admin_role = (admin_role or "ADMIN").strip().upper()
            valid_roles = ["SUPER_ADMIN", "ADMIN", "TREASURY", "COMPLIANCE", "SUPPORT"]
            if admin_role not in valid_roles:
                return {
                    "success": False,
                    "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                }

            email_clean = (email or "").strip().lower()
            if not email_clean or not password:
                return {"success": False, "error": "Email and password are required"}

            if len(password) < 8:
                return {"success": False, "error": "Password must be at least 8 characters long"}

            existing_res = await db_session.execute(
                select(DBUser).where(DBUser.email == email_clean)
            )
            existing_user = existing_res.scalars().first()

            if existing_user:
                existing_user.full_name = full_name or existing_user.full_name
                existing_user.hashed_password = get_password_hash(password)
                existing_user.is_admin = True
                existing_user.admin_role = admin_role
                existing_user.is_active = True
                existing_user.is_verified = True
                existing_user.kyc_status = "approved"
                target_admin = existing_user
                action_label = "ADMIN_PROMOTED_OR_UPDATED"
            else:
                acct_num = generate_account_number()
                target_admin = DBUser(
                    email=email_clean,
                    full_name=full_name or email_clean.split("@")[0],
                    hashed_password=get_password_hash(password),
                    account_number=acct_num,
                    is_admin=True,
                    admin_role=admin_role,
                    is_active=True,
                    is_verified=True,
                    kyc_status="approved",
                    created_at=datetime.utcnow()
                )
                db_session.add(target_admin)
                await db_session.flush()

                admin_acct = Account(
                    account_number=acct_num,
                    account_type="checking",
                    balance=0.0,
                    currency="USD",
                    owner_id=target_admin.id,
                    status="active",
                    is_admin_account=True
                )
                db_session.add(admin_acct)
                action_label = "ADMIN_CREATED"

            await db_session.flush()

            audit = AuditLog(
                action_type=action_label,
                admin_id=created_by_admin_id,
                user_id=target_admin.id,
                resource_type="Admin",
                resource_id=str(target_admin.id),
                details=f"Admin configured: {email_clean} | Role: {admin_role} | By: {created_by_admin_id}"
            )
            db_session.add(audit)

            await db_session.commit()
            logger.info(f"Admin account configured: {email_clean} with role {admin_role}")

            return {
                "success": True,
                "admin_id": target_admin.id,
                "email": email_clean,
                "admin_role": admin_role,
                "permissions": rbac.get_effective_permissions(target_admin),
                "message": f"Admin account ({admin_role}) configured successfully"
            }

        except Exception as e:
            await db_session.rollback()
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
        """
        try:
            admin = await db_session.get(DBUser, admin_id)
            if not admin:
                return {"success": False, "error": "Admin not found"}

            if not admin.is_admin:
                return {"success": False, "error": "User is not an admin"}

            if admin.id == revoked_by_admin_id:
                return {"success": False, "error": "You cannot revoke your own admin access"}

            admin.is_admin = False
            admin.admin_role = "STANDARD"
            admin.custom_permissions = None

            await db_session.flush()

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
            await db_session.rollback()
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
        Reset admin password (by SUPER_ADMIN).
        """
        try:
            admin = await db_session.get(DBUser, admin_id)
            if not admin:
                return {"success": False, "error": "Admin not found"}

            if not admin.is_admin:
                return {"success": False, "error": "User is not an admin"}

            if not new_password or len(new_password) < 8:
                return {
                    "success": False,
                    "error": "Password must be at least 8 characters long"
                }

            admin.hashed_password = get_password_hash(new_password)
            await db_session.flush()

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
            await db_session.rollback()
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
            new_role = (new_role or "").strip().upper()
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
            admin.is_admin = True
            admin.is_active = True

            await db_session.flush()

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
                "new_role": new_role,
                "permissions": rbac.get_effective_permissions(admin)
            }

        except Exception as e:
            await db_session.rollback()
            logger.error(f"Error changing admin role: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_all_admins(db_session: AsyncSession) -> List[Dict]:
        """Get list of all admin accounts with their effective permissions and role summary"""
        try:
            result = await db_session.execute(
                select(DBUser).where(DBUser.is_admin == True).order_by(DBUser.id.asc())
            )
            admins = result.scalars().all()
            matrix = rbac.get_role_matrix()

            out = []
            for admin in admins:
                resolved_role = rbac.resolve_admin_role(admin)
                r_info = matrix.get(resolved_role, matrix["ADMIN"])
                out.append({
                    "id": admin.id,
                    "email": admin.email,
                    "full_name": admin.full_name,
                    "admin_role": resolved_role,
                    "role_title": r_info.get("title", resolved_role),
                    "role_summary": r_info.get("summary", ""),
                    "can_do": r_info.get("can_do", []),
                    "cannot_do": r_info.get("cannot_do", []),
                    "permissions": rbac.get_effective_permissions(admin),
                    "has_custom_permissions": bool(getattr(admin, "custom_permissions", None)),
                    "mfa_enabled": bool(getattr(admin, "mfa_enabled", False)),
                    "is_active": bool(admin.is_active),
                    "created_at": admin.created_at.isoformat() if admin.created_at else None
                })
            return out

        except Exception as e:
            logger.error(f"Error getting admins: {e}")
            return []

    @staticmethod
    async def get_admin_activity(
        db_session: AsyncSession,
        admin_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict]:
        """Get activity logs for admin(s)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            query = select(AuditLog).where(AuditLog.created_at >= cutoff_date)
            if admin_id:
                query = query.where(AuditLog.admin_id == admin_id)

            result = await db_session.execute(query.order_by(AuditLog.created_at.desc()).limit(500))
            logs = result.scalars().all()

            return [
                {
                    "id": log.id,
                    "action_type": log.action_type,
                    "admin_id": log.admin_id,
                    "user_id": log.user_id,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]

        except Exception as e:
            logger.error(f"Error getting admin activity: {e}")
            return []
