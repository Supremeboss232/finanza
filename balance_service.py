"""
Balance Calculation Service
==========================

Provides the SINGLE SOURCE OF TRUTH for all balance calculations.

PRINCIPLE: Never store balance as a primary value.
Balance = sum(completed transactions) filtered by user_id + account_id

This ensures Admin and User dashboards always read the same reality.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, distinct
from decimal import Decimal
from typing import Dict, List, Optional
from models import Transaction as DBTransaction, Account as DBAccount, User as DBUser, Ledger as DBLedger


class BalanceService:
    """Service for calculating balances from transactions (source of truth)"""
    
    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: int) -> float:
        """
        Calculate a user's total balance from:
        1. COMPLETED transactions (legacy system)
        2. POSTED ledger entries (double-entry accounting system)
        
        RULE 3: Balance is derived from transactions/ledger, never stored.
        Pending/blocked transactions are HELD FUNDS, not balance.
        
        Formula: 
        - From Transactions: sum(amount) where status="completed"
        - From Ledger: sum(credits) - sum(debits) where status="posted"
        
        Returns: float balance
        """
        # Get balance from Transaction table (completed transactions)
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.status == "completed"
                )
            )
        )
        tx_balance = result.scalar() or Decimal("0")
        
        # Get balance from Ledger table (double-entry accounting)
        # Credits increase balance, debits decrease it
        result = await db.execute(
            select(func.sum(DBLedger.amount)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted"
                )
            )
        )
        ledger_credits = result.scalar() or Decimal("0")
        
        result = await db.execute(
            select(func.sum(DBLedger.amount)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "debit",
                    DBLedger.status == "posted"
                )
            )
        )
        ledger_debits = result.scalar() or Decimal("0")
        
        ledger_balance = ledger_credits - ledger_debits
        
        # Return combined balance
        total_balance = float(tx_balance) + float(ledger_balance)
        return total_balance
    
    @staticmethod
    async def get_account_balance(db: AsyncSession, account_id: int) -> float:
        """
        Calculate an account's balance from completed transactions.
        
        Formula: sum(amount) of all completed transactions for this account
        
        Returns: float balance
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.account_id == account_id,
                    DBTransaction.status == "completed"
                )
            )
        )
        balance = result.scalar() or 0
        return float(balance)
    
    @staticmethod
    async def get_user_deposit_total(db: AsyncSession, user_id: int) -> float:
        """
        Calculate total deposits (inbound money) for a user.
        
        Formula: sum(amount) of completed deposit transactions
        
        Returns: float total deposits
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.transaction_type == "deposit",
                    DBTransaction.status == "completed"
                )
            )
        )
        total = result.scalar() or Decimal("0")
        return float(total)
    
    @staticmethod
    async def get_user_withdrawal_total(db: AsyncSession, user_id: int) -> float:
        """
        Calculate total withdrawals (outbound money) for a user.
        
        Formula: sum(amount) of completed withdrawal transactions
        
        Returns: float total withdrawals (as positive number)
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.transaction_type == "withdrawal",
                    DBTransaction.status == "completed"
                )
            )
        )
        total = result.scalar() or Decimal("0")
        return float(total)
    
    @staticmethod
    async def get_user_transfer_received(db: AsyncSession, user_id: int) -> float:
        """
        Calculate total transfers received by a user.
        
        Formula: sum(amount) of completed fund_transfer transactions (positive amounts)
        
        Returns: float total transfers received
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.transaction_type == "fund_transfer",
                    DBTransaction.status == "completed"
                )
            )
        )
        total = result.scalar() or Decimal("0")
        return float(total)
    
    @staticmethod
    async def get_all_user_balances(db: AsyncSession) -> Dict[int, float]:
        """
        Calculate balances for ALL users.
        
        Returns: Dict mapping user_id -> balance
        """
        # Get all users
        users_result = await db.execute(select(DBUser.id))
        user_ids = [row[0] for row in users_result.fetchall()]
        
        balances = {}
        for user_id in user_ids:
            balances[user_id] = await BalanceService.get_user_balance(db, user_id)
        
        return balances
    
    @staticmethod
    async def get_admin_total_deposits(db: AsyncSession) -> float:
        """
        Calculate TOTAL deposits across ALL users.
        
        Formula: sum(amount) of all completed deposit transactions in system
        
        Returns: float total deposits
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.transaction_type == "deposit",
                    DBTransaction.status == "completed"
                )
            )
        )
        total = result.scalar() or 0
        return float(total)
    
    @staticmethod
    async def get_admin_total_volume(db: AsyncSession) -> float:
        """
        Calculate TOTAL transaction volume (sum of all completed transactions).
        
        Formula: sum(amount) of all completed transactions
        
        Returns: float total volume
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                DBTransaction.status == "completed"
            )
        )
        total = result.scalar() or 0
        return float(total)
    
    @staticmethod
    async def get_admin_total_system_balance(db: AsyncSession) -> float:
        """
        Calculate TOTAL system balance (sum of all users' balances).
        
        This is the verification metric - should equal get_admin_total_volume
        
        Returns: float total system balance
        """
        all_balances = await BalanceService.get_all_user_balances(db)
        return sum(all_balances.values())
    
    @staticmethod
    async def get_active_user_count(db: AsyncSession) -> int:
        """
        Count users with at least one completed transaction.
        
        Returns: int count
        """
        result = await db.execute(
            select(func.count(distinct(DBTransaction.user_id))).where(
                DBTransaction.status == "completed"
            )
        )
        count = result.scalar() or 0
        return int(count)
    
    @staticmethod
    async def reconcile_account_balance(db: AsyncSession, account_id: int) -> Dict[str, float]:
        """
        Reconcile an account's stored balance with calculated balance.
        
        Returns: {
            'stored_balance': float (from DB),
            'calculated_balance': float (from transactions),
            'difference': float (stored - calculated),
            'needs_correction': bool
        }
        """
        # Get stored balance
        account_result = await db.execute(
            select(DBAccount.balance).where(DBAccount.id == account_id)
        )
        stored = account_result.scalar() or 0
        stored = float(stored)
        
        # Get calculated balance
        calculated = await BalanceService.get_account_balance(db, account_id)
        
        difference = stored - calculated
        needs_correction = abs(difference) > 0.01  # Allow for rounding
        
        return {
            'stored_balance': stored,
            'calculated_balance': calculated,
            'difference': difference,
            'needs_correction': needs_correction
        }
    
    @staticmethod
    async def get_user_transaction_breakdown(db: AsyncSession, user_id: int) -> Dict[str, float]:
        """
        Get breakdown of all transaction types for a user.
        
        Returns: {
            'total_balance': float,
            'total_deposits': float,
            'total_withdrawals': float,
            'total_transfers': float,
            'transaction_count': int
        }
        """
        # Total balance
        balance = await BalanceService.get_user_balance(db, user_id)
        
        # Deposits
        deposits = await BalanceService.get_user_deposit_total(db, user_id)
        
        # Withdrawals
        withdrawals = await BalanceService.get_user_withdrawal_total(db, user_id)
        
        # Transfers
        transfers = await BalanceService.get_user_transfer_received(db, user_id)
        
        # Transaction count
        count_result = await db.execute(
            select(func.count(DBTransaction.id)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.status == "completed"
                )
            )
        )
        count = count_result.scalar() or 0
        
        return {
            'total_balance': balance,
            'total_deposits': deposits,
            'total_withdrawals': withdrawals,
            'total_transfers': transfers,
            'transaction_count': int(count)
        }

    @staticmethod
    async def get_user_held_funds(db: AsyncSession, user_id: int) -> float:
        """
        Calculate total held funds (pending + blocked transactions) for a user.
        
        RULE 3: Held funds = pending + blocked transactions
        These are visible to admin but NOT included in user balance.
        
        Formula: sum(amount) of all pending/blocked transactions for this user
        
        Returns: float held funds (0 if no pending/blocked)
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.status.in_(["pending", "blocked"])
                )
            )
        )
        held = result.scalar() or 0
        return float(held)

    @staticmethod
    async def get_account_held_funds(db: AsyncSession, account_id: int) -> float:
        """
        Calculate total held funds for an account.
        
        Formula: sum(amount) of all pending/blocked transactions for this account
        
        Returns: float held funds
        """
        result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.account_id == account_id,
                    DBTransaction.status.in_(["pending", "blocked"])
                )
            )
        )
        held = result.scalar() or 0
        return float(held)

    @staticmethod
    async def get_user_fund_summary(db: AsyncSession, user_id: int) -> Dict[str, float]:
        """
        Get comprehensive fund summary for a user.
        
        Returns: {
            'available_balance': float (completed transactions only),
            'held_funds': float (pending + blocked),
            'total_funds': float (available + held),
            'pending_count': int,
            'blocked_count': int
        }
        """
        available = await BalanceService.get_user_balance(db, user_id)
        held = await BalanceService.get_user_held_funds(db, user_id)
        
        # Get transaction counts by status
        pending_result = await db.execute(
            select(func.count(DBTransaction.id)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.status == "pending"
                )
            )
        )
        pending_count = pending_result.scalar() or 0
        
        blocked_result = await db.execute(
            select(func.count(DBTransaction.id)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.status == "blocked"
                )
            )
        )
        blocked_count = blocked_result.scalar() or 0
        
        return {
            'available_balance': available,
            'held_funds': held,
            'total_funds': available + held,
            'pending_count': int(pending_count),
            'blocked_count': int(blocked_count)
        }

