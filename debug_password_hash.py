#!/usr/bin/env python3
"""
Debug script to check password hashing and database state
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config import settings
import models
from auth_utils import get_password_hash, verify_password

async def check_database():
    """Check database and verify password hashing"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Get admin user
            result = await db.execute(select(models.User).filter(models.User.email == "admin@admin.com"))
            admin = result.scalar_one_or_none()
            
            if admin:
                print("=" * 70)
                print("ADMIN USER STATUS")
                print("=" * 70)
                print(f"Email: {admin.email}")
                print(f"Full Name: {admin.full_name}")
                print(f"ID: {admin.id}")
                print(f"Is Admin: {admin.is_admin}")
                print(f"Hashed Password (first 50 chars): {admin.hashed_password[:50]}...")
                print(f"Password hash type: {admin.hashed_password[:8]}")  # Show hash type prefix
                
                # Test password verification
                print("\n" + "=" * 70)
                print("PASSWORD VERIFICATION TEST")
                print("=" * 70)
                
                test_passwords = [
                    "admin123",
                    "test123",
                    "password"
                ]
                
                for pwd in test_passwords:
                    is_valid = verify_password(pwd, admin.hashed_password)
                    print(f"Password '{pwd}': {'✅ VALID' if is_valid else '❌ INVALID'}")
                
                # Test hashing a new password
                print("\n" + "=" * 70)
                print("NEW PASSWORD HASH TEST")
                print("=" * 70)
                
                new_pwd = "newtest123"
                new_hash = get_password_hash(new_pwd)
                print(f"Original password: {new_pwd}")
                print(f"New hash: {new_hash[:50]}...")
                print(f"New hash type: {new_hash[:8]}")
                
                # Test if the new hash can be verified
                is_valid = verify_password(new_pwd, new_hash)
                print(f"Verify new hash with original password: {'✅ VALID' if is_valid else '❌ INVALID'}")
                
            else:
                print("❌ Admin user not found")
            
            # Check other users
            print("\n" + "=" * 70)
            print("ALL USERS IN DATABASE")
            print("=" * 70)
            
            result = await db.execute(select(models.User).limit(10))
            users = result.scalars().all()
            
            for user in users:
                print(f"ID: {user.id:3} | Email: {user.email:30} | Is Admin: {user.is_admin} | Active: {user.is_active}")
    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_database())
