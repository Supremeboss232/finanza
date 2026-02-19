#!/usr/bin/env python
"""
FIX ORPHANED USERS - Create missing accounts

This script fixes invariant violations by:
1. Finding all users without accounts
2. Creating primary accounts for them
3. Setting KYC status if missing
4. Logging all repairs

Usage:
    python fix_orphaned_users.py
"""

import asyncio
import logging
import time
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import SessionLocal
from models import User as DBUser, Account as DBAccount

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class OrphanedUserFixer:
    """Fix users without accounts"""
    
    @staticmethod
    async def fix_orphaned_users(db: AsyncSession):
        """Create accounts for all orphaned users"""
        log.info("🔧 Starting orphaned user fix...")
        
        # Find all users without accounts
        result = await db.execute(
            select(DBUser).filter(
                ~DBUser.accounts.any()
            )
        )
        orphaned_users = result.scalars().all()
        
        if not orphaned_users:
            log.info("✅ No orphaned users found - system is clean!")
            return 0, []
        
        log.warning(f"⚠️  Found {len(orphaned_users)} orphaned users - creating accounts...")
        
        fixed_count = 0
        fixes = []
        
        for user in orphaned_users:
            try:
                log.info(f"  Processing user {user.id}: {user.email}")
                
                # Ensure KYC status is set
                if not user.kyc_status:
                    user.kyc_status = 'not_started'
                    log.info(f"    ✓ Set kyc_status='not_started'")
                
                # Create primary account
                account_number = f"ACC{user.id}_{int(time.time() * 1000000) % 1000000}"
                primary_account = DBAccount(
                    owner_id=user.id,
                    account_number=account_number,
                    account_type='primary',
                    balance=0.0,
                    currency='USD'
                )
                db.add(primary_account)
                
                # Update user's account_number field for quick reference
                if not user.account_number:
                    user.account_number = account_number
                
                await db.flush()
                
                log.info(f"    ✓ Created account: {account_number}")
                fixes.append({
                    "user_id": user.id,
                    "email": user.email,
                    "account_id": primary_account.id,
                    "account_number": account_number,
                    "status": "fixed"
                })
                fixed_count += 1
                
            except Exception as e:
                log.error(f"    ❌ Error fixing user {user.id}: {e}")
                fixes.append({
                    "user_id": user.id,
                    "email": user.email,
                    "status": "error",
                    "error": str(e)
                })
        
        # Commit all fixes
        await db.commit()
        
        log.info(f"\n✅ Fixed {fixed_count} orphaned users")
        return fixed_count, fixes
    
    @staticmethod
    async def fix_kyc_status(db: AsyncSession):
        """Ensure all users have KYC status"""
        log.info("🔧 Checking KYC status...")
        
        result = await db.execute(
            select(DBUser).filter(
                (DBUser.kyc_status == None) | (DBUser.kyc_status == '')
            )
        )
        users = result.scalars().all()
        
        if not users:
            log.info("✅ All users have KYC status")
            return 0
        
        log.warning(f"⚠️  Found {len(users)} users without KYC status - fixing...")
        
        for user in users:
            user.kyc_status = 'not_started'
            log.info(f"  ✓ User {user.id}: kyc_status='not_started'")
        
        await db.commit()
        log.info(f"✅ Fixed {len(users)} users")
        return len(users)


async def main():
    """Run the fix"""
    async with SessionLocal() as db:
        log.info("="*70)
        log.info("ORPHANED USER FIX SCRIPT")
        log.info("="*70 + "\n")
        
        # Fix orphaned users
        fixed_count, fixes = await OrphanedUserFixer.fix_orphaned_users(db)
        
        # Fix missing KYC status
        kyc_fixed = await OrphanedUserFixer.fix_kyc_status(db)
        
        log.info("\n" + "="*70)
        log.info("✅ FIX COMPLETE")
        log.info(f"  Orphaned users fixed: {fixed_count}")
        log.info(f"  KYC status fixed: {kyc_fixed}")
        log.info("="*70 + "\n")
        
        return {
            "orphaned_users_fixed": fixed_count,
            "kyc_status_fixed": kyc_fixed,
            "fixes": fixes
        }


if __name__ == "__main__":
    result = asyncio.run(main())
    
    import sys
    if result["orphaned_users_fixed"] > 0 or result["kyc_status_fixed"] > 0:
        log.info("⚠️  System was not compliant - fixes applied.")
        log.info("   Please run verify_invariants.py to confirm.")
        sys.exit(0)  # Success
    else:
        log.info("✅ System was already compliant.")
        sys.exit(0)
