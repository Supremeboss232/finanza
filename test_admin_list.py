#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, 'C:\\Users\\Aweh\\Downloads\\supreme\\financial-services-website-template')

from sqlalchemy import select
from database import SessionLocal
from models import User as DBUser

async def check_admins():
    """Check what admins exist in the database"""
    async with SessionLocal() as session:
        # Query admins
        result = await session.execute(
            select(DBUser).where(
                (DBUser.is_admin == True) &
                (DBUser.is_active == True)
            )
        )
        admins = result.scalars().all()
        
        print(f"Active admins with is_admin=True: {len(admins)}")
        for admin in admins:
            print(f"  - {admin.email}: {admin.admin_role} (is_admin={admin.is_admin}, is_active={admin.is_active})")
        
        # Check all users with admin role
        result2 = await session.execute(
            select(DBUser).where(DBUser.admin_role.isnot(None))
        )
        admin_role_users = result2.scalars().all()
        print(f"\nUsers with admin_role set: {len(admin_role_users)}")
        for admin in admin_role_users:
            print(f"  - {admin.email}: is_admin={admin.is_admin}, admin_role={admin.admin_role}, is_active={admin.is_active}")

if __name__ == "__main__":
    asyncio.run(check_admins())
