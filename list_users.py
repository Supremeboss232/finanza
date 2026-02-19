#!/usr/bin/env python3
"""List all users in the database."""

import asyncio
from sqlalchemy import select
from database import SessionLocal
from models import User

async def list_users():
    """List all users."""
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print("\nAll Users:")
        print("=" * 80)
        for user in users:
            print(f"ID: {user.id}")
            print(f"  Email: {user.email}")
            print(f"  Name: {user.full_name}")
            print(f"  Account Number: {user.account_number}")
            print(f"  Is Admin: {user.is_admin}")
            print(f"  Is Active: {user.is_active}")
            print(f"  Is Verified: {user.is_verified}")
            print()

if __name__ == "__main__":
    asyncio.run(list_users())
