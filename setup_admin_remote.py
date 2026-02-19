#!/usr/bin/env python
"""
Simple script to update admin user directly (for local/sync usage).
Run this on the server where the application is deployed.
"""

import sys
import asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.insert(0, '/home/ec2-user/financial-services-website-template')

from config import settings
from auth_utils import get_password_hash
from app.models import User, Base
from app.database import engine, SessionLocal

async def setup_admin():
    """Create or update admin user."""
    print("\n🔄 Setting up admin user in database...")
    print(f"   Database: {settings.DATABASE_URL.split('@')[1]}")
    print(f"   Admin Email: {settings.ADMIN_EMAIL}")
    print(f"   Admin Password: {settings.ADMIN_PASSWORD}")

    async with SessionLocal() as session:
        try:
            # Check if admin exists
            result = await session.execute(
                select(User).filter(User.email == settings.ADMIN_EMAIL)
            )
            admin = result.scalars().first()

            if admin:
                print(f"✓ Found existing admin")
                admin.full_name = "Admin User"
                admin.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
                admin.is_admin = True
                admin.is_active = True
            else:
                print(f"✗ Admin not found, creating new...")
                admin = User(
                    full_name="Admin User",
                    email=settings.ADMIN_EMAIL,
                    hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                    is_admin=True,
                    is_active=True
                )
                session.add(admin)

            await session.commit()
            print(f"✅ Admin user ready!")
            print(f"\n   Login with:")
            print(f"   Email: {settings.ADMIN_EMAIL}")
            print(f"   Password: {settings.ADMIN_PASSWORD}\n")

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(setup_admin())
