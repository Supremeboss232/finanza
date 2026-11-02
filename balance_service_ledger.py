"""
Balance Calculation Service - Unified Ledger & Account Service
==============================================================

Provides SINGLE SOURCE OF TRUTH for all balance calculations across
both the User Portal and the Admin Control Center.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from decimal import Decimal
from typing import Dict, List, Optional
from models import (
    Ledger as DBLedger,
    User as DBUser,
    Account as DBAccount,
    Transaction as DBTransaction
)


class BalanceServiceLedger:
    """Service for calculating balances from ledger and accounts (unified source of truth)"""

    @staticmethod
    async def get_user_balance(db: AsyncSession, user_id: int) -> float:
        """
        Calculate a user's total balance across their accounts and ledger entries.
        Ensures Admin and User portals always display the exact same balance.
        """
        acc_result = await db.execute(
            select(func.coalesce(func.sum(DBAccount.balance), 0), func.count(DBAccount.id)).where(
                DBAccount.owner_id == user_id
            )
        )
        acc_row = acc_result.one()
        acc_balance = float(acc_row[0] or 0)
        acc_count = int(acc_row[1] or 0)

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
        ledger_balance = credits - debits

        if acc_count > 0 and (acc_balance != 0 or ledger_balance == 0):
            return acc_balance
        return ledger_balance

    @staticmethod
    async def get_account_balance(db: AsyncSession, account_id: int) -> float:
        """Calculate an account's balance."""
        account_result = await db.execute(
            select(DBAccount).where(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            return 0.0
        if account.balance is not None and float(account.balance) != 0:
            return float(account.balance)
        return await BalanceServiceLedger.get_user_balance(db, account.owner_id)

    @staticmethod
    async def get_user_deposit_total(db: AsyncSession, user_id: int) -> float:
        """Get total deposits for a user."""
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted",
                    DBLedger.source_user_id == 1
                )
            )
        )
        ledger_dep = float(result.scalar() or 0)
        tx_res = await db.execute(
            select(func.coalesce(func.sum(DBTransaction.amount), 0)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.transaction_type.in_(["deposit", "admin_fund", "admin_credit", "credit"]),
                    DBTransaction.status == "completed"
                )
            )
        )
        tx_dep = float(tx_res.scalar() or 0)
        return max(ledger_dep, tx_dep)

    @staticmethod
    async def get_user_withdrawal_total(db: AsyncSession, user_id: int) -> float:
        """Get total withdrawals for a user."""
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "debit",
                    DBLedger.status == "posted",
                    DBLedger.destination_user_id == 1
                )
            )
        )
        ledger_wd = float(result.scalar() or 0)
        tx_res = await db.execute(
            select(func.coalesce(func.sum(DBTransaction.amount), 0)).where(
                and_(
                    DBTransaction.user_id == user_id,
                    DBTransaction.transaction_type.in_(["withdrawal", "admin_debit", "debit", "transfer", "bill_pay", "wire_transfer"]),
                    DBTransaction.status == "completed"
                )
            )
        )
        tx_wd = float(tx_res.scalar() or 0)
        return max(ledger_wd, tx_wd)

    @staticmethod
    async def get_user_transfer_received(db: AsyncSession, user_id: int) -> float:
        """Get total transfers received from other users."""
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.user_id == user_id,
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted",
                    DBLedger.source_user_id != 1
                )
            )
        )
        return float(result.scalar() or 0)

    @staticmethod
    async def get_all_user_balances(db: AsyncSession) -> Dict[int, float]:
        """Get balances for all users."""
        result = await db.execute(select(DBUser.id))
        user_ids = result.scalars().all()

        balances = {}
        for user_id in user_ids:
            balances[user_id] = await BalanceServiceLedger.get_user_balance(db, user_id)

        return balances

    @staticmethod
    async def get_admin_total_deposits(db: AsyncSession) -> float:
        """Get total system deposits / AUM across ledger and accounts."""
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted",
                    DBLedger.source_user_id == 1
                )
            )
        )
        ledger_deposits = float(result.scalar() or 0)
        acc_result = await db.execute(
            select(func.coalesce(func.sum(DBAccount.balance), 0))
        )
        acc_deposits = float(acc_result.scalar() or 0)
        return max(ledger_deposits, acc_deposits)

    @staticmethod
    async def get_admin_total_volume(db: AsyncSession) -> float:
        """Get total system volume across ledger and completed transactions."""
        result = await db.execute(
            select(func.coalesce(func.sum(DBLedger.amount), 0)).where(
                and_(
                    DBLedger.entry_type == "credit",
                    DBLedger.status == "posted"
                )
            )
        )
        ledger_vol = float(result.scalar() or 0)
        tx_result = await db.execute(
            select(func.coalesce(func.sum(DBTransaction.amount), 0)).where(
                DBTransaction.status == "completed"
            )
        )
        tx_vol = float(tx_result.scalar() or 0)
        return max(ledger_vol, tx_vol)

    @staticmethod
    async def get_admin_total_system_balance(db: AsyncSession) -> float:
        """Get sum of all user balances."""
        all_balances = await BalanceServiceLedger.get_all_user_balances(db)
        return sum(all_balances.values())

    @staticmethod
    async def reconcile_account_balance(
        db: AsyncSession,
        account_id: int
    ) -> bool:
        """Verify that account.balance column matches calculated balance."""
        account_result = await db.execute(
            select(DBAccount).where(DBAccount.id == account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            return False

        calculated = await BalanceServiceLedger.get_account_balance(db, account_id)
        stored = float(account.balance or 0)
        return abs(calculated - stored) < 0.01

    @staticmethod
    async def get_user_transaction_breakdown(
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """Get detailed breakdown of user's money movements."""
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
