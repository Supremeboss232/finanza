#!/usr/bin/env python3
"""
Verify the exact password for Supremercyworld@gmail.com (ID 2)
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from config import settings
import models
from auth_utils import verify_password

async def verify_user_password():
    """Verify password for user"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as db:
            # Get user
            result = await db.execute(
                select(models.User).where(models.User.id == 2)
            )
            user = result.scalar_one_or_none()
            
            if user:
                print(f"User ID 2")
                print(f"Email: {user.email}")
                print(f"Hash: {user.hashed_password}")
                print()
                
                passwords_to_test = [
                    "Supposedbe",
                    "test123",
                    "password",
                    "DebugTest123!"
                ]
                
                for pwd in passwords_to_test:
                    result = verify_password(pwd, user.hashed_password)
                    print(f"Password '{pwd}': {result}")

    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_user_password())
