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
