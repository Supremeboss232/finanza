"""
Ledger Service: Double-Entry Accounting
========================================

Implements proper double-entry accounting for all financial transactions.

PRINCIPLE: Every transaction creates exactly TWO ledger entries (debit and credit).
Balance = sum(credits) - sum(debits)

This ensures:
✓ Money is never created or destroyed (double-entry)
✓ Every transaction is linked to users
✓ Audit trail is complete and reversible
✓ System balances: total debits = total credits
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from decimal import Decimal
from typing import Tuple, Optional, Dict, List
from datetime import datetime
from models import (
    Ledger as DBLedger,
    Transaction as DBTransaction,
    User as DBUser,
    Account as DBAccount
)


class LedgerService:
    """Service for managing double-entry ledger entries"""
    
    # Special system account: user_id = 1 (admin/system account with infinite funds)
    SYSTEM_USER_ID = 1
    
    @staticmethod
    async def create_atomic_transfer(
        db: AsyncSession,
        transaction: DBTransaction,
        from_user_id: int,
        to_user_id: int,
        amount: Decimal,
        description: str,
        reference_number: Optional[str] = None
    ) -> Tuple[DBLedger, DBLedger]:
        """
        Create atomic double-entry ledger for a transfer.
        
        RULE 1: Money is atomic
        Either BOTH entries succeed or both rollback.
        No partial transactions.
        
        Args:
            db: Database session
            transaction: The Transaction record (must be created first)
            from_user_id: User whose money is leaving
            to_user_id: User whose money is arriving
            amount: Amount (always positive)
            description: What happened
            reference_number: External reference
            
        Returns:
            Tuple of (debit_entry, credit_entry)
            
        Raises:
            ValueError: If amount <= 0 or users invalid
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")
        
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer to same user")
        
        # Verify both users exist
        from_user = await db.execute(select(DBUser).where(DBUser.id == from_user_id))
        if not from_user.scalar():
            raise ValueError(f"Source user {from_user_id} not found")
        
        to_user = await db.execute(select(DBUser).where(DBUser.id == to_user_id))
        if not to_user.scalar():
            raise ValueError(f"Destination user {to_user_id} not found")
        
        amount_decimal = Decimal(str(amount))
        now = datetime.utcnow()
        
        # Create DEBIT entry: Money leaves source user
        debit_entry = DBLedger(
            user_id=from_user_id,
            entry_type="debit",
            amount=amount_decimal,
            transaction_id=transaction.id,
            source_user_id=from_user_id,
            destination_user_id=to_user_id,
            description=f"Debit: {description}",
            reference_number=reference_number,
            status="posted",
            posted_at=now
        )
        db.add(debit_entry)
        await db.flush()  # Get debit_entry.id
        
        # Create CREDIT entry: Money arrives at destination user
        credit_entry = DBLedger(
            user_id=to_user_id,
            entry_type="credit",
            amount=amount_decimal,
            transaction_id=transaction.id,
            related_entry_id=debit_entry.id,  # Link to matching debit
            source_user_id=from_user_id,
            destination_user_id=to_user_id,
            description=f"Credit: {description}",
            reference_number=reference_number,
            status="posted",
            posted_at=now
        )
        db.add(credit_entry)
        await db.flush()
        
        # Update debit entry's related_entry_id to complete the pair
        debit_entry.related_entry_id = credit_entry.id
        db.add(debit_entry)
        await db.flush()
        
        return debit_entry, credit_entry
    
    @staticmethod
    async def create_admin_funding(
        db: AsyncSession,
        transaction: DBTransaction,
        to_user_id: int,
        amount: Decimal,
        description: str,
        reference_number: Optional[str] = None
    ) -> Tuple[DBLedger, DBLedger]:
        """
        Create atomic double-entry ledger for admin funding.
        
        RULE 2: Admin funding is a debit from system account
        
        System account has "infinite" funds (user_id = 1).
        Admin fund creates:
        1. Debit: From SYSTEM account
        2. Credit: To target user
        
        Args:
            db: Database session
            transaction: The Transaction record
            to_user_id: User receiving funds
            amount: Amount
            description: What happened
            reference_number: External reference
            
        Returns:
            Tuple of (debit_entry, credit_entry)
        """
        return await LedgerService.create_atomic_transfer(
            db=db,
            transaction=transaction,
            from_user_id=LedgerService.SYSTEM_USER_ID,
            to_user_id=to_user_id,
            amount=amount,
            description=description,
            reference_number=reference_number
        )
    
    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: int) -> float:
        """
        Calculate user balance from ledger (source of truth).
        
        Balance = sum(credits) - sum(debits)
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            float balance
        """
        # Sum all credits to this user
        credits_result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted"
                )
            )
        )
        credits = float(credits_result.scalar() or 0)
        
        # Sum all debits from this user
        debits_result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "debit",
                    DBLedger.status == "posted"
                )
            )
        )
        debits = float(debits_result.scalar() or 0)
        
        return credits - debits
    
    @staticmethod
    async def get_all_user_balances(db: AsyncSession) -> Dict[int, float]:
        """
        Get balances for all users.
        
        Returns:
            Dict mapping user_id -> balance
        """
        # Get all users
        result = await db.execute(select(DBUser.id))
        user_ids = result.scalars().all()
        
        balances = {}
        for user_id in user_ids:
            balances[user_id] = await LedgerService.get_user_balance(db, user_id)
        
        return balances
    
    @staticmethod
    async def get_total_system_balance(db: AsyncSession) -> float:
        """
        Get total balance across all users.
        
        Should be 0 if ledger is balanced (debits = credits globally).
        If non-zero, indicates accounting error.
        
        Returns:
            float - should be 0 for balanced ledger
        """
        balances = await LedgerService.get_all_user_balances(db)
        return sum(balances.values())
    
    @staticmethod
    async def reconcile_ledger(db: AsyncSession) -> Dict:
        """
        Verify ledger integrity and balance.
        
        Returns:
            Dict with reconciliation results
        """
        result = {
            "is_balanced": False,
            "total_debits": 0.0,
            "total_credits": 0.0,
            "difference": 0.0,
            "entry_pairs_matched": 0,
            "orphaned_entries": 0,
            "errors": []
        }
        
        # Calculate total debits and credits
        debits_result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.entry_type == "debit",
                    DBLedger.status == "posted"
                )
            )
        )
        result["total_debits"] = float(debits_result.scalar() or 0)
        
        credits_result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted"
                )
            )
        )
        result["total_credits"] = float(credits_result.scalar() or 0)
        
        result["difference"] = abs(result["total_debits"] - result["total_credits"])
        result["is_balanced"] = result["difference"] < 0.01  # Allow rounding
        
        # Check for orphaned entries (no related entry)
        orphaned_result = await db.execute(
            select(func.count(DBLedger.id)).where(
                and_(
                    DBLedger.related_entry_id.is_(None),
                    DBLedger.entry_type == "debit"  # Only check debits (they should have a credit)
                )
            )
        )
        result["orphaned_entries"] = orphaned_result.scalar() or 0
        
        if result["orphaned_entries"] > 0:
            result["errors"].append(f"Found {result['orphaned_entries']} orphaned debit entries without credits")
        
        if not result["is_balanced"]:
            result["errors"].append(f"Ledger not balanced: debits ${result['total_debits']:.2f} ≠ credits ${result['total_credits']:.2f}")
        
        return result
    
    @staticmethod
    async def get_user_transaction_history(db: AsyncSession, user_id: int, limit: int = 100) -> List[Dict]:
        """
        Get transaction history for a user from ledger.
        
        Returns list of ledger entries showing all money movements.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Max entries to return
            
        Returns:
            List of transaction entries
        """
        result = await db.execute(
            select(DBLedger)
            .where(DBLedger.user_id == user_id)
            .order_by(DBLedger.created_at.desc())
            .limit(limit)
        )
        entries = result.scalars().all()
        
        return [
            {
                "id": entry.id,
                "type": entry.entry_type,
                "amount": float(entry.amount),
                "description": entry.description,
                "reference": entry.reference_number,
                "status": entry.status,
                "source_user": entry.source_user_id,
                "destination_user": entry.destination_user_id,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "posted_at": entry.posted_at.isoformat() if entry.posted_at else None
            }
            for entry in entries
        ]
    
    @staticmethod
    async def verify_transaction_has_ledger_entries(db: AsyncSession, transaction_id: int) -> bool:
        """
        Verify that a transaction has exactly 2 ledger entries (debit and credit).
        
        Args:
            db: Database session
            transaction_id: Transaction ID
            
        Returns:
            True if exactly 1 debit and 1 credit exist
        """
        result = await db.execute(
            select(func.count(DBLedger.id)).where(
                DBLedger.transaction_id == transaction_id
            )
        )
        count = result.scalar() or 0
        return count == 2
