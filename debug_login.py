#!/usr/bin/env python3
"""Debug login - test password verification."""

import asyncio
from app.database import SessionLocal
from app.models import User
from app.auth_utils import verify_password, get_password_hash
from sqlalchemy.future import select


async def test_login(email: str, password: str):
    """Test login with given credentials."""
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).filter(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"❌ User '{email}' not found!")
            return False
        
        print(f"✅ User found: {user.email}")
        print(f"   Full Name: {user.full_name}")
        print(f"   Is Admin: {user.is_admin}")
        print(f"   Is Active: {user.is_active}")
        print(f"\nTesting password verification...")
        
        # Test password
        is_valid = verify_password(password, user.hashed_password)
        
        if is_valid:
            print(f"✅ Password is CORRECT!")
        else:
            print(f"❌ Password is INCORRECT!")
            print(f"\n   Entered password: {password}")
            print(f"   Hashed password: {user.hashed_password[:50]}...")
            
            # Try with the new hash to see if it works
            new_hash = get_password_hash(password)
            is_valid_new = verify_password(password, new_hash)
            print(f"\n   Fresh hash verification: {'✅ PASS' if is_valid_new else '❌ FAIL'}")
        
        return is_valid


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python debug_login.py <email> <password>")
        print("\nExample:")
        print("  python debug_login.py admin@example.com Password123!")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    result = asyncio.run(test_login(email, password))
    sys.exit(0 if result else 1)
