"""
Granular Permission Control System
Fine-grained permission management beyond roles
"""

from typing import Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json

logger = logging.getLogger(__name__)


class Permission:
    """
    Granular permissions - more fine-grained than roles
    Example: admin has ADMIN role, but can have these specific permissions:
    - can_suspend_users: true
    - can_freeze_accounts: false
    - can_adjust_balance: false
    - can_view_transactions: true
    """
    
    # User Management Permissions
    PERM_VIEW_USERS = "perm:users:view"
    PERM_SUSPEND_USERS = "perm:users:suspend"
    PERM_FREEZE_ACCOUNTS = "perm:users:freeze"
    PERM_SEARCH_USERS = "perm:users:search"
    PERM_EXPORT_USERS = "perm:users:export"
    PERM_IMPORT_USERS = "perm:users:import"
    
    # KYC Permissions
    PERM_VIEW_KYC = "perm:kyc:view"
    PERM_APPROVE_KYC = "perm:kyc:approve"
    PERM_REJECT_KYC = "perm:kyc:reject"
    
    # Transaction Permissions
    PERM_VIEW_TRANSACTIONS = "perm:transactions:view"
    PERM_BLOCK_TRANSACTIONS = "perm:transactions:block"
    
    # Balance Permissions
    PERM_VIEW_BALANCE = "perm:balance:view"
    PERM_ADJUST_BALANCE = "perm:balance:adjust"
    PERM_VIEW_LEDGER = "perm:balance:ledger"
    
    # Admin Permissions
    PERM_CREATE_ADMIN = "perm:admin:create"
    PERM_REVOKE_ADMIN = "perm:admin:revoke"
    PERM_RESET_PASSWORD = "perm:admin:reset_password"
    PERM_CHANGE_ADMIN_ROLE = "perm:admin:change_role"
    PERM_LIST_ADMINS = "perm:admin:list"
    
    # MFA Permissions
    PERM_SETUP_MFA = "perm:mfa:setup"
    PERM_VERIFY_MFA = "perm:mfa:verify"
    PERM_DISABLE_MFA = "perm:mfa:disable"
    
    # Security Permissions
    PERM_FORCE_LOGOUT = "perm:security:force_logout"
    PERM_MANAGE_RATE_LIMITS = "perm:security:manage_rate_limits"
    
    # Audit Permissions
    PERM_VIEW_AUDIT_LOG = "perm:audit:view"
    PERM_EXPORT_AUDIT_LOG = "perm:audit:export"
    
    # Role Management Permissions
    PERM_CREATE_ROLES = "perm:roles:create"
    PERM_MODIFY_ROLES = "perm:roles:modify"
    PERM_DELETE_ROLES = "perm:roles:delete"
    
    # All permissions
    ALL_PERMISSIONS = [
        # User Management
        PERM_VIEW_USERS,
        PERM_SUSPEND_USERS,
        PERM_FREEZE_ACCOUNTS,
        PERM_SEARCH_USERS,
        PERM_EXPORT_USERS,
        PERM_IMPORT_USERS,
        # KYC
        PERM_VIEW_KYC,
        PERM_APPROVE_KYC,
        PERM_REJECT_KYC,
        # Transactions
        PERM_VIEW_TRANSACTIONS,
        PERM_BLOCK_TRANSACTIONS,
        # Balance
        PERM_VIEW_BALANCE,
        PERM_ADJUST_BALANCE,
        PERM_VIEW_LEDGER,
        # Admin
        PERM_CREATE_ADMIN,
        PERM_REVOKE_ADMIN,
        PERM_RESET_PASSWORD,
        PERM_CHANGE_ADMIN_ROLE,
        PERM_LIST_ADMINS,
        # MFA
        PERM_SETUP_MFA,
        PERM_VERIFY_MFA,
        PERM_DISABLE_MFA,
        # Security
        PERM_FORCE_LOGOUT,
        PERM_MANAGE_RATE_LIMITS,
        # Audit
        PERM_VIEW_AUDIT_LOG,
        PERM_EXPORT_AUDIT_LOG,
        # Roles
        PERM_CREATE_ROLES,
        PERM_MODIFY_ROLES,
        PERM_DELETE_ROLES,
    ]


class RolePermissionDefaults:
    """Default permissions for each role"""
    
    ROLE_DEFAULTS = {
        'SUPER_ADMIN': Permission.ALL_PERMISSIONS,
        'ADMIN': [
            # Full user management
            Permission.PERM_VIEW_USERS,
            Permission.PERM_SUSPEND_USERS,
            Permission.PERM_FREEZE_ACCOUNTS,
            Permission.PERM_SEARCH_USERS,
            Permission.PERM_EXPORT_USERS,
            Permission.PERM_IMPORT_USERS,
            # KYC management
            Permission.PERM_VIEW_KYC,
            Permission.PERM_APPROVE_KYC,
            Permission.PERM_REJECT_KYC,
            # Transaction viewing
            Permission.PERM_VIEW_TRANSACTIONS,
            # Audit access
            Permission.PERM_VIEW_AUDIT_LOG,
            # MFA setup
            Permission.PERM_SETUP_MFA,
            Permission.PERM_VERIFY_MFA,
        ],
        'TREASURY': [
            # Balance management only
            Permission.PERM_VIEW_BALANCE,
            Permission.PERM_ADJUST_BALANCE,
            Permission.PERM_VIEW_LEDGER,
            Permission.PERM_VIEW_USERS,  # Need to see users for balance adjustments
            Permission.PERM_VIEW_AUDIT_LOG,
        ],
        'COMPLIANCE': [
            # Compliance focused
            Permission.PERM_VIEW_USERS,
            Permission.PERM_SEARCH_USERS,
            Permission.PERM_VIEW_KYC,
            Permission.PERM_APPROVE_KYC,
            Permission.PERM_REJECT_KYC,
            Permission.PERM_VIEW_AUDIT_LOG,
            Permission.PERM_EXPORT_AUDIT_LOG,
        ],
        'SUPPORT': [
            # View only + password reset
            Permission.PERM_VIEW_USERS,
            Permission.PERM_SEARCH_USERS,
            Permission.PERM_VIEW_TRANSACTIONS,
            Permission.PERM_VIEW_BALANCE,
            Permission.PERM_RESET_PASSWORD,
            Permission.PERM_VIEW_AUDIT_LOG,
        ],
    }


