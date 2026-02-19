#!/usr/bin/env python3
"""
Debug the exact password reset issue
Trace: Admin updates password -> Check database -> Try to login
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config import settings
import models
from auth_utils import get_password_hash, verify_password
import admin_service

async def debug_password_reset():
    """Debug the password reset flow step by step"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Get a test user
            result = await db.execute(
                select(models.User).where(models.User.email == "awehbaba@gmail.com")
            )
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ User not found!")
                return
            
            print("=" * 80)
            print("INITIAL STATE")
            print("=" * 80)
            print(f"User: {user.email}")
            print(f"Current hash: {user.hashed_password[:60]}...")
            
            # Test if admin can verify old password
            test_old = "test123"
            result_old = verify_password(test_old, user.hashed_password)
            print(f"Old password '{test_old}' verifies: {result_old}")
            
            # Now simulate what admin_service.update_user does
            print("\n" + "=" * 80)
            print("SIMULATING ADMIN PASSWORD UPDATE")
            print("=" * 80)
            
            new_password = "DebugTest123!"
            updates = {"password": new_password}
            
            print(f"Updates dict: {updates}")
            print(f"Calling admin_service.update_user()...")
            
            updated_user = await admin_service.AdminService.update_user(db, user.id, updates)
            
            print(f"Update returned, refreshing from DB...")
            
            # Fetch from database to see what was actually saved
            result = await db.execute(
                select(models.User).where(models.User.id == user.id)
            )
            user_from_db = result.scalar_one_or_none()
            
            print(f"\nDatabase hash: {user_from_db.hashed_password[:60]}...")
            
            # Test verification
            print("\n" + "=" * 80)
            print("VERIFICATION TESTS")
            print("=" * 80)
            
            test_new = "DebugTest123!"
            result_new = verify_password(test_new, user_from_db.hashed_password)
            print(f"New password '{test_new}' verifies: {result_new}")
            
            result_old_after = verify_password(test_old, user_from_db.hashed_password)
            print(f"Old password '{test_old}' verifies: {result_old_after}")
            
            if result_new and not result_old_after:
                print("\n✅ PASSWORD RESET WORKING!")
            else:
                print("\n❌ PASSWORD RESET NOT WORKING!")
                
                # Debug what hash was actually created
                print("\nDEBUGGING:")
                manual_hash = get_password_hash(new_password)
                print(f"Manual hash of '{new_password}': {manual_hash[:60]}...")
                print(f"Stored hash in DB:              {user_from_db.hashed_password[:60]}...")
                print(f"Hashes match: {manual_hash == user_from_db.hashed_password}")
                
                # Test the manual hash
                test_manual = verify_password(new_password, manual_hash)
                print(f"Manual hash verifies new password: {test_manual}")

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(debug_password_reset())
