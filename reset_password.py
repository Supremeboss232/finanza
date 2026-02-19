#!/usr/bin/env python3
"""Update admin user password."""

import asyncio
from app.database import SessionLocal
from app.models import User
from app.auth_utils import get_password_hash
from sqlalchemy.future import select


async def update_admin_password(email: str, new_password: str):
    """Update admin user password."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User with email '{email}' not found!")
            return False
        
        # Hash and update password
        hashed_password = get_password_hash(new_password)
        user.hashed_password = hashed_password
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        print(f"✅ Password updated successfully!")
        print(f"   Email: {user.email}")
        print(f"   New Password: {new_password}")
        
        return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python reset_password.py <email> <new_password>")
        print("\nExample:")
        print("  python reset_password.py admin@example.com Admin123!")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    asyncio.run(update_admin_password(email, new_password))