class GranularPermissionService:
    """
    Manage granular permissions per admin user
    Allows override of role-based permissions
    """
    
    def __init__(self):
        pass
    
    async def grant_permission(
        self,
        db: AsyncSession,
        admin_id: str,
        permission: str,
    ) -> bool:
        """Grant a specific permission to an admin"""
        from models import User
        
        try:
            stmt = select(User).where(User.id == admin_id)
            user = await db.scalar(stmt)
            
            if not user or not user.is_admin:
                logger.warning(f"User {admin_id} is not admin")
                return False
            
            # Parse current permissions
            current_perms = json.loads(user.custom_permissions or '{}')
            grant_dict = current_perms.get('granted', [])
            deny_dict = current_perms.get('denied', [])
            
            # Add permission
            if permission not in grant_dict:
                grant_dict.append(permission)
            
            # Remove from denied if present
            if permission in deny_dict:
                deny_dict.remove(permission)
            
            # Save
            user.custom_permissions = json.dumps({
                'granted': grant_dict,
                'denied': deny_dict,
            })
            await db.commit()
            
            logger.info(f"Granted permission {permission} to admin {admin_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to grant permission: {e}")
            return False
    
    async def deny_permission(
        self,
        db: AsyncSession,
        admin_id: str,
        permission: str,
    ) -> bool:
        """Deny a specific permission to an admin"""
        from models import User
        
        try:
            stmt = select(User).where(User.id == admin_id)
            user = await db.scalar(stmt)
            
            if not user or not user.is_admin:
                logger.warning(f"User {admin_id} is not admin")
                return False
            
            # Parse current permissions
            current_perms = json.loads(user.custom_permissions or '{}')
            grant_dict = current_perms.get('granted', [])
            deny_dict = current_perms.get('denied', [])
            
            # Add to denied
            if permission not in deny_dict:
                deny_dict.append(permission)
            
            # Remove from granted if present
            if permission in grant_dict:
                grant_dict.remove(permission)
            
            # Save
            user.custom_permissions = json.dumps({
                'granted': grant_dict,
                'denied': deny_dict,
            })
            await db.commit()
            
            logger.info(f"Denied permission {permission} to admin {admin_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to deny permission: {e}")
            return False
    
    async def has_permission(
        self,
        db: AsyncSession,
        admin_id: str,
        permission: str,
    ) -> bool:
        """Check if admin has a specific permission"""
        from models import User
        
        try:
            stmt = select(User).where(User.id == admin_id)
            user = await db.scalar(stmt)
            
            if not user or not user.is_admin:
                return False
            
            # Check explicit denials first
            current_perms = json.loads(user.custom_permissions or '{}')
            deny_dict = current_perms.get('denied', [])
            
            if permission in deny_dict:
                return False
            
            # Check explicit grants
            grant_dict = current_perms.get('granted', [])
            if permission in grant_dict:
                return True
            
            # Fall back to role-based permissions
            role = user.admin_role
            role_perms = RolePermissionDefaults.ROLE_DEFAULTS.get(role, [])
            
            return permission in role_perms
        
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return False
    
    async def get_admin_permissions(
        self,
        db: AsyncSession,
        admin_id: str,
    ) -> List[str]:
        """Get all permissions for an admin"""
        from models import User
        
        try:
            stmt = select(User).where(User.id == admin_id)
            user = await db.scalar(stmt)
            
            if not user or not user.is_admin:
                return []
            
            # Get role-based permissions
            role = user.admin_role
            perms: Set[str] = set(RolePermissionDefaults.ROLE_DEFAULTS.get(role, []))
            
            # Apply custom permissions
            current_perms = json.loads(user.custom_permissions or '{}')
            grant_dict = current_perms.get('granted', [])
            deny_dict = current_perms.get('denied', [])
            
            # Add explicit grants
            perms.update(grant_dict)
            
            # Remove explicit denials
            perms.difference_update(deny_dict)
            
            return sorted(list(perms))
        
        except Exception as e:
            logger.error(f"Failed to get permissions: {e}")
            return []
    
    async def reset_to_role_defaults(
        self,
        db: AsyncSession,
        admin_id: str,
    ) -> bool:
        """Reset admin permissions to role defaults"""
        from models import User
        
        try:
            stmt = select(User).where(User.id == admin_id)
            user = await db.scalar(stmt)
            
            if not user or not user.is_admin:
                return False
            
            user.custom_permissions = '{}'
            await db.commit()
            
            logger.info(f"Reset permissions for admin {admin_id} to role defaults")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reset permissions: {e}")
            return False


# Singleton instance
_permission_service: Optional[GranularPermissionService] = None


def get_permission_service() -> GranularPermissionService:
    """Get or create permission service"""
    global _permission_service
    if _permission_service is None:
        _permission_service = GranularPermissionService()
    return _permission_service
