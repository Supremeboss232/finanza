#!/usr/bin/env python3
"""
Database Seeding Script for System Reserve Account

This script ensures that:
1. System User (ID=1) exists with correct credentials
2. System Reserve Account (SYS-RESERVE-0001) exists and is properly funded
3. Ledger entries are properly initialized

Run this script after deploying or when setting up a new database.
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select
from database import SessionLocal
from models import User, Account, Ledger, Transaction
from auth_utils import get_password_hash


async def seed_system_reserve():
    """
    Seed the database with System User and System Reserve Account.
    
    This is idempotent - running it multiple times is safe.
    """
    async with SessionLocal() as db:
        print("\n" + "=" * 80)
        print("SYSTEM RESERVE ACCOUNT SEEDING")
        print("=" * 80)
        
        try:
            # Step 1: Check/Create System User (ID=1)
            print("\n[1/3] Checking System User (ID=1)...")
            result = await db.execute(select(User).filter(User.id == 1))
            system_user = result.scalars().first()
            
            if system_user:
                print(f"✅ System User already exists:")
                print(f"   - ID: {system_user.id}")
                print(f"   - Name: {system_user.full_name}")
                print(f"   - Email: {system_user.email}")
                print(f"   - Role: {'admin' if system_user.is_admin else 'user'}")
                print(f"   - Status: {'Active' if system_user.is_active else 'Inactive'}")
                print(f"   - KYC: {system_user.kyc_status}")
                
                # Update password if needed
                if system_user.email != "sysreserve@finanza.com":
                    print("\n⚠️  WARNING: System user email doesn't match spec!")
                    print(f"   Expected: sysreserve@finanza.com")
                    print(f"   Actual: {system_user.email}")
            else:
                # Create System User with exact specifications
                system_user = User(
                    id=1,  # Explicitly set ID to 1
                    full_name="System Reserve / Treasury",
                    email="sysreserve@finanza.com",
                    hashed_password=get_password_hash("Supposedbe5"),
                    is_active=True,
                    is_admin=True,
                    is_verified=True,
                    kyc_status='approved'
                )
                db.add(system_user)
                await db.flush()
                print("✅ System User created successfully:")
                print(f"   - ID: {system_user.id}")
                print(f"   - Name: {system_user.full_name}")
                print(f"   - Email: {system_user.email}")
                print(f"   - Role: admin")
                print(f"   - Status: Active")
                print(f"   - KYC: approved")
            
            # Step 2: Check/Create System Reserve Account
            print("\n[2/3] Checking System Reserve Account...")
            result = await db.execute(
                select(Account).filter(Account.account_number == "SYS-RESERVE-0001")
            )
            reserve_account = result.scalars().first()
            
            SEED_BALANCE = 10_000_000.0  # $10M
            
            if reserve_account:
                print(f"✅ System Reserve Account already exists:")
                print(f"   - Account Number: {reserve_account.account_number}")
                print(f"   - Type: {reserve_account.account_type}")
                print(f"   - Owner: User ID {reserve_account.owner_id}")
                print(f"   - Balance: ${reserve_account.balance:,.2f}")
                print(f"   - Currency: {reserve_account.currency}")
                print(f"   - Status: {reserve_account.status}")
                print(f"   - KYC Level: {reserve_account.kyc_level}")
                print(f"   - Is Admin Account: {reserve_account.is_admin_account}")
                
                # Check if balance needs updating
                if reserve_account.balance < SEED_BALANCE:
                    print(f"\n⚠️  Current balance (${reserve_account.balance:,.2f}) is below seed amount (${SEED_BALANCE:,.2f})")
                    print("   No automatic update - manual intervention may be needed")
            else:
                # Create System Reserve Account
                reserve_account = Account(
                    owner_id=1,  # System user
                    account_number="SYS-RESERVE-0001",
                    account_type="treasury",
                    balance=SEED_BALANCE,
                    currency="USD",
                    status="active",
                    kyc_level="full",
                    is_admin_account=True
                )
                db.add(reserve_account)
                await db.flush()
                print(f"✅ System Reserve Account created successfully:")
                print(f"   - Account Number: SYS-RESERVE-0001")
                print(f"   - Type: treasury")
                print(f"   - Owner: System User (ID=1)")
                print(f"   - Balance: ${SEED_BALANCE:,.2f}")
                print(f"   - Currency: USD")
                print(f"   - Status: active")
                print(f"   - KYC Level: full")
                print(f"   - Is Admin Account: True")
                
                # Step 3: Create initial transaction and ledger entry for seed balance
                print("\n[3/3] Creating Transaction and Ledger Entry for Seed Balance...")
                
                # First create the seed transaction (required for Ledger.transaction_id)
                seed_transaction = Transaction(
                    user_id=1,  # System user
                    account_id=reserve_account.id,
                    amount=SEED_BALANCE,
                    transaction_type="system_seed",
                    direction="credit",
                    status="completed",
                    description="System Reserve Account initialization seed"
                )
                db.add(seed_transaction)
                await db.flush()  # Get transaction.id
                
                # Now create the ledger entry with the transaction_id
                seed_ledger = Ledger(
                    user_id=1,  # System user
                    entry_type="credit",  # Money coming into the system
                    amount=Decimal(str(SEED_BALANCE)),
                    transaction_id=seed_transaction.id,  # Link to seed transaction
                    description="System Reserve Account initialization seed",
                    status="posted"
                )
                db.add(seed_ledger)
                print(f"✅ Transaction and Ledger entry created:")
                print(f"   - Transaction ID: {seed_transaction.id}")
                print(f"   - Ledger Entry ID: (will be generated on commit)")
                print(f"   - Amount: ${SEED_BALANCE:,.2f}")
                print(f"   - Type: credit")
                print(f"   - Description: System Reserve Account initialization seed")
                print(f"   - Status: posted")
            
            # Commit all changes
            await db.commit()
            
            # Final verification
            print("\n" + "=" * 80)
            print("VERIFICATION")
            print("=" * 80)
            
            # Re-fetch to show current state
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
            print("\nSystem User:")
            print(f"  • ID: {system_user.id}")
            print(f"  • Name: {system_user.full_name}")
            print(f"  • Email: {system_user.email}")
            print(f"  • Role: admin/system")
            print(f"  • Status: active")
            print(f"  • KYC: approved")
            
            print("\nSystem Reserve Account:")
            print(f"  • Account Number: {reserve_account.account_number}")
            print(f"  • Type: {reserve_account.account_type}")
            print(f"  • Balance: ${reserve_account.balance:,.2f}")
            print(f"  • Currency: {reserve_account.currency}")
            print(f"  • Status: {reserve_account.status}")
            print(f"  • KYC Level: {reserve_account.kyc_level}")
            
            print("\nLedger Summary:")
            print(f"  • Total Entries: {len(ledger_entries)}")
            total_credits = sum(float(e.amount) for e in ledger_entries if e.entry_type == "credit")
            total_debits = sum(float(e.amount) for e in ledger_entries if e.entry_type == "debit")
            print(f"  • Total Credits: ${total_credits:,.2f}")
            print(f"  • Total Debits: ${total_debits:,.2f}")
            print(f"  • Net Balance: ${total_credits - total_debits:,.2f}")
            
            print("\n" + "=" * 80)
            print("✅ DATABASE SEEDING COMPLETE")
            print("=" * 80 + "\n")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


async def verify_system_reserve():
    """Verify the system reserve account is properly configured."""
    async with SessionLocal() as db:
        try:
            # Check System User
            result = await db.execute(select(User).filter(User.id == 1))
            system_user = result.scalars().first()
            
            # Check System Reserve Account
            result = await db.execute(
                select(Account).filter(Account.account_number == "SYS-RESERVE-0001")
            )
            reserve_account = result.scalars().first()
            
            # Check Ledger
            result = await db.execute(select(Ledger).filter(Ledger.user_id == 1))
            ledger_entries = result.scalars().all()
            
            if system_user and reserve_account and ledger_entries:
                return True, {
                    "system_user": system_user,
                    "reserve_account": reserve_account,
                    "ledger_entries": ledger_entries
                }
            else:
                return False, {
                    "system_user_exists": system_user is not None,
                    "reserve_account_exists": reserve_account is not None,
                    "ledger_entries_exist": len(ledger_entries) > 0 if ledger_entries else False
                }
        
        except Exception as e:
            return False, {"error": str(e)}


async def main():
    """Main entry point."""
    try:
        # Seed the database
        await seed_system_reserve()
        
        # Verify
        is_valid, data = await verify_system_reserve()
        if is_valid:
            print("✅ System Reserve Account verified and ready!")
        else:
            print("⚠️  WARNING: Some components are missing:")
            print(data)
    
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
