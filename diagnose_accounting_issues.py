"""
Diagnostic script to identify accounting data integrity issues.
This will reveal:
1. Transactions with NULL/N/A user_id
2. Transactions without account_id
3. Mismatches between Account.balance and actual transaction sums
4. Orphaned fund transfers
"""

import asyncio
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from config import settings
from database import engine, SessionLocal
from models import (
    User as DBUser,
    Account as DBAccount,
    Transaction as DBTransaction,
    FundTransfer as DBFundTransfer,
    KYCInfo as DBKYCInfo
)

async def diagnose_accounting_issues():
    """Run diagnostic checks on accounting data"""
    
    async with SessionLocal() as db:
        print("\n" + "="*80)
        print("FINANCIAL SYSTEM DIAGNOSTIC REPORT")
        print("="*80)
        
        # 1. Check transactions with NULL user_id
        print("\n[1] ORPHANED TRANSACTIONS (no user_id)")
        print("-" * 80)
        orphaned_tx = await db.execute(
            select(DBTransaction).where(DBTransaction.user_id.is_(None))
        )
        orphaned_list = orphaned_tx.scalars().all()
        print(f"Total orphaned transactions: {len(orphaned_list)}")
        for tx in orphaned_list[:5]:
            print(f"  - TX ID {tx.id}: ${tx.amount} ({tx.transaction_type}) - Status: {tx.status}")
        if len(orphaned_list) > 5:
            print(f"  ... and {len(orphaned_list) - 5} more")
        
        # 2. Check transactions without account_id
        print("\n[2] TRANSACTIONS WITHOUT ACCOUNT LINKAGE")
        print("-" * 80)
        no_account_tx = await db.execute(
            select(DBTransaction).where(DBTransaction.account_id.is_(None))
        )
        no_account_list = no_account_tx.scalars().all()
        print(f"Total transactions missing account_id: {len(no_account_list)}")
        for tx in no_account_list[:5]:
            user = await db.execute(select(DBUser).where(DBUser.id == tx.user_id))
            user_obj = user.scalar_one_or_none()
            user_email = user_obj.email if user_obj else "UNKNOWN"
            print(f"  - TX ID {tx.id}: User {user_email} - ${tx.amount} ({tx.transaction_type})")
        if len(no_account_list) > 5:
            print(f"  ... and {len(no_account_list) - 5} more")
        
        # 3. Check fund transfers with invalid user_id
        print("\n[3] FUND TRANSFERS WITH INVALID/MISSING USER")
        print("-" * 80)
        invalid_fund = await db.execute(
            select(DBFundTransfer).where(
                or_(DBFundTransfer.user_id.is_(None), DBFundTransfer.user_id == 0)
            )
        )
        invalid_list = invalid_fund.scalars().all()
        print(f"Total fund transfers with invalid user: {len(invalid_list)}")
        for ft in invalid_list[:5]:
            print(f"  - FT ID {ft.id}: ${ft.amount} - Status: {ft.status}")
        
        # 4. Check Account balance mismatches
        print("\n[4] ACCOUNT BALANCE RECONCILIATION")
        print("-" * 80)
        accounts_result = await db.execute(select(DBAccount))
        all_accounts = accounts_result.scalars().all()
        
        mismatches = []
        for account in all_accounts:
            # Calculate expected balance from transactions
            tx_sum_result = await db.execute(
                select(func.sum(DBTransaction.amount)).where(
                    and_(
                        DBTransaction.account_id == account.id,
                        DBTransaction.status == "completed"
                    )
                )
            )
            expected_balance = float(tx_sum_result.scalar() or 0)
            actual_balance = float(account.balance)
            
            if abs(expected_balance - actual_balance) > 0.01:  # Allow for rounding
                mismatches.append({
                    "account_id": account.id,
                    "account_number": account.account_number,
                    "owner_id": account.owner_id,
                    "stored_balance": actual_balance,
                    "calculated_balance": expected_balance,
                    "difference": actual_balance - expected_balance
                })
        
        print(f"Total accounts with balance mismatches: {len(mismatches)}")
        for mismatch in mismatches[:5]:
            print(f"  - Account {mismatch['account_number']} (Owner: {mismatch['owner_id']})")
            print(f"    Stored: ${mismatch['stored_balance']:.2f} | Calculated: ${mismatch['calculated_balance']:.2f} | Diff: ${mismatch['difference']:.2f}")
        if len(mismatches) > 5:
            print(f"  ... and {len(mismatches) - 5} more")
        
        # 5. User-level balance analysis
        print("\n[5] USER BALANCE ANALYSIS")
        print("-" * 80)
        users_result = await db.execute(select(DBUser))
        all_users = users_result.scalars().all()
        
        balance_issues = []
        for user in all_users:
            # Sum all completed transactions for this user
            user_tx_sum = await db.execute(
                select(func.sum(DBTransaction.amount)).where(
                    and_(
                        DBTransaction.user_id == user.id,
                        DBTransaction.status == "completed"
                    )
                )
            )
            tx_total = float(user_tx_sum.scalar() or 0)
            
            # Sum all account balances for this user
            account_balance_sum = await db.execute(
                select(func.sum(DBAccount.balance)).where(
                    DBAccount.owner_id == user.id
                )
            )
            account_total = float(account_balance_sum.scalar() or 0)
            
            if abs(tx_total - account_total) > 0.01:
                balance_issues.append({
                    "user_id": user.id,
                    "email": user.email,
                    "tx_sum": tx_total,
                    "account_sum": account_total,
                    "diff": account_total - tx_total
                })
        
        print(f"Users with balance mismatches between transactions and accounts: {len(balance_issues)}")
        for issue in balance_issues[:5]:
            print(f"  - {issue['email']} (User {issue['user_id']})")
            print(f"    Transaction sum: ${issue['tx_sum']:.2f} | Account balance: ${issue['account_sum']:.2f} | Diff: ${issue['diff']:.2f}")
        if len(balance_issues) > 5:
            print(f"  ... and {len(balance_issues) - 5} more")
        
        # 6. Check deposits specifically
        print("\n[6] DEPOSIT ANALYSIS")
        print("-" * 80)
        deposits_result = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                and_(
                    DBTransaction.transaction_type == "deposit",
                    DBTransaction.status == "completed"
                )
            )
        )
        total_deposits = float(deposits_result.scalar() or 0)
        
        deposit_count = await db.execute(
            select(func.count(DBTransaction.id)).where(
                and_(
                    DBTransaction.transaction_type == "deposit",
                    DBTransaction.status == "completed"
                )
            )
        )
        deposit_num = deposit_count.scalar() or 0
        
        print(f"Total completed deposits: {deposit_num}")
        print(f"Total deposit amount: ${total_deposits:.2f}")
        
        # Deposits without account
        deposits_no_account = await db.execute(
            select(func.count(DBTransaction.id)).where(
                and_(
                    DBTransaction.transaction_type == "deposit",
                    DBTransaction.status == "completed",
                    DBTransaction.account_id.is_(None)
                )
            )
        )
        print(f"Deposits missing account_id: {deposits_no_account.scalar() or 0}")
        
        # 7. Summary statistics
        print("\n[7] SUMMARY STATISTICS")
        print("-" * 80)
        
        total_users = await db.execute(select(func.count(DBUser.id)))
        total_accounts = await db.execute(select(func.count(DBAccount.id)))
        total_transactions = await db.execute(select(func.count(DBTransaction.id)))
        total_completed_tx = await db.execute(
            select(func.count(DBTransaction.id)).where(DBTransaction.status == "completed")
        )
        
        print(f"Total users: {total_users.scalar()}")
        print(f"Total accounts: {total_accounts.scalar()}")
        print(f"Total transactions: {total_transactions.scalar()}")
        print(f"Completed transactions: {total_completed_tx.scalar()}")
        
        # Global totals
        global_account_balance = await db.execute(
            select(func.sum(DBAccount.balance))
        )
        print(f"\nGlobal account balance (sum of all accounts): ${float(global_account_balance.scalar() or 0):.2f}")
        
        global_tx_sum = await db.execute(
            select(func.sum(DBTransaction.amount)).where(
                DBTransaction.status == "completed"
            )
        )
        print(f"Global transaction sum (all completed): ${float(global_tx_sum.scalar() or 0):.2f}")
        
        print("\n" + "="*80)
        print("END DIAGNOSTIC REPORT")
        print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(diagnose_accounting_issues())
