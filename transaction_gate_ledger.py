"""
Transaction Gate: Enforce User Linkage & Ledger Creation
=========================================================

Before ANY transaction becomes "completed", this gate ensures:

1. Transaction has valid user_id (never N/A, never NULL)
2. Transaction has valid reference_number (for audit)
3. Transaction type is valid and recognized
4. Ledger entries are created (double-entry accounting)
5. Account balance is synchronized from ledger

This prevents cosmetic accounting where transactions exist but balances stay at $0.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple

from models import (
    Transaction as DBTransaction,
    User as DBUser,
    Account as DBAccount
)
from ledger_service import LedgerService


class TransactionGate:
    """
    Gate for controlling transaction flow through system.
    
    Every transaction must pass through this gate to be "completed".
    Ensures double-entry ledger entries are created.
    """
    
    # Valid transaction types
    VALID_TYPES = {
        "deposit",
        "withdrawal",
        "transfer",
        "fund_transfer",
        "admin_fund",
        "bulk_fund",
        "interest",
        "fee",
        "reversal"
    }
    
    @staticmethod
    async def validate_transaction_linkage(transaction: DBTransaction) -> Tuple[bool, str]:
        """
        Validate that transaction has required fields.
        
        RULE 1: No N/A values - all transactions must have user linkage
        
        Args:
            transaction: Transaction to validate
            
        Returns:
            (is_valid, reason)
        """
        errors = []
        
        # Check user_id
        if not transaction.user_id or transaction.user_id <= 0:
            errors.append("user_id is missing or invalid (N/A value)")
        
        # Check transaction type
        if not transaction.transaction_type:
            errors.append("transaction_type is missing")
        elif transaction.transaction_type.lower() not in TransactionGate.VALID_TYPES:
            errors.append(f"transaction_type '{transaction.transaction_type}' is not valid. Valid: {TransactionGate.VALID_TYPES}")
        
        # Check amount
        if not transaction.amount or transaction.amount <= 0:
            errors.append(f"amount is missing or invalid: {transaction.amount}")
        
        # Check reference (required for audit trail)
        if not transaction.reference_number or transaction.reference_number.strip() == "":
            errors.append("reference_number is missing (required for audit trail)")
        
        if errors:
            return False, "; ".join(errors)
        
        return True, "OK"
    
    @staticmethod
    async def complete_transaction(
        db: AsyncSession,
        transaction: DBTransaction,
        ledger_callback=None
    ) -> Tuple[bool, str]:
        """
        Complete a transaction and create ledger entries.
        
        RULE 2: Completing transaction requires double-entry ledger creation.
        
        Args:
            db: Database session
            transaction: Transaction to complete
            ledger_callback: Optional callback to create custom ledger entries
            
        Returns:
            (success: bool, message: str)
        """
        try:
            # 1. Validate linkage first
            is_valid, reason = await TransactionGate.validate_transaction_linkage(transaction)
            if not is_valid:
                return False, f"Transaction validation failed: {reason}"
            
            # 2. Verify user exists
            user_result = await db.execute(
                select(DBUser).where(DBUser.id == transaction.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return False, f"User {transaction.user_id} not found"
            
            # 3. Verify account exists
            if not transaction.account_id:
                return False, "Transaction has no account_id (money must have a destination)"
            
            account_result = await db.execute(
                select(DBAccount).where(DBAccount.id == transaction.account_id)
            )
            account = account_result.scalar_one_or_none()
            if not account:
                return False, f"Account {transaction.account_id} not found"
            
            # 4. Update transaction status to completed
            transaction.status = "completed"
            db.add(transaction)
            await db.flush()
            
            # 5. Create ledger entries based on transaction type
            if ledger_callback:
                # Use custom callback (for complex transactions like transfers)
                await ledger_callback(db, transaction)
            else:
                # Default: create simple credit entry to user
                await LedgerService.create_admin_funding(
                    db=db,
                    transaction=transaction,
                    to_user_id=transaction.user_id,
                    amount=Decimal(str(transaction.amount)),
                    description=transaction.description or f"{transaction.transaction_type.upper()}",
                    reference_number=transaction.reference_number
                )
            
            # 6. Sync account balance from ledger
            new_balance = await LedgerService.get_user_balance(db, transaction.user_id)
            account.balance = float(new_balance)
            db.add(account)
            await db.flush()
            
            # 7. Verify ledger integrity
            reconciliation = await LedgerService.reconcile_ledger(db)
            if not reconciliation["is_balanced"]:
                await db.rollback()
                return False, f"Ledger reconciliation failed: {reconciliation['errors']}"
            
            return True, "Transaction completed and ledger entries created"
            
        except Exception as e:
            await db.rollback()
            return False, f"Error completing transaction: {str(e)}"
    
    @staticmethod
    async def reject_transaction(
        db: AsyncSession,
        transaction: DBTransaction,
        reason: str
    ) -> Tuple[bool, str]:
        """
        Reject a transaction (set to failed).
        
        No ledger entries are created for rejected transactions.
        
        Args:
            db: Database session
            transaction: Transaction to reject
            reason: Why it was rejected
            
        Returns:
            (success, message)
        """
        try:
            transaction.status = "failed"
            transaction.description = f"{transaction.description} [REJECTED: {reason}]"
            db.add(transaction)
            await db.commit()
            
            return True, f"Transaction rejected: {reason}"
        except Exception as e:
            await db.rollback()
            return False, f"Error rejecting transaction: {str(e)}"
    
    @staticmethod
    async def block_transaction(
        db: AsyncSession,
        transaction: DBTransaction,
        reason: str
    ) -> Tuple[bool, str]:
        """
        Block a transaction (held funds, pending review).
        
        Blocked transactions show held funds (visible to admin, not user).
        No ledger entries until unblocked or rejected.
        
        Args:
            db: Database session
            transaction: Transaction to block
            reason: Why it's blocked
            
        Returns:
            (success, message)
        """
        try:
            transaction.status = "blocked"
            transaction.description = f"{transaction.description} [BLOCKED: {reason}]"
            db.add(transaction)
            await db.commit()
            
            return True, f"Transaction blocked: {reason}"
        except Exception as e:
            await db.rollback()
            return False, f"Error blocking transaction: {str(e)}"
    
    @staticmethod
    async def unblock_transaction(
        db: AsyncSession,
        transaction: DBTransaction
    ) -> Tuple[bool, str]:
        """
        Unblock a transaction (convert from blocked to completed).
        
        Creates ledger entries if unblocking.
        
        Args:
            db: Database session
            transaction: Transaction to unblock
            
        Returns:
            (success, message)
        """
        try:
            if transaction.status != "blocked":
                return False, f"Transaction is not blocked (status: {transaction.status})"
            
            # Complete the transaction (creates ledger entries)
            return await TransactionGate.complete_transaction(db, transaction)
            
        except Exception as e:
            await db.rollback()
            return False, f"Error unblocking transaction: {str(e)}"
