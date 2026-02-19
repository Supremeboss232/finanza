"""
Transaction Validation Service

Enforces all validation rules at API layer before transaction creation:
1. Amount must be positive
2. User must exist
3. Account must exist
4. KYC must be approved for transaction completion
5. For transfers: both parties must have accounts + sufficient balance

This service complements TransactionGate by validating at creation time.
"""

from decimal import Decimal
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from models import User, Account, Transaction
from balance_service_ledger import BalanceServiceLedger
from account_id_enforcement import account_id_enforcement


class TransactionValidator:
    """Validates transaction requests before creation"""

    @staticmethod
    async def validate_deposit(
        db: AsyncSession,
        user_id: int,
        amount: float,
        account_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validate a deposit request.
        
        Args:
            db: Database session
            user_id: User making the deposit
            amount: Deposit amount
            account_id: Account to deposit into (optional if user has default)
            
        Returns:
            (is_valid: bool, reason: str)
            - (True, "OK") if all checks pass
            - (False, reason) if validation fails
        """
        # 1. Check amount is positive
        if not amount or amount <= 0:
            return False, f"Deposit amount must be positive. Got: {amount}"

        # 2. Check user exists and is active
        user = await db.get(User, user_id)
        if not user:
            return False, f"User {user_id} not found"
        if not user.is_active:
            return False, f"User account is inactive"

        # 3. Check account exists (RULE 1: No account, no money)
        if account_id:
            account = await db.get(Account, account_id)
        else:
            # Try to get user's primary account
            result = await db.execute(
                select(Account).where(
                    and_(
                        Account.user_id == user_id,
                        Account.is_default == True
                    )
                )
            )
            account = result.scalar_one_or_none()

        if not account:
            return False, f"User has no account. Cannot deposit without account (RULE 1)"

        if account.user_id != user_id:
            return False, f"Account does not belong to user"

        if not account.is_active:
            return False, f"Account is not active"

        # 4. Check KYC status (RULE 2: No KYC, no completed transactions)
        # Note: Deposit will be created with status based on KYC at gate time
        # But we validate KYC is in valid state (not rejected)
        if user.kyc_status == "rejected":
            return False, f"User KYC is rejected. Contact support to resubmit."

        return True, "OK"

    @staticmethod
    async def validate_transfer(
        db: AsyncSession,
        sender_id: int,
        recipient_id: int,
        amount: float
    ) -> Tuple[bool, str]:
        """
        Validate a transfer request.
        
        Args:
            db: Database session
            sender_id: User sending money
            recipient_id: User receiving money
            amount: Transfer amount
            
        Returns:
            (is_valid: bool, reason: str)
        """
        # 1. Check amount is positive
        if not amount or amount <= 0:
            return False, f"Transfer amount must be positive. Got: {amount}"

        # 2. Check sender exists and is active
        sender = await db.get(User, sender_id)
        if not sender:
            return False, f"Sender user {sender_id} not found"
        if not sender.is_active:
            return False, f"Sender account is inactive"

        # 3. Check recipient exists and is active
        recipient = await db.get(User, recipient_id)
        if not recipient:
            return False, f"Recipient user {recipient_id} not found"
        if not recipient.is_active:
            return False, f"Recipient account is inactive"

        # 4. Check both have accounts (RULE 1)
        sender_result = await db.execute(
            select(Account).where(Account.user_id == sender_id)
        )
        sender_account = sender_result.scalar_one_or_none()
        if not sender_account:
            return False, f"Sender has no account. Cannot transfer without account (RULE 1)"

        # 🔧 ENFORCEMENT: Validate sender account ownership
        is_valid, reason = await account_id_enforcement.validate_account_ownership(
            db=db, user_id=sender_id, account_id=sender_account.id
        )
        if not is_valid:
            return False, f"Sender account validation failed: {reason}"

        recipient_result = await db.execute(
            select(Account).where(Account.user_id == recipient_id)
        )
        recipient_account = recipient_result.scalar_one_or_none()
        if not recipient_account:
            return False, f"Recipient has no account. Cannot transfer to account that doesn't exist (RULE 1)"

        # 🔧 ENFORCEMENT: Validate recipient account ownership
        is_valid, reason = await account_id_enforcement.validate_account_ownership(
            db=db, user_id=recipient_id, account_id=recipient_account.id
        )
        if not is_valid:
            return False, f"Recipient account validation failed: {reason}"

        # 5. Check sender has sufficient balance (RULE 3: derived from ledger only)
        # ISSUE #1 FIX: Use BalanceServiceLedger instead of BalanceService
        sender_balance = await BalanceServiceLedger.get_user_balance(db, sender_id)
        if sender_balance < amount:
            return False, f"Insufficient balance. Have: {sender_balance}, Need: {amount}"

        # 6. Check both have valid KYC status (RULE 2)
        if sender.kyc_status == "rejected":
            return False, f"Sender KYC is rejected. Contact support."
        if recipient.kyc_status == "rejected":
            return False, f"Recipient KYC is rejected. Contact support."

        return True, "OK"

    @staticmethod
    async def validate_withdrawal(
        db: AsyncSession,
        user_id: int,
        amount: float,
        account_id: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Validate a withdrawal request.
        
        Args:
            db: Database session
            user_id: User withdrawing
            amount: Withdrawal amount
            account_id: Account to withdraw from (optional if user has default)
            
        Returns:
            (is_valid: bool, reason: str)
        """
        # 1. Check amount is positive
        if not amount or amount <= 0:
            return False, f"Withdrawal amount must be positive. Got: {amount}"

        # 2. Check user exists and is active
        user = await db.get(User, user_id)
        if not user:
            return False, f"User {user_id} not found"
        if not user.is_active:
            return False, f"User account is inactive"

        # 3. Check account exists
        if account_id:
            account = await db.get(Account, account_id)
        else:
            result = await db.execute(
                select(Account).where(
                    and_(
                        Account.user_id == user_id,
                        Account.is_default == True
                    )
                )
            )
            account = result.scalar_one_or_none()

        if not account:
            return False, f"User has no account for withdrawal"

        if account.user_id != user_id:
            return False, f"Account does not belong to user"

        if not account.is_active:
            return False, f"Account is not active"

        # 4. Check sufficient balance (RULE 3: derived from ledger)
        # ISSUE #1 FIX: Use BalanceServiceLedger instead of BalanceService
        balance = await BalanceServiceLedger.get_user_balance(db, user_id)
        if balance < amount:
            return False, f"Insufficient balance. Have: {balance}, Need: {amount}"

        # 5. Check KYC status is not rejected
        if user.kyc_status == "rejected":
            return False, f"User KYC is rejected. Cannot withdraw."

        return True, "OK"
