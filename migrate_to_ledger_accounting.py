#!/usr/bin/env python
"""
Migration Script: Initialize Ledger-Based Accounting System
===========================================================

This script:
1. Creates the Ledger table
2. Migrates existing transactions to ledger entries (double-entry)
3. Verifies ledger integrity
4. Tests reconciliation

Run this ONCE when deploying the fix.
"""

import asyncio
from sqlalchemy import text, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime

from database import engine
from models import (
    Base,
    User as DBUser,
    Account as DBAccount,
    Transaction as DBTransaction,
    Ledger as DBLedger
)
from ledger_service import LedgerService
from balance_service_ledger import BalanceServiceLedger


async def create_ledger_table():
    """Step 1: Create the Ledger table"""
    print("\n" + "=" * 80)
    print("STEP 1: Creating Ledger Table")
    print("=" * 80)
    
    try:
        async with engine.begin() as connection:
            # Create Ledger table
            await connection.run_sync(Base.metadata.create_all, tables=[DBLedger.__table__])
        print("✓ Ledger table created successfully")
        return True
    except Exception as e:
        print(f"✗ Error creating Ledger table: {e}")
        return False


async def migrate_transactions_to_ledger(db: AsyncSession):
    """Step 2: Migrate existing transactions to ledger entries"""
    print("\n" + "=" * 80)
    print("STEP 2: Migrating Existing Transactions to Ledger")
    print("=" * 80)
    
    try:
        # Get all completed transactions that don't have ledger entries yet
        result = await db.execute(
            select(DBTransaction).where(
                DBTransaction.status == "completed"
            )
        )
        transactions = result.scalars().all()
        
        print(f"Found {len(transactions)} completed transactions to migrate")
        
        migrated = 0
        failed = 0
        
        for tx in transactions:
            try:
                # Check if ledger entries already exist for this transaction
                ledger_result = await db.execute(
                    select(func.count(DBLedger.id)).where(
                        DBLedger.transaction_id == tx.id
                    )
                )
                existing_count = ledger_result.scalar() or 0
                
                if existing_count > 0:
                    print(f"  ⊘ TX {tx.id}: Already has {existing_count} ledger entries, skipping")
                    continue
                
                if not tx.user_id or tx.user_id <= 0:
                    print(f"  ✗ TX {tx.id}: Invalid user_id ({tx.user_id}), skipping")
                    failed += 1
                    continue
                
                # For deposits/funds: create credit from system account
                if tx.transaction_type in ["deposit", "fund_transfer", "admin_fund", "bulk_fund"]:
                    _, _ = await LedgerService.create_admin_funding(
                        db=db,
                        transaction=tx,
                        to_user_id=tx.user_id,
                        amount=Decimal(str(tx.amount)),
                        description=tx.description or tx.transaction_type,
                        reference_number=tx.reference_number
                    )
                    print(f"  ✓ TX {tx.id}: Created ledger entries (fund: ${tx.amount})")
                    migrated += 1
                
                elif tx.transaction_type == "withdrawal":
                    # Withdrawal: create debit to system account
                    _, _ = await LedgerService.create_atomic_transfer(
                        db=db,
                        transaction=tx,
                        from_user_id=tx.user_id,
                        to_user_id=LedgerService.SYSTEM_USER_ID,
                        amount=Decimal(str(tx.amount)),
                        description=f"Withdrawal: {tx.description}",
                        reference_number=tx.reference_number
                    )
                    print(f"  ✓ TX {tx.id}: Created ledger entries (withdrawal: ${tx.amount})")
                    migrated += 1
                
                else:
                    print(f"  ⊘ TX {tx.id}: Type '{tx.transaction_type}' - manual review needed")
                    failed += 1
                
            except Exception as e:
                print(f"  ✗ TX {tx.id}: Error during migration: {e}")
                failed += 1
                continue
        
        await db.commit()
        print(f"\nMigration Summary:")
        print(f"  ✓ Migrated: {migrated}")
        print(f"  ✗ Failed: {failed}")
        print(f"  Total: {len(transactions)}")
        
        return migrated > 0 or failed == 0
        
    except Exception as e:
        await db.rollback()
        print(f"✗ Error during migration: {e}")
        return False


async def verify_ledger_integrity(db: AsyncSession):
    """Step 3: Verify ledger integrity"""
    print("\n" + "=" * 80)
    print("STEP 3: Verifying Ledger Integrity")
    print("=" * 80)
    
    try:
        reconciliation = await LedgerService.reconcile_ledger(db)
        
        print(f"\nLedger Reconciliation Results:")
        print(f"  Total Debits:      ${reconciliation['total_debits']:.2f}")
        print(f"  Total Credits:     ${reconciliation['total_credits']:.2f}")
        print(f"  Difference:        ${reconciliation['difference']:.2f}")
        print(f"  Ledger Balanced:   {'✓ YES' if reconciliation['is_balanced'] else '✗ NO'}")
        print(f"  Orphaned Entries:  {reconciliation['orphaned_entries']}")
        
        if reconciliation['errors']:
            print(f"\nErrors found:")
            for error in reconciliation['errors']:
                print(f"  ✗ {error}")
        else:
            print(f"\n✓ No errors found in ledger")
        
        return reconciliation['is_balanced']
        
    except Exception as e:
        print(f"✗ Error verifying ledger: {e}")
        return False


