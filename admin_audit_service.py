"""
Admin Audit Service
Provides centralized audit logging for all admin actions.

RULE: Every admin action must create an immutable AuditLog record.
- Admin ID: who performed the action
- User ID: who the action was performed on
- Account ID: which account was affected
- Action type: what was done (fund, freeze, reset_password, etc.)
- Timestamp: when it happened
- Reason: why it happened (admin notes)
- Status: success/failed/pending

This ensures complete traceability and accountability for admin authority.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User as DBUser, Account as DBAccount, AuditLog as DBAuditLog
from auth_utils import get_password_hash

log = logging.getLogger(__name__)


class AdminAuditService:
    """Service for logging and retrieving admin audit trails"""
    
    @staticmethod
    async def log_admin_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        action_type: str,
        account_id: Optional[int] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        status_message: Optional[str] = None
    ) -> DBAuditLog:
        """
        Create an audit log entry for an admin action.
        
        Args:
            db: Database session
            admin_id: ID of admin performing the action
            user_id: ID of user the action is performed on
            action_type: Type of action (fund, freeze, reset_password, approve_kyc, etc.)
            account_id: ID of account affected (optional but recommended)
            reason: Why the action was performed (admin notes)
            details: Additional details as dict (will be stringified to JSON)
            status: "success", "failed", or "pending"
            status_message: Human-readable status message
            
        Returns:
            Created AuditLog record
        """
        try:
            # Verify admin exists and is admin
            admin_result = await db.execute(
                select(DBUser).filter(DBUser.id == admin_id)
            )
            admin = admin_result.scalars().first()
            if not admin:
                raise ValueError(f"Admin user {admin_id} not found")
            if not admin.is_admin:
                raise ValueError(f"User {admin_id} is not an admin")
            
            # Verify target user exists
            user_result = await db.execute(
                select(DBUser).filter(DBUser.id == user_id)
            )
            user = user_result.scalars().first()
            if not user:
                raise ValueError(f"Target user {user_id} not found")
            
            # Verify account exists if provided
            if account_id:
                account_result = await db.execute(
                    select(DBAccount).filter(DBAccount.id == account_id)
                )
                account = account_result.scalars().first()
                if not account:
                    raise ValueError(f"Account {account_id} not found")
                # RULE: Account must belong to the target user
                if account.owner_id != user_id:
                    raise ValueError(f"Account {account_id} does not belong to user {user_id}")
            
            # Stringify details if provided
            details_str = json.dumps(details) if details else None
            
            # Create audit log entry
            audit_log = DBAuditLog(
                admin_id=admin_id,
                user_id=user_id,
                account_id=account_id,
                action_type=action_type,
                reason=reason,
                details=details_str,
                status=status,
                status_message=status_message
            )
            
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)
            
            log.info(
                f"AUDIT: Admin {admin_id} performed {action_type} on User {user_id} "
                f"(Account {account_id}). Status: {status}"
            )
            
            return audit_log
            
        except Exception as e:
            await db.rollback()
            log.error(f"Failed to create audit log: {str(e)}")
            raise
    
    @staticmethod
    async def log_fund_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        account_id: int,
        amount: float,
        fund_source: str,
        notes: Optional[str] = None
    ) -> DBAuditLog:
        """
        Log a funding action by admin.
        
        Args:
            db: Database session
            admin_id: ID of admin performing the fund
            user_id: ID of user being funded
            account_id: ID of account being funded
            amount: Amount funded
            fund_source: Where the money came from
            notes: Optional admin notes
        """
        details = {
            "amount": float(amount),
            "fund_source": fund_source,
            "timestamp": datetime.now().isoformat()
        }
        
        reason = notes or f"Admin funding from {fund_source}"
        
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            account_id=account_id,
            action_type="fund",
            reason=reason,
            details=details
        )
    
    @staticmethod
    async def log_password_reset_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """
        Log a password reset action by admin.
        
        RULE: Admin does NOT see the new password, only that a reset was initiated.
        User must change password on next login.
        
        Args:
            db: Database session
            admin_id: ID of admin performing the reset
            user_id: ID of user whose password is being reset
            reason: Why the password is being reset
        """
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            action_type="reset_password",
            reason=reason or "Admin initiated password reset",
            details={"force_change_on_next_login": True}
        )
    
    @staticmethod
    async def log_freeze_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        account_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log account freeze action by admin."""
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            account_id=account_id,
            action_type="freeze",
            reason=reason or "Admin froze account"
        )
    
    @staticmethod
    async def log_unfreeze_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        account_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log account unfreeze action by admin."""
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            account_id=account_id,
            action_type="unfreeze",
            reason=reason or "Admin unfroze account"
        )
    
    @staticmethod
    async def log_kyc_approval_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log KYC approval action by admin."""
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            action_type="approve_kyc",
            reason=reason or "Admin approved KYC"
        )
    
    @staticmethod
    async def log_kyc_rejection_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log KYC rejection action by admin."""
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            action_type="reject_kyc",
            reason=reason or "Admin rejected KYC"
        )
    
    @staticmethod
    async def log_reverse_transaction_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        account_id: int,
        transaction_id: int,
        amount: float,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log transaction reversal action by admin."""
        details = {
            "transaction_id": transaction_id,
            "amount_reversed": float(amount)
        }
        
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            account_id=account_id,
            action_type="reverse_transaction",
            reason=reason or "Admin reversed transaction",
            details=details
        )
    
    @staticmethod
    async def log_create_user_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log user creation action by admin."""
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            action_type="create_user",
            reason=reason or "Admin created user"
        )
    
    @staticmethod
    async def log_delete_user_action(
        db: AsyncSession,
        admin_id: int,
        user_id: int,
        reason: Optional[str] = None
    ) -> DBAuditLog:
        """Log user deletion action by admin."""
        return await AdminAuditService.log_admin_action(
            db=db,
            admin_id=admin_id,
            user_id=user_id,
            action_type="delete_user",
            reason=reason or "Admin deleted user"
        )
    
    @staticmethod
    async def get_audit_logs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        admin_id: Optional[int] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> list:
        """
        Retrieve audit logs with optional filtering.
        
        Args:
            db: Database session
            user_id: Filter by target user ID
            admin_id: Filter by admin ID
            action_type: Filter by action type
            limit: Maximum results to return
            skip: Number of results to skip (for pagination)
            
        Returns:
            List of audit log records
        """
        query = select(DBAuditLog)
        
        if user_id:
            query = query.filter(DBAuditLog.user_id == user_id)
        if admin_id:
            query = query.filter(DBAuditLog.admin_id == admin_id)
        if action_type:
            query = query.filter(DBAuditLog.action_type == action_type)
        
        # Order by most recent first
        query = query.order_by(DBAuditLog.created_at.desc())
        query = query.limit(limit).offset(skip)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_user_audit_logs(
        db: AsyncSession,
        user_id: int,
        limit: int = 100,
        skip: int = 0
    ) -> list:
        """Get all audit logs for a specific user."""
        return await AdminAuditService.get_audit_logs(
            db=db,
            user_id=user_id,
            limit=limit,
            skip=skip
        )
    
    @staticmethod
    async def get_admin_audit_logs(
        db: AsyncSession,
        admin_id: int,
        limit: int = 100,
        skip: int = 0
    ) -> list:
        """Get all audit logs for a specific admin."""
        return await AdminAuditService.get_audit_logs(
            db=db,
            admin_id=admin_id,
            limit=limit,
            skip=skip
        )


# Singleton instance
admin_audit_service = AdminAuditService()
