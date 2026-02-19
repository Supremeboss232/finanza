#!/usr/bin/env python3
"""
Migration Script: Update System User and Seed Reserve Account

This script:
1. Updates the existing System User (ID=1) to match specifications
2. Seeds the System Reserve Account with $10M
3. Creates proper ledger entries
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select
from database import SessionLocal
from models import User, Account, Ledger, Transaction
from auth_utils import get_password_hash


async def migrate_system_reserve():
    """Migrate existing system account to new spec and seed it."""
    async with SessionLocal() as db:
        print("\n" + "=" * 80)
        print("SYSTEM RESERVE ACCOUNT MIGRATION")
        print("=" * 80)
        
        try:
            # Step 1: Update System User
            print("\n[1/3] Updating System User (ID=1) to match spec...")
            result = await db.execute(select(User).filter(User.id == 1))
            system_user = result.scalars().first()
            
            if system_user:
                print(f"Current System User:")
                print(f"  • Name: {system_user.full_name}")
                print(f"  • Email: {system_user.email}")
                
                # Update to match spec
                system_user.full_name = "System Reserve / Treasury"
                system_user.email = "sysreserve@finanza.com"
                system_user.hashed_password = get_password_hash("Supposedbe5")
                system_user.is_active = True
                system_user.is_admin = True
                system_user.is_verified = True
                system_user.kyc_status = 'approved'
                
                db.add(system_user)
                await db.flush()
                
                print(f"✅ Updated System User:")
                print(f"  • Name: {system_user.full_name}")
                print(f"  • Email: {system_user.email}")
                print(f"  • Password: Supposedbe5 (hashed)")
                print(f"  • Role: admin")
                print(f"  • Status: active")
                print(f"  • KYC: approved")
            
            # Step 2: Update System Reserve Account
            print("\n[2/3] Updating System Reserve Account...")
            result = await db.execute(
                select(Account).filter(Account.account_number == "SYS-RESERVE-0001")
            )
            reserve_account = result.scalars().first()
            
            SEED_BALANCE = 10_000_000.0
            
            if reserve_account:
                print(f"Current System Reserve Account:")
                print(f"  • Type: {reserve_account.account_type}")
                print(f"  • Balance: ${reserve_account.balance:,.2f}")
                print(f"  • KYC Level: {reserve_account.kyc_level}")
                
                # Update to match spec
                reserve_account.account_type = "treasury"
                reserve_account.balance = SEED_BALANCE
                reserve_account.kyc_level = "full"
                reserve_account.is_admin_account = True
                
                db.add(reserve_account)
                await db.flush()
                
                print(f"✅ Updated System Reserve Account:")
                print(f"  • Account Number: SYS-RESERVE-0001")
                print(f"  • Type: treasury")
                print(f"  • Balance: ${SEED_BALANCE:,.2f}")
                print(f"  • KYC Level: full")
                print(f"  • Is Admin Account: True")
            
            # Step 3: Create/Update Ledger Entry
            print("\n[3/3] Creating Ledger Entry for Seed Balance...")
            
            # Check if seed entry exists
            result = await db.execute(
                select(Ledger).filter(
                    Ledger.user_id == 1,
                    Ledger.description.contains("initialization seed")
                )
            )
            existing_entry = result.scalars().first()
            
            if existing_entry:
                print(f"⚠️  Ledger entry already exists")
                print(f"   No additional entry created")
            else:
                # Create a Transaction first (required by Ledger.transaction_id constraint)
                seed_transaction = Transaction(
                    user_id=1,
                    account_id=reserve_account.id,
                    amount=10_000_000.0,
                    transaction_type="system_seed",
                    direction="credit",
                    status="completed",
                    description="System Reserve Account initialization seed"
                )
                db.add(seed_transaction)
                await db.flush()  # Get transaction.id
                
                # Now create the ledger entry with the transaction_id
                seed_ledger = Ledger(
                    user_id=1,
                    entry_type="credit",
                    amount=Decimal(str(SEED_BALANCE)),
                    transaction_id=seed_transaction.id,
                    description="System Reserve Account initialization seed",
                    status="posted"
                )
                db.add(seed_ledger)
                await db.flush()
                
                print(f"✅ Created Transaction and Ledger Entry:")
                print(f"  • Transaction ID: {seed_transaction.id}")
                print(f"  • Ledger Entry ID: {seed_ledger.id}")
                print(f"  • Amount: ${SEED_BALANCE:,.2f}")
                print(f"  • Type: credit")
                print(f"  • Status: posted")
            
            # Commit all changes
            await db.commit()
            
            # Final verification
            print("\n" + "=" * 80)
            print("FINAL STATE")
            print("=" * 80)
            
            result = await db.execute(select(User).filter(User.id == 1))
            system_user = result.scalars().first()
            
            result = await db.execute(
                select(Account).filter(Account.account_number == "SYS-RESERVE-0001")
            )
            reserve_account = result.scalars().first()
            
            result = await db.execute(
                select(Ledger).filter(Ledger.user_id == 1)
            )
            ledger_entries = result.scalars().all()
            
            print("\n✅ SYSTEM RESERVE ACCOUNT READY FOR OPERATIONS")
            print("\nSystem User (ID=1):")
            print(f"  • Name: {system_user.full_name}")
            print(f"  • Email: {system_user.email}")
            print(f"  • Role: admin/system")
            print(f"  • Status: active")
            print(f"  • KYC: approved")
            
            print("\nSystem Reserve Account:")
            print(f"  • Account Number: SYS-RESERVE-0001")
            print(f"  • Type: {reserve_account.account_type}")
            print(f"  • Balance: ${reserve_account.balance:,.2f}")
            print(f"  • KYC Level: {reserve_account.kyc_level}")
            print(f"  • Is Admin Account: {reserve_account.is_admin_account}")
            
            print("\nLedger Summary:")
            print(f"  • Total Entries: {len(ledger_entries)}")
            total_credits = sum(float(e.amount) for e in ledger_entries if e.entry_type == "credit")
            total_debits = sum(float(e.amount) for e in ledger_entries if e.entry_type == "debit")
            print(f"  • Total Credits: ${total_credits:,.2f}")
            print(f"  • Total Debits: ${total_debits:,.2f}")
            print(f"  • Net Balance: ${total_credits - total_debits:,.2f}")
            
            print("\n" + "=" * 80)
            print("✅ MIGRATION COMPLETE")
            print("=" * 80 + "\n")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(migrate_system_reserve())
