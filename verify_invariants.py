#!/usr/bin/env python
"""
VERIFY USER-ACCOUNT INVARIANTS IN DATABASE

This script checks for violations of the core invariant:
"Every user must have BOTH a User ID and an Account ID"

Run this to:
1. Find orphaned users (user with no account)
2. Find orphaned accounts (account with no user)
3. Find transactions without account_id
4. Report all invariant violations

Usage:
    python verify_invariants.py
"""

import asyncio
import logging
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import SessionLocal
from models import User as DBUser, Account as DBAccount, Transaction as DBTransaction

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class InvariantChecker:
    """Check database for invariant violations"""
    
    @staticmethod
    async def check_orphaned_users(db: AsyncSession):
        """Find users without accounts"""
        log.info("🔍 Checking for orphaned users (users without accounts)...")
        
        # Query: Users with no associated account
        result = await db.execute(
            select(DBUser).filter(
                ~DBUser.accounts.any()  # SQLAlchemy relationship negation
            )
        )
        orphaned = result.scalars().all()
        
        if orphaned:
            log.critical(f"🚨 Found {len(orphaned)} orphaned users:")
            for user in orphaned:
                log.critical(
                    f"   ❌ User ID {user.id}: {user.email} "
                    f"(created: {user.created_at})"
                )
            return len(orphaned), orphaned
        else:
            log.info("✅ No orphaned users found")
            return 0, []
    
    @staticmethod
    async def check_orphaned_accounts(db: AsyncSession):
        """Find accounts without users"""
        log.info("🔍 Checking for orphaned accounts (accounts without users)...")
        
        result = await db.execute(
            select(DBAccount).filter(
                ~DBAccount.owner.any()  # Accounts with no owner
            )
        )
        orphaned = result.scalars().all()
        
        if orphaned:
            log.critical(f"🚨 Found {len(orphaned)} orphaned accounts:")
            for account in orphaned:
                log.critical(
                    f"   ❌ Account ID {account.id}: {account.account_number} "
                    f"(owner_id: {account.owner_id})"
                )
            return len(orphaned), orphaned
        else:
            log.info("✅ No orphaned accounts found")
            return 0, []
    
    @staticmethod
    async def check_transactions_without_account(db: AsyncSession):
        """Find transactions without account_id"""
        log.info("🔍 Checking for transactions without account_id...")
        
        result = await db.execute(
            select(DBTransaction).filter(
                (DBTransaction.account_id == None) |
                (DBTransaction.account_id == 0)
            )
        )
        invalid = result.scalars().all()
        
        if invalid:
            log.critical(f"🚨 Found {len(invalid)} transactions without account_id:")
            for tx in invalid:
                log.critical(
                    f"   ❌ Transaction ID {tx.id}: user_id={tx.user_id}, "
                    f"account_id={tx.account_id}"
                )
            return len(invalid), invalid
        else:
            log.info("✅ No transactions without account_id found")
            return 0, []
    
    @staticmethod
    async def check_users_without_kyc_status(db: AsyncSession):
        """Find users without KYC status"""
        log.info("🔍 Checking for users without KYC status...")
        
        result = await db.execute(
            select(DBUser).filter(
                (DBUser.kyc_status == None) | 
                (DBUser.kyc_status == '')
            )
        )
        invalid = result.scalars().all()
        
        if invalid:
            log.critical(f"🚨 Found {len(invalid)} users without KYC status:")
            for user in invalid:
                log.critical(
                    f"   ❌ User ID {user.id}: {user.email} "
                    f"(kyc_status: '{user.kyc_status}')"
                )
            return len(invalid), invalid
        else:
            log.info("✅ All users have KYC status set")
            return 0, []
    
    @staticmethod
    async def generate_report(db: AsyncSession):
        """Generate comprehensive invariant violation report"""
        log.info("\n" + "="*70)
        log.info("USER-ACCOUNT INVARIANT VERIFICATION REPORT")
        log.info("="*70 + "\n")
        
        violations = 0
        
        # Check 1: Orphaned users
        orphaned_user_count, orphaned_users = await InvariantChecker.check_orphaned_users(db)
        violations += orphaned_user_count
        
        # Check 2: Orphaned accounts
        orphaned_account_count, orphaned_accounts = await InvariantChecker.check_orphaned_accounts(db)
        violations += orphaned_account_count
        
        # Check 3: Transactions without account
        invalid_tx_count, invalid_txs = await InvariantChecker.check_transactions_without_account(db)
        violations += invalid_tx_count
        
        # Check 4: Users without KYC status
        no_kyc_count, no_kyc_users = await InvariantChecker.check_users_without_kyc_status(db)
        violations += no_kyc_count
        
        log.info("\n" + "="*70)
        if violations == 0:
            log.info("✅ ALL CHECKS PASSED - System is compliant!")
            log.info("   Every user has an account")
            log.info("   Every account has a user")
            log.info("   All transactions have account_id")
            log.info("   All users have KYC status")
        else:
            log.critical(f"⚠️  FOUND {violations} INVARIANT VIOLATIONS!")
            log.critical("   The system has core integrity issues.")
            log.critical("   Please run fix_orphaned_users.py to resolve.")
        log.info("="*70 + "\n")
        
        return {
            "total_violations": violations,
            "orphaned_users": orphaned_user_count,
            "orphaned_accounts": orphaned_account_count,
            "invalid_transactions": invalid_tx_count,
            "users_without_kyc": no_kyc_count
        }


async def main():
    """Run invariant checks"""
    async with SessionLocal() as db:
        report = await InvariantChecker.generate_report(db)
        return report


if __name__ == "__main__":
    result = asyncio.run(main())
    
    # Exit with error code if violations found
    import sys
    if result["total_violations"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)
