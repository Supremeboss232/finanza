#!/usr/bin/env python3
"""
Get all active user accounts with login information
"""

import asyncio
import sys
from sqlalchemy import select
from database import SessionLocal
from models import User, Account

async def get_active_accounts():
    """Retrieve all active user accounts"""
    
    async with SessionLocal() as db:
        # Query all active users
        result = await db.execute(
            select(User).where(User.is_active == True).order_by(User.id)
        )
        users = result.scalars().all()
        
        if not users:
            print("No active accounts found.")
            return
        
        print("\n" + "="*100)
        print("ACTIVE USER ACCOUNTS")
        print("="*100)
        print(f"\n{'ID':<5} {'Email':<30} {'Name':<25} {'Is Admin':<10} {'KYC Status':<15} {'Verified':<10}")
        print("-"*100)
        
        for user in users:
            admin_badge = "⭐ ADMIN" if user.is_admin else "User"
            verified = "✓ Yes" if user.is_verified else "✗ No"
            print(f"{user.id:<5} {user.email:<30} {user.full_name:<25} {admin_badge:<10} {user.kyc_status:<15} {verified:<10}")
        
        print("\n" + "="*100)
        print("USER ACCOUNTS DETAILS")
        print("="*100 + "\n")
        
        for user in users:
            print(f"User ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.full_name}")
            print(f"  Account Number: {user.account_number}")
            print(f"  Is Admin: {'Yes ⭐' if user.is_admin else 'No'}")
            print(f"  Is Active: {'Yes ✓' if user.is_active else 'No ✗'}")
            print(f"  Is Verified: {'Yes ✓' if user.is_verified else 'No ✗'}")
            print(f"  KYC Status: {user.kyc_status}")
            print(f"  Created: {user.created_at}")
            
            # Get associated accounts
            result_accounts = await db.execute(
                select(Account).where(Account.owner_id == user.id)
            )
            accounts = result_accounts.scalars().all()
            
            if accounts:
                print(f"  Associated Accounts: {len(accounts)}")
                for acc in accounts:
                    print(f"    - {acc.account_number} ({acc.account_type}): ${acc.balance:.2f} {acc.currency}")
            else:
                print(f"  Associated Accounts: None")
            
            print()

async def main():
    try:
        await get_active_accounts()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
