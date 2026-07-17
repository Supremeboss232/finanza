#!/usr/bin/env python3
"""
Script to promote admin@admin.com to SUPER_ADMIN role
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select
from models import User
from config import settings

async def promote_user():
    """Promote admin@admin.com to SUPER_ADMIN"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Find the admin user
            result = await session.execute(select(User).where(User.email == "admin@admin.com"))
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("❌ User admin@admin.com not found in database")
                await engine.dispose()
                return False
            
            # Update the user
            admin_user.is_admin = True
            admin_user.admin_role = "SUPER_ADMIN"
            admin_user.is_verified = True
            admin_user.is_active = True
            
            session.add(admin_user)
            await session.commit()
            
            print(f"✅ Successfully promoted admin@admin.com to SUPER_ADMIN")
            print(f"   User ID: {admin_user.id}")
            print(f"   Email: {admin_user.email}")
            print(f"   is_admin: {admin_user.is_admin}")
            print(f"   admin_role: {admin_user.admin_role}")
            print(f"   is_verified: {admin_user.is_verified}")
            print(f"   is_active: {admin_user.is_active}")
            return True
            
    except Exception as e:
        print(f"❌ Error promoting user: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(promote_user())
    exit(0 if success else 1)
