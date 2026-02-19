"""
Data Cleanup Script
===================

Fixes accounting data integrity issues identified by reconciliation tests:
1. Removes transactions without account_id
2. Corrects account balances to match transaction sums
3. Validates all orphaned data is cleaned
"""

import asyncio
from sqlalchemy import select, func, and_

from database import SessionLocal
from models import (
    User as DBUser,
    Account as DBAccount,
    Transaction as DBTransaction,
)
from balance_service import BalanceService


async def cleanup_accounting_data():
    """Clean up accounting data"""
    
    async with SessionLocal() as db:
        print("\n" + "="*80)
        print("ACCOUNTING DATA CLEANUP")
        print("="*80 + "\n")
        
        # Step 1: Identify and remove transactions without account_id
        print("[1] Removing transactions without account_id...")
        no_account_tx = await db.execute(
            select(DBTransaction).where(DBTransaction.account_id.is_(None))
        )
        no_account_list = no_account_tx.scalars().all()
        
        removed_count = 0
        for tx in no_account_list:
            print(f"  Removing TX ID {tx.id}: User {tx.user_id} - ${tx.amount} ({tx.transaction_type})")
            await db.delete(tx)
            removed_count += 1
        
        print(f"  Removed: {removed_count} transactions\n")
        
        # Step 2: Recalculate and fix account balances
        print("[2] Recalculating account balances...")
        accounts_result = await db.execute(select(DBAccount))
        all_accounts = accounts_result.scalars().all()
        
        accounts_fixed = 0
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
            calculated_balance = float(tx_sum_result.scalar() or 0)
            
            if abs(float(account.balance) - calculated_balance) > 0.01:
                print(f"  Account {account.account_number} (Owner: {account.owner_id})")
                print(f"    Stored balance: ${float(account.balance):.2f}")
                print(f"    Calculated balance: ${calculated_balance:.2f}")
                
                # Update account balance to match transactions
                account.balance = calculated_balance
                accounts_fixed += 1
                
                print(f"    ✓ Updated to ${calculated_balance:.2f}\n")
        
        print(f"  Fixed: {accounts_fixed} accounts\n")
        
        # Step 3: Commit all changes
        print("[3] Committing changes...")
        await db.commit()
        print("  ✓ Changes committed\n")
        
        # Step 4: Verify cleanup
        print("[4] Verifying cleanup...")
        
        # Check for remaining orphaned transactions
        orphaned_check = await db.execute(
            select(func.count(DBTransaction.id)).where(DBTransaction.account_id.is_(None))
        )
        remaining_orphaned = orphaned_check.scalar() or 0
        
        if remaining_orphaned == 0:
            print("  ✓ No orphaned transactions remaining")
        else:
            print(f"  ⚠ WARNING: {remaining_orphaned} orphaned transactions still exist")
        
        # Verify accounting equation
        admin_total = await BalanceService.get_admin_total_volume(db)
        user_balances_sum = await BalanceService.get_admin_total_system_balance(db)
        difference = abs(admin_total - user_balances_sum)
        
        if difference < 0.01:
            print(f"  ✓ Accounting equation balanced: ${admin_total:.2f} = ${user_balances_sum:.2f}")
        else:
            print(f"  ⚠ WARNING: Accounting equation imbalanced: ${admin_total:.2f} ≠ ${user_balances_sum:.2f}")
        
        print("\n" + "="*80)
        print("CLEANUP COMPLETE")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(cleanup_accounting_data())
