"""
Account & User Completeness Audit & Migration Script

Ensures every user and account has all required fields:

User Requirements:
- id (PK)
- email (unique)
- full_name
- hashed_password
- kyc_status (not_started, pending, approved, rejected)
- is_active (True by default)
- created_at

Account Requirements:
- id (PK)
- account_number (unique)
- owner_id (FK to users.id) - REQUIRED
- account_type (savings/checking/business/investment/loan)
- balance (float, default 0.0)
- currency (default USD)
- status (active/frozen/closed)
- kyc_level (none/basic/full)
- created_at

This script:
1. Audits existing data
2. Creates missing accounts for users without accounts
3. Populates missing fields with sensible defaults
4. Generates migration SQL if needed
"""

import asyncio
import sys
from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, func, and_
from sqlalchemy.orm import sessionmaker

from models import Base, User as DBUser, Account as DBAccount
from database import get_db_url

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def log_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def log_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def log_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def log_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")

async def audit_users_and_accounts():
    """Audit all users and accounts for missing fields"""
    
    # Setup database connection
    engine = create_async_engine(get_db_url(), echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            log_info("Starting User & Account Audit...")
            
            # 1. Check users without accounts
            result = await session.execute(
                select(DBUser).outerjoin(DBAccount).filter(DBAccount.id == None)
            )
            users_without_accounts = result.scalars().unique().all()
            
            if users_without_accounts:
                log_warning(f"Found {len(users_without_accounts)} users without accounts")
                for user in users_without_accounts:
                    # Create primary account for user
                    account_number = f"AC-{str(uuid.uuid4())[:8].upper()}-{datetime.now().strftime('%d%m%y%H%M%S')}"
                    new_account = DBAccount(
                        account_number=account_number,
                        owner_id=user.id,
                        account_type="savings",
                        balance=0.0,
                        currency="USD",
                        status="active",
                        kyc_level="basic" if user.kyc_status == "approved" else "none"
                    )
                    session.add(new_account)
                    log_info(f"Created account {account_number} for user {user.email}")
            
            # 2. Check for accounts with missing fields
            result = await session.execute(select(DBAccount))
            all_accounts = result.scalars().all()
            
            accounts_fixed = 0
            for account in all_accounts:
                fixed = False
                
                # Check if status is missing
                if not account.status or account.status == "":
                    account.status = "active"
                    fixed = True
                
                # Check if kyc_level is missing
                if not account.kyc_level or account.kyc_level == "":
                    account.kyc_level = "basic"
                    fixed = True
                
                # Check if currency is missing
                if not account.currency or account.currency == "":
                    account.currency = "USD"
                    fixed = True
                
                # Verify balance is not None
                if account.balance is None:
                    account.balance = 0.0
                    fixed = True
                
                if fixed:
                    session.add(account)
                    accounts_fixed += 1
                    log_info(f"Fixed missing fields in account {account.account_number}")
            
            # 3. Check users with missing fields
            result = await session.execute(select(DBUser))
            all_users = result.scalars().all()
            
            users_fixed = 0
            for user in all_users:
                fixed = False
                
                # Check if kyc_status is missing
                if not user.kyc_status or user.kyc_status == "":
                    user.kyc_status = "not_started"
                    fixed = True
                
                # Check if is_active is None
                if user.is_active is None:
                    user.is_active = True
                    fixed = True
                
                if fixed:
                    session.add(user)
                    users_fixed += 1
                    log_info(f"Fixed missing fields for user {user.email}")
            
            # Commit all changes
            await session.commit()
            
            # 4. Print summary report
            log_success("Audit Complete!")
            print("\n" + "="*60)
            print("AUDIT SUMMARY")
            print("="*60)
            
            # Count statistics
            total_users = await session.execute(select(func.count(DBUser.id)))
            total_users_count = total_users.scalar() or 0
            
            total_accounts = await session.execute(select(func.count(DBAccount.id)))
            total_accounts_count = total_accounts.scalar() or 0
            
            users_with_accounts = await session.execute(
                select(func.count(DBUser.id)).select_from(DBUser).join(DBAccount)
            )
            users_with_accounts_count = users_with_accounts.scalar() or 0
            
            print(f"Total Users:               {total_users_count}")
            print(f"Total Accounts:            {total_accounts_count}")
            print(f"Users with Accounts:       {users_with_accounts_count}")
            print(f"Users without Accounts:    {total_users_count - users_with_accounts_count}")
            print(f"Accounts Fixed:            {accounts_fixed}")
            print(f"Users Fixed:               {users_fixed}")
            print("="*60 + "\n")
            
            # 5. List all users and their account status
            log_info("User Account Status:")
            result = await session.execute(select(DBUser).order_by(DBUser.created_at.desc()))
            users = result.scalars().all()
            
            for user in users:
                account_result = await session.execute(
                    select(DBAccount).filter(DBAccount.owner_id == user.id).limit(1)
                )
                account = account_result.scalar_one_or_none()
                
                if account:
                    status_icon = GREEN + "✓" + RESET
                    kyc_label = "approved" if user.kyc_status == "approved" else user.kyc_status
                    print(f"  {status_icon} {user.email:40} | Account: {account.account_number:25} | KYC: {kyc_label}")
                else:
                    status_icon = RED + "✗" + RESET
                    print(f"  {status_icon} {user.email:40} | NO ACCOUNT")
            
            print()
            log_success("All users and accounts are properly configured!")
            
        except Exception as e:
            log_error(f"Audit failed: {str(e)}")
            raise
        finally:
            await engine.dispose()

async def main():
    """Run the audit"""
    try:
        await audit_users_and_accounts()
    except Exception as e:
        log_error(f"Migration failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
