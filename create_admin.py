#!/usr/bin/env python3
"""
Script to create an admin user in the database.
Usage: python create_admin.py <email> <password> [full_name]
"""

import asyncio
import sys
from app.database import SessionLocal
from app.models import User
from app.auth_utils import get_password_hash


async def create_admin_user(email: str, password: str, full_name: str = "Admin"):
    """Create an admin user in the database."""
    from sqlalchemy.future import select
    
    async with SessionLocal() as db:
        # Check if user already exists
        result = await db.execute(
            select(User).filter(User.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"❌ User with email '{email}' already exists!")
            return False
        
        # Create new admin user
        hashed_password = get_password_hash(password)
        new_admin = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_admin=True,
            is_active=True
        )
        
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)
        
        print(f"✅ Admin user created successfully!")
        print(f"   Email: {email}")
        print(f"   Full Name: {full_name}")
        print(f"   User ID: {new_admin.id}")
        
        return True


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [full_name]")
        print("\nExample:")
        print("  python create_admin.py admin@example.com mypassword123 'Admin User'")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Admin"
    
    # Validate email
    if "@" not in email:
        print("❌ Invalid email address!")
        sys.exit(1)
    
    # Validate password
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        sys.exit(1)
    
    print(f"Creating admin user...")
    print(f"  Email: {email}")
    print(f"  Full Name: {full_name}")
    
    success = asyncio.run(create_admin_user(email, password, full_name))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
