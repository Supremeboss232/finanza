#!/usr/bin/env python
"""Check if KYC rejection properly unlocked profile"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from models import User, KYCInfo

async def check_kyc_status():
    """Check current KYC status after rejection"""
    async with get_session() as db_session:
        # Get all users with KYC info
        result = await db_session.execute(
            select(User, KYCInfo).outerjoin(KYCInfo)
        )
        rows = result.all()
        
        if not rows:
            print("No users found")
            return
        
        print("\n" + "="*80)
        print("KYC STATUS REPORT")
        print("="*80)
        
        for user, kyc_info in rows:
            print(f"\n👤 User: {user.email}")
            print(f"   ID: {user.id}")
            print(f"   User KYC Status: {user.kyc_status}")
            
            if kyc_info:
                print(f"\n   KYCInfo Details:")
                print(f"   ├─ kyc_status: {kyc_info.kyc_status}")
                print(f"   ├─ status: {kyc_info.status}")
                print(f"   ├─ kyc_submitted: {kyc_info.kyc_submitted}")
                print(f"   ├─ submission_locked: {kyc_info.submission_locked}")
                print(f"   ├─ rejection_reason: {kyc_info.rejection_reason}")
                print(f"   └─ reviewed_at: {kyc_info.reviewed_at}")
                
                # Check if profile should be locked
                is_locked = kyc_info and kyc_info.kyc_submitted
                print(f"\n   [LOCK] Profile Locked? {is_locked}")
                
                if not is_locked:
                    print(f"   [OK] Profile is OPEN for updates!")
                else:
                    print(f"   [FAIL] Profile is LOCKED - KYC under review")
            else:
                print(f"   [FAIL] No KYC info found")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(check_kyc_status())