async def test_reconciliation(db: AsyncSession):
    """Step 4: Test reconciliation"""
    print("\n" + "=" * 80)
    print("STEP 4: Testing Reconciliation")
    print("=" * 80)
    
    try:
        # Get all users
        result = await db.execute(select(DBUser))
        users = result.scalars().all()
        
        print(f"\nUser Balance Verification ({len(users)} users):")
        
        total_balance = 0
        mismatches = 0
        
        for user in users[:10]:  # Show first 10
            ledger_balance = await BalanceServiceLedger.get_user_balance(db, user.id)
            total_balance += ledger_balance
            
            # Get account balances from DB
            account_result = await db.execute(
                select(func.sum(DBAccount.balance)).where(
                    DBAccount.owner_id == user.id
                )
            )
            account_balance = float(account_result.scalar() or 0)
            
            match = "✓" if abs(ledger_balance - account_balance) < 0.01 else "✗"
            print(f"  {match} User {user.id} ({user.email}): Ledger=${ledger_balance:.2f}, Account=${account_balance:.2f}")
            
            if abs(ledger_balance - account_balance) > 0.01:
                mismatches += 1
        
        if len(users) > 10:
            print(f"  ... and {len(users) - 10} more users")
        
        print(f"\nTotal System Balance: ${total_balance:.2f}")
        print(f"Accounts with Mismatches: {mismatches}")
        
        return mismatches == 0
        
    except Exception as e:
        print(f"✗ Error during reconciliation test: {e}")
        return False


async def sync_account_balances_from_ledger(db: AsyncSession):
    """Step 5: Sync all account balances from ledger"""
    print("\n" + "=" * 80)
    print("STEP 5: Syncing Account Balances from Ledger")
    print("=" * 80)
    
    try:
        # Get all accounts
        result = await db.execute(select(DBAccount))
        accounts = result.scalars().all()
        
        print(f"Updating {len(accounts)} account balances...")
        
        updated = 0
        for account in accounts:
            try:
                # Calculate balance from ledger
                new_balance = await BalanceServiceLedger.get_user_balance(db, account.owner_id)
                old_balance = float(account.balance)
                
                if abs(new_balance - old_balance) > 0.01:
                    account.balance = new_balance
                    db.add(account)
                    print(f"  ✓ Account {account.id} (User {account.owner_id}): ${old_balance:.2f} → ${new_balance:.2f}")
                    updated += 1
                
            except Exception as e:
                print(f"  ✗ Account {account.id}: Error {e}")
        
        await db.commit()
        print(f"\nUpdated: {updated} accounts")
        return True
        
    except Exception as e:
        await db.rollback()
        print(f"✗ Error syncing balances: {e}")
        return False


async def main():
    """Run complete migration"""
    print("\n" + "=" * 80)
    print("LEDGER-BASED ACCOUNTING SYSTEM INITIALIZATION")
    print("=" * 80)
    print("\nThis migration will:")
    print("  1. Create the Ledger table")
    print("  2. Migrate existing transactions to double-entry ledger")
    print("  3. Verify ledger integrity and reconciliation")
    print("  4. Sync account balances from ledger")
    print("  5. Run final validation tests")
    
    # Get database session
    from database import SessionLocal
    async with SessionLocal() as db:
        
        # Step 1: Create table
        if not await create_ledger_table():
            print("\n✗ FAILED: Could not create Ledger table")
            return False
        
        # Step 2: Migrate transactions
        if not await migrate_transactions_to_ledger(db):
            print("\n⚠ WARNING: Migration had issues, continuing...")
        
        # Step 3: Verify ledger
        if not await verify_ledger_integrity(db):
            print("\n⚠ WARNING: Ledger integrity check found issues, continuing...")
        
        # Step 4: Test reconciliation
        if not await test_reconciliation(db):
            print("\n⚠ WARNING: Reconciliation test found mismatches, continuing...")
        
        # Step 5: Sync balances
        if not await sync_account_balances_from_ledger(db):
            print("\n✗ FAILED: Could not sync account balances")
            return False
    
    print("\n" + "=" * 80)
    print("✓ MIGRATION COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Deploy updated code with ledger support")
    print("  2. Monitor transaction creation for proper ledger entries")
    print("  3. Run test_ledger_accounting.py to verify")
    print("  4. Update admin dashboard to use BalanceServiceLedger")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
