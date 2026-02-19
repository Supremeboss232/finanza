#!/usr/bin/env python3
"""
Debug script to identify fund transfer endpoint error.

Tests:
1. Check if SystemFundService is properly initialized
2. Test fund transfer with System Reserve Account
3. Check balance calculation
"""

import asyncio
import json
from decimal import Decimal
from sqlalchemy import select
from database import SessionLocal
from models import User, Account, Ledger, Transaction, AuditLog
from system_fund_service import SystemFundService

async def debug_fund_transfer():
    async with SessionLocal() as db:
        print("\n" + "="*80)
        print("DEBUG: Fund Transfer Issues")
        print("="*80)
        
        # Check 1: System Reserve Account exists
        print("\n[1/5] Checking System Reserve Account...")
        result = await db.execute(
            select(Account).filter(Account.account_number == "SYS-RESERVE-0001")
        )
        reserve = result.scalars().first()
        
        if not reserve:
            print("❌ System Reserve Account NOT FOUND")
            print("   This is the root cause of the 500 error")
            print("   Action: Run seed_system_reserve.py")
            return
        
        print(f"✅ System Reserve Account found:")
        print(f"   Account ID: {reserve.id}")
        print(f"   Number: {reserve.account_number}")
        print(f"   Balance: ${reserve.balance:,.2f}")
        print(f"   Owner ID: {reserve.owner_id}")
        
        # Check 2: System User exists
        print("\n[2/5] Checking System User (ID=1)...")
        result = await db.execute(select(User).filter(User.id == 1))
        sys_user = result.scalars().first()
        
        if not sys_user:
            print("❌ System User NOT FOUND")
            print("   Action: Run seed_system_reserve.py")
            return
        
        print(f"✅ System User found:")
        print(f"   ID: {sys_user.id}")
        print(f"   Email: {sys_user.email}")
        print(f"   Is Admin: {sys_user.is_admin}")
        
        # Check 3: Test user exists
        print("\n[3/5] Checking Test User (for fund transfer)...")
        result = await db.execute(select(User).filter(User.email == "testuser@finanza.com"))
        test_user = result.scalars().first()
        
        if test_user:
            print(f"✅ Test user exists (ID={test_user.id})")
        else:
            print("⚠️  Test user not found - creating...")
            from auth_utils import get_password_hash
            test_user = User(
                full_name="Test User",
                email="testuser@finanza.com",
                hashed_password=get_password_hash("test123"),
                is_active=True,
                is_verified=True,
                kyc_status='approved'
            )
            db.add(test_user)
            await db.flush()
            print(f"✅ Test user created (ID={test_user.id})")
        
        # Check 4: Test account exists
        print("\n[4/5] Checking Test Account...")
        result = await db.execute(
            select(Account).filter(Account.owner_id == test_user.id)
        )
        test_account = result.scalars().first()
        
        if test_account:
            print(f"✅ Test account exists (ID={test_account.id})")
        else:
            print("⚠️  Test account not found - creating...")
            test_account = Account(
                owner_id=test_user.id,
                account_number=f"TEST-{test_user.id:06d}",
                account_type="checking",
                balance=0.0,
                currency="USD",
                status="active",
                kyc_level="full"
            )
            db.add(test_account)
            await db.flush()
            print(f"✅ Test account created (ID={test_account.id})")
        
        # Check 5: Try fund transfer
        print("\n[5/5] Testing Fund Transfer...")
        try:
            result = await SystemFundService.fund_user_from_system(
                db=db,
                target_user_id=test_user.id,
                target_account_id=test_account.id,
                amount=100.0,
                admin_user_id=1,
                reason="Debug test"
            )
            
            if result.get('success'):
                print("✅ Fund transfer successful!")
                print(f"   Transaction ID: {result.get('transaction_id')}")
                print(f"   Debit Entry ID: {result.get('debit_entry_id')}")
                print(f"   Credit Entry ID: {result.get('credit_entry_id')}")
                print(f"   New Balance: ${result.get('new_balance'):,.2f}")
            else:
                print(f"❌ Fund transfer failed: {result.get('error')}")
                print("\nFull result:")
                print(json.dumps(result, indent=2, default=str))
        except Exception as e:
            print(f"❌ Exception during fund transfer: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*80)
        print("DEBUG COMPLETE")
        print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(debug_fund_transfer())
