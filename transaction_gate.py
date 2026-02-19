"""
Transaction Gate Service
========================

Enforces the 3 critical rules:

RULE 1: No account, no money
- Deposits/transfers/balances only if account exists

RULE 2: No KYC, no completed transactions
- Transactions initiated but held/blocked if KYC not approved
- Only completed transactions affect balance

RULE 3: Balances derived, never stored
- Balance = sum(completed transactions only)
- Scoped to user_id + account_id

This service is the gatekeeper for all financial operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime

from models import (
    User as DBUser,
    Account as DBAccount,
    Transaction as DBTransaction,
    KYCInfo as DBKYCInfo
)
from balance_service_ledger import BalanceServiceLedger

# Transaction Status States
TRANSACTION_STATES = {
    "pending": "Created but awaiting processing",
    "blocked": "Held due to missing account or KYC",
    "completed": "Approved and affects balance",
    "failed": "Failed validation",
    "cancelled": "User/admin cancelled"
}

# Only 'completed' transactions affect balance
BALANCE_AFFECTING_STATES = ["completed"]

# These states are held (visible to admin as held funds)
HELD_STATES = ["pending", "blocked"]


class TransactionGate:
    """Service to validate and gate transactions"""
    
    @staticmethod
    async def validate_deposit(
        db: AsyncSession,
        user_id: int,
        amount: float,
        account_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate if a deposit can be completed.
        
        Returns: (can_complete, status, reason)
        - can_complete: bool - True if should be 'completed', False if 'blocked'/'pending'
        - status: str - 'completed', 'blocked', or 'pending'
        - reason: str - Why it's this status (if not completed)
        """
        
        # Get user
        user_result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            return False, "failed", "User not found"
        
        # Check amount
        if amount <= 0:
            return False, "failed", "Amount must be positive"
        
        # RULE 1: Check if account exists (or will be created)
        if account_id:
            account_result = await db.execute(
                select(DBAccount).where(DBAccount.id == account_id)
            )
            account = account_result.scalar_one_or_none()
            if not account:
                return False, "blocked", "Account does not exist"
        else:
            # No account specified - need to check if user has one
            account_result = await db.execute(
                select(DBAccount).where(DBAccount.owner_id == user_id)
            )
            account = account_result.scalar_one_or_none()
            if not account:
                return False, "blocked", "User has no account (create account first)"
        
        # RULE 2: Check KYC status
        if user.kyc_status != "approved":
            return False, "blocked", f"KYC not approved (status: {user.kyc_status}). Deposit will be held."
        
        # All checks passed - can complete
        return True, "completed", None
    
    @staticmethod
    async def validate_transfer(
        db: AsyncSession,
        sender_id: int,
        recipient_id: int,
        amount: float,
        sender_account_id: Optional[int] = None,
        recipient_account_id: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Validate if a transfer can be completed.
        
        Returns: (can_complete, status, reason)
        """
        
        # Get sender
        sender_result = await db.execute(select(DBUser).where(DBUser.id == sender_id))
        sender = sender_result.scalar_one_or_none()
        
        if not sender:
            return False, "failed", "Sender not found"
        
        # Get recipient
        recipient_result = await db.execute(select(DBUser).where(DBUser.id == recipient_id))
        recipient = recipient_result.scalar_one_or_none()
        
        if not recipient:
            return False, "failed", "Recipient not found"
        
        # Check amount
        if amount <= 0:
            return False, "failed", "Amount must be positive"
        
        # RULE 1: Both must have accounts
        sender_account_result = await db.execute(
            select(DBAccount).where(DBAccount.owner_id == sender_id)
        )
        sender_account = sender_account_result.scalar_one_or_none()
        
        if not sender_account:
            return False, "blocked", "Sender has no account"
        
        recipient_account_result = await db.execute(
            select(DBAccount).where(DBAccount.owner_id == recipient_id)
        )
        recipient_account = recipient_account_result.scalar_one_or_none()
        
        if not recipient_account:
            return False, "blocked", "Recipient has no account"
        
        # Check sender has sufficient balance
        sender_balance = await TransactionGate.get_user_completed_balance(db, sender_id)
        if sender_balance < amount:
            return False, "failed", f"Insufficient balance. Have ${sender_balance:.2f}, need ${amount:.2f}"
        
        # RULE 2: Both must have KYC approved
        if sender.kyc_status != "approved":
            return False, "blocked", f"Sender KYC not approved (status: {sender.kyc_status})"
        
        if recipient.kyc_status != "approved":
            return False, "blocked", f"Recipient KYC not approved (status: {recipient.kyc_status})"
        
        # All checks passed
        return True, "completed", None
    
    @staticmethod
    async def get_user_completed_balance(db: AsyncSession, user_id: int) -> float:
        """
        Get user's balance from LEDGER (single source of truth).
        
        ISSUE #1 FIX: Use BalanceServiceLedger instead of Transaction table
        
        RULE 3: Balance is derived, never stored.
        Balance = sum(ledger credits - debits)
        """
        return await BalanceServiceLedger.get_user_balance(db, user_id)
    
    @staticmethod
    async def get_account_completed_balance(db: AsyncSession, account_id: int) -> float:
        """
        Get account balance from COMPLETED transactions only.
        
        RULE 3: Balance is derived, never stored.
        """
        result = await db.execute(
            select(
                __import__('sqlalchemy').func.sum(DBTransaction.amount)
            ).where(
                and_(
                    DBTransaction.account_id == account_id,
                    DBTransaction.status == "completed"
                )
            )
        )
        balance = result.scalar() or 0
        return float(balance)
    
    @staticmethod
    async def get_held_funds(db: AsyncSession, user_id: int) -> float:
        """
        Get user's held funds (pending + blocked transactions).
        Visible to admin, not in user's balance.
        """
        result = await db.execute(
            select(
                __import__('sqlalchemy').func.sum(DBTransaction.amount)
            ).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.status.in_(HELD_STATES)
                )
            )
        )
        held = result.scalar() or 0
        return float(held)
    
    @staticmethod
    async def get_transaction_status_info(db: AsyncSession, user_id: int) -> Dict:
        """
        Get complete transaction status breakdown for a user.
        """
        # Completed balance
        completed = await TransactionGate.get_user_completed_balance(db, user_id)
        
        # Held funds
        held = await TransactionGate.get_held_funds(db, user_id)
        
        # Get user KYC status
        user_result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        user = user_result.scalar_one_or_none()
        
        # Get account status
        account_result = await db.execute(
            select(DBAccount).where(DBAccount.owner_id == user_id)
        )
        account = account_result.scalar_one_or_none()
        
        return {
            "user_id": user_id,
            "kyc_status": user.kyc_status if user else "unknown",
            "account_exists": account is not None,
            "account_id": account.id if account else None,
            "balance": completed,
            "held_funds": held,
            "total_value": completed + held,
            "can_transact": user and user.kyc_status == "approved" and account is not None
        }
    
    @staticmethod
    async def can_complete_transaction(db: AsyncSession, user_id: int) -> Tuple[bool, str]:
        """
        Check if user can have completed transactions.
        
        Returns: (can_complete, reason)
        """
        # Get user
        user_result = await db.execute(select(DBUser).where(DBUser.id == user_id))
        user = user_result.scalar_one_or_none()
        
        if not user:
            return False, "User not found"
        
        # Check KYC
        if user.kyc_status != "approved":
            return False, f"KYC not approved: {user.kyc_status}"
        
        # Check account
        account_result = await db.execute(
            select(DBAccount).where(DBAccount.owner_id == user_id)
        )
        account = account_result.scalar_one_or_none()
        
        if not account:
            return False, "No account"
        
        return True, "OK"
