"""
Account ID Enforcement Module

Enforces the core principle:
- Account ID → unique, immutable
- User ID → owner (FK)
- All user accounts (except admin) must be bound to a specific user

This module validates that:
1. Every transaction targets an account owned by the user
2. Every operation validates user_id → account_id relationship
3. Admin accounts are exempt from user binding enforcement
"""

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from models import User as DBUser, Account as DBAccount, Transaction as DBTransaction

class AccountIDEnforcement:
    """Validates and enforces Account ID → User ID relationships"""
    
    @staticmethod
    async def validate_account_ownership(
        db: AsyncSession,
        user_id: int,
        account_id: int
    ) -> Tuple[bool, str]:
        """
        Validate that an account is owned by a user.
        
        Args:
            db: Database session
            user_id: User ID claiming ownership
            account_id: Account ID to validate
            
        Returns:
            (is_valid, reason)
            - (True, "") if valid
            - (False, reason) if invalid
        """
        # Verify account exists
        account_result = await db.execute(
            select(DBAccount).filter(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            return False, f"Account {account_id} not found"
        
        # Skip admin accounts (they don't have user binding)
        if account.is_admin_account:
            return False, f"Account {account_id} is an admin account, cannot be used by regular users"
        
        # Verify user exists
        user_result = await db.execute(
            select(DBUser).filter(DBUser.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return False, f"User {user_id} not found"
        
        # Verify account belongs to user
        if account.owner_id != user_id:
            return False, f"Account {account_id} does not belong to user {user_id} (owner_id={account.owner_id})"
        
        # Verify account is active
        if account.status != "active":
            return False, f"Account {account_id} is {account.status}, cannot perform operations"
        
        return True, ""
    
    @staticmethod
    async def get_user_account(
        db: AsyncSession,
        user_id: int,
        account_id: Optional[int] = None
    ) -> Optional[DBAccount]:
        """
        Get a user's account (validates ownership).
        
        If account_id not provided, returns user's primary account.
        If account_id provided, validates it belongs to user.
        
        Args:
            db: Database session
            user_id: User ID
            account_id: Optional account ID (must belong to user)
            
        Returns:
            Account if valid, None otherwise
        """
        if account_id:
            # Validate specific account
            is_valid, reason = await AccountIDEnforcement.validate_account_ownership(
                db, user_id, account_id
            )
            if not is_valid:
                return None
            
            result = await db.execute(
                select(DBAccount).filter(DBAccount.id == account_id)
            )
            return result.scalar_one_or_none()
        else:
            # Get primary account (first created)
            result = await db.execute(
                select(DBAccount)
                .filter(and_(
                    DBAccount.owner_id == user_id,
                    DBAccount.is_admin_account == False
                ))
                .order_by(DBAccount.created_at)
                .limit(1)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def validate_transaction_account_binding(
        db: AsyncSession,
        user_id: int,
        account_id: int,
        transaction_amount: float
    ) -> Tuple[bool, str]:
        """
        Validate that a transaction can proceed on this account.
        
        Checks:
        1. Account belongs to user
        2. Account is active
        3. Account has sufficient balance (if withdrawal)
        4. User KYC status allows transaction
        
        Args:
            db: Database session
            user_id: User ID performing transaction
            account_id: Account to use
            transaction_amount: Amount (positive for credit, negative for debit)
            
        Returns:
            (is_valid, reason)
        """
        # Validate account ownership
        is_valid, reason = await AccountIDEnforcement.validate_account_ownership(
            db, user_id, account_id
        )
        if not is_valid:
            return False, reason
        
        # Get account and user for additional checks
        account_result = await db.execute(
            select(DBAccount).filter(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        
        user_result = await db.execute(
            select(DBUser).filter(DBUser.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        # Check KYC status
        if user.kyc_status != "approved":
            return False, f"User KYC status is {user.kyc_status}, transactions require 'approved' status"
        
        # Check sufficient balance for withdrawals
        if transaction_amount < 0:  # Withdrawal
            if account.balance + transaction_amount < 0:
                return False, f"Insufficient balance. Have: {account.balance}, Need: {-transaction_amount}"
        
        return True, ""
    
    @staticmethod
    async def get_user_accounts(
        db: AsyncSession,
        user_id: int,
        exclude_admin: bool = True
    ) -> list:
        """
        Get all accounts for a user.
        
        Args:
            db: Database session
            user_id: User ID
            exclude_admin: If True, exclude admin accounts
            
        Returns:
            List of Account objects
        """
        query = select(DBAccount).filter(DBAccount.owner_id == user_id)
        
        if exclude_admin:
            query = query.filter(DBAccount.is_admin_account == False)
        
        query = query.order_by(DBAccount.created_at)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_account_user(
        db: AsyncSession,
        account_id: int
    ) -> Optional[DBUser]:
        """
        Get the user who owns an account (if not admin account).
        
        Args:
            db: Database session
            account_id: Account ID
            
        Returns:
            User object if account is user-bound, None otherwise
        """
        account_result = await db.execute(
            select(DBAccount).filter(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        
        if not account or account.is_admin_account or not account.owner_id:
            return None
        
        user_result = await db.execute(
            select(DBUser).filter(DBUser.id == account.owner_id)
        )
        return user_result.scalar_one_or_none()


# Singleton instance for use throughout application
account_id_enforcement = AccountIDEnforcement()