"""
Balance Calculation Service - Ledger-Based
===========================================

Provides SINGLE SOURCE OF TRUTH for all balance calculations.

PRINCIPLE: Balance = sum(credit_entries) - sum(debit_entries) from ledger

This ensures Admin and User dashboards always read the same reality.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from decimal import Decimal
from typing import Dict, List, Optional
from models import (
    Ledger as DBLedger,
    User as DBUser,
    Account as DBAccount
)


class BalanceServiceLedger:
    """Service for calculating balances from ledger (double-entry source of truth)"""
    
    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: int) -> float:
        """
        Calculate a user's total balance from LEDGER entries.
        
        RULE 3: Balance is derived from ledger, never stored.
        
        Balance = sum(credits to user) - sum(debits from user)
        
        Returns: float balance
        """
        # Sum all credits TO this user
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
        
        # Sum all debits FROM this user
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
    async def get_account_balance(db: AsyncSession, account_id: int) -> float:
        """
        Calculate an account's balance from ledger.
        
        Account balance = sum(credits to account owner) - sum(debits from account owner)
        
        Args:
            db: Database session
            account_id: Account ID
            
        Returns: float balance
        """
        # Get account owner
        account_result = await db.execute(
            select(DBAccount).where(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            return 0.0
        
        return await BalanceServiceLedger.get_user_balance(db, account.owner_id)
    
    @staticmethod
    async def get_user_deposit_total(db: AsyncSession, user_id: int) -> float:
        """
        Get total deposits for a user (credits from system account).
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns: float total deposits
        """
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted",
                    DBLedger.source_user_id == 1  # From system account
                )
            )
        )
        return float(result.scalar() or 0)
    
    @staticmethod
    async def get_user_withdrawal_total(db: AsyncSession, user_id: int) -> float:
        """
        Get total withdrawals for a user (debits to system account).
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns: float total withdrawals
        """
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "debit",
                    DBLedger.status == "posted",
                    DBLedger.destination_user_id == 1  # To system account
                )
            )
        )
        return float(result.scalar() or 0)
    
    @staticmethod
    async def get_user_transfer_received(db: AsyncSession, user_id: int) -> float:
        """
        Get total transfers received from other users.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns: float total received
        """
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted",
                    DBLedger.source_user_id != 1  # Not from system
                )
            )
        )
        return float(result.scalar() or 0)
    
    @staticmethod
    async def get_all_user_balances(db: AsyncSession) -> Dict[int, float]:
        """
        Get balances for all users.
        
        Returns:
            Dict mapping user_id -> balance
        """
        result = await db.execute(select(DBUser.id))
        user_ids = result.scalars().all()
        
        balances = {}
        for user_id in user_ids:
            balances[user_id] = await BalanceServiceLedger.get_user_balance(db, user_id)
        
        return balances
    
    @staticmethod
    async def get_admin_total_deposits(db: AsyncSession) -> float:
        """
        Get total system deposits (sum of all credits from system account).
        
        Returns: float total deposits
        """
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted",
                    DBLedger.source_user_id == 1  # From system account
                )
            )
        )
        return float(result.scalar() or 0)
    
    @staticmethod
    async def get_admin_total_volume(db: AsyncSession) -> float:
        """
        Get total system volume (sum of all credits across all users).
        
        Note: This equals sum of all debits globally.
        If ledger is balanced: total_credits_all_users should equal total_debits_all_users
        
        Returns: float total volume
        """
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted"
                )
            )
        )
        return float(result.scalar() or 0)
    
    @staticmethod
    async def get_admin_total_system_balance(db: AsyncSession) -> float:
        """
        Get sum of all user balances.
        
        In a properly balanced ledger:
        sum(all_user_balances) should equal total_debits - total_credits globally
        
        If different, indicates accounting error.
        
        Returns: float sum of all balances
        """
        all_balances = await BalanceServiceLedger.get_all_user_balances(db)
        return sum(all_balances.values())
    
    @staticmethod
    async def reconcile_account_balance(
        db: AsyncSession,
        account_id: int
    ) -> bool:
        """
        Verify that account.balance column matches calculated balance from ledger.
        
        Args:
            db: Database session
            account_id: Account to check
            
        Returns:
            True if balanced, False if mismatch
        """
        account_result = await db.execute(
            select(DBAccount).where(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            return False
        
        calculated = await BalanceServiceLedger.get_account_balance(db, account_id)
        stored = float(account.balance)
        
        # Allow for rounding errors
        return abs(calculated - stored) < 0.01
    
    @staticmethod
    async def get_user_transaction_breakdown(
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """
        Get detailed breakdown of user's money movements.
        
        Returns:
            Dict with credits, debits, balance, and breakdown by type
        """
        credits = await BalanceServiceLedger.get_user_balance(db, user_id)  # Will be net
        
        # Get breakdown
        deposits = await BalanceServiceLedger.get_user_deposit_total(db, user_id)
        withdrawals = await BalanceServiceLedger.get_user_withdrawal_total(db, user_id)
        received = await BalanceServiceLedger.get_user_transfer_received(db, user_id)
        
        balance = await BalanceServiceLedger.get_user_balance(db, user_id)
        
        return {
            "balance": balance,
            "deposits": deposits,
            "withdrawals": withdrawals,
            "transfers_received": received,
            "breakdown": {
                "from_deposits": deposits,
                "from_transfers": received,
                "total_credits": deposits + received,
                "withdrawals": withdrawals,
                "net": balance
            }
        }
