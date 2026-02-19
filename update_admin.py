#!/usr/bin/env python
"""
Script to update or create admin user in the database.
Usage: python update_admin.py
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import settings
from auth_utils import get_password_hash
from app.models import User

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
)

# Create async session
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def update_or_create_admin():
    """Update or create admin user in database."""
    async with AsyncSessionLocal() as session:
        try:
            # Check if admin exists
            result = await session.execute(
                select(User).filter(User.email == settings.ADMIN_EMAIL)
            )
            admin_user = result.scalars().first()

            if admin_user:
                # Update existing admin
                print(f"✓ Found existing admin: {admin_user.email}")
                admin_user.full_name = "Admin User"
                admin_user.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
                admin_user.is_admin = True
                admin_user.is_active = True
                await session.commit()
                print(f"✓ Updated admin password and settings")
            else:
                # Create new admin
                print(f"✗ Admin not found, creating new admin...")
                hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
                new_admin = User(
                    full_name="Admin User",
                    email=settings.ADMIN_EMAIL,
                    hashed_password=hashed_password,
                    is_admin=True,
                    is_active=True
                )
                session.add(new_admin)
                await session.commit()
                print(f"✓ Created new admin user: {settings.ADMIN_EMAIL}")

            print("\n✅ Admin user setup complete!")
            print(f"   Email: {settings.ADMIN_EMAIL}")
            print(f"   Password: {settings.ADMIN_PASSWORD}")
            print(f"   Admin Status: True")

        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            raise


async def list_all_users():
    """List all users in the database."""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User))
            users = result.scalars().all()

            if not users:
                print("No users found in database")
            else:
                print(f"\n📋 Total users: {len(users)}")
                print("-" * 60)
                for user in users:
                    admin_status = "✓ ADMIN" if user.is_admin else "  User"
                    active_status = "Active" if user.is_active else "Inactive"
                    print(f"{admin_status} | {user.email:30} | {active_status}")
                print("-" * 60)

        except Exception as e:
            print(f"Error listing users: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Admin User Management Script")
    print("=" * 60)
    print(f"\nDatabase: {settings.DATABASE_URL.split('@')[1]}")
    print(f"Admin Email: {settings.ADMIN_EMAIL}")
    print(f"Admin Password: {settings.ADMIN_PASSWORD}")
    print("\n" + "=" * 60)

    # Run the async function
    asyncio.run(update_or_create_admin())
    asyncio.run(list_all_users())

    print("\n✅ Complete! You can now login with:")
    print(f"   Email: {settings.ADMIN_EMAIL}")
    print(f"   Password: {settings.ADMIN_PASSWORD}")
