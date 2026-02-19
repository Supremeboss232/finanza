#!/usr/bin/env python3
"""
Script to reset a user's password.
Usage: python reset_user_password.py <email>
"""

import asyncio
import sys
from sqlalchemy import select
from database import SessionLocal
from models import User
from auth_utils import get_password_hash

async def reset_password(email: str, new_password: str = None):
    """Reset a user's password."""
    if new_password is None:
        # Generate a default password
        new_password = "TempPassword123!"
    
    async with SessionLocal() as db:
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User with email {email} not found.")
            return False
        
        # Update password
        user.hashed_password = get_password_hash(new_password)
        await db.commit()
        
        print(f"✓ Password reset successfully for {email}")
        print(f"  Temporary Password: {new_password}")
        print(f"  Please inform the user to change this password after login.")
        return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python reset_user_password.py <email> [new_password]")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(reset_password(email, new_password))
