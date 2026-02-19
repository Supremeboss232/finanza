#!/usr/bin/env python3
"""List all admin users in the database."""

import asyncio
from app.database import SessionLocal
from app.models import User
from sqlalchemy.future import select


async def list_admins():
    """List all admin users."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.is_admin == True)
        )
        admins = result.scalars().all()
        
        if not admins:
            print("❌ No admin users found!")
            return
        
        print(f"✅ Found {len(admins)} admin user(s):\n")
        for admin in admins:
            print(f"  Email: {admin.email}")
            print(f"  Full Name: {admin.full_name}")
            print(f"  User ID: {admin.id}")
            print(f"  Active: {'Yes' if admin.is_active else 'No'}")
            print()


if __name__ == "__main__":
    asyncio.run(list_admins())
