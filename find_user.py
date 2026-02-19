#!/usr/bin/env python3
"""
Check which user ID belongs to Supremercyworld@gmail.com
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config import settings
import models

async def find_user():
    """Find user by email"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Get user
            result = await db.execute(
                select(models.User).where(models.User.email == "Supremercyworld@gmail.com")
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"Email: {user.email}")
                print(f"ID: {user.id}")
                print(f"Name: {user.full_name}")
                print(f"Hash: {user.hashed_password[:60]}...")
            else:
                print("User not found")
                
                # List all users
                print("\nAll users:")
                result = await db.execute(select(models.User))
                users = result.scalars().all()
                for u in users:
                    print(f"  ID: {u.id}, Email: {u.email}, Name: {u.full_name}")

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(find_user())
