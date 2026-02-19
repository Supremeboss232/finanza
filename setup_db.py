"""
Test database connection and create test user for login testing.
Run this script to verify database is working and create a test account.
"""
import asyncio
from sqlalchemy import text
from database import SessionLocal, Base, engine
from models import User
from auth_utils import get_password_hash
from config import settings


async def test_connection():
    """Test if database is reachable."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def create_test_users():
    """Create test users for login testing."""
    async with SessionLocal() as db:
        try:
            # Check if admin user already exists
            from sqlalchemy.future import select
            
            admin_result = await db.execute(
                select(User).filter(User.email == settings.ADMIN_EMAIL)
            )
            admin_user = admin_result.scalar_one_or_none()
            
            if not admin_user:
                admin_user = User(
                    email=settings.ADMIN_EMAIL,
                    hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                    full_name="Admin User",
                    is_admin=True,
                    is_active=True,
                    is_verified=True
                )
                db.add(admin_user)
                await db.commit()
                print(f"✅ Admin user created: {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")
            else:
                print(f"✅ Admin user already exists: {settings.ADMIN_EMAIL}")
            
            # Create a test user for regular login
            test_result = await db.execute(
                select(User).filter(User.email == "testuser@example.com")
            )
            test_user = test_result.scalar_one_or_none()
            
            if not test_user:
                test_user = User(
                    email="testuser@example.com",
                    hashed_password=get_password_hash("testuser123"),
                    full_name="Test User",
                    is_admin=False,
                    is_active=True,
                    is_verified=True
                )
                db.add(test_user)
                await db.commit()
                print(f"✅ Test user created: testuser@example.com / testuser123")
            else:
                print(f"✅ Test user already exists: testuser@example.com")
                
        except Exception as e:
            print(f"❌ Error creating test users: {e}")
            import traceback
            traceback.print_exc()


async def main():
    print("=" * 60)
    print("DATABASE CONNECTION & TEST USER SETUP")
    print("=" * 60)
    print()
    
    print("1. Testing database connection...")
    connected = await test_connection()
    print()
    
    if connected:
        print("2. Creating test users...")
        await create_test_users()
        print()
        print("=" * 60)
        print("✅ Setup Complete! You can now login with:")
        print(f"   Email: {settings.ADMIN_EMAIL}")
        print(f"   Password: {settings.ADMIN_PASSWORD}")
        print()
        print("   OR")
        print("   Email: testuser@example.com")
        print("   Password: testuser123")
        print("=" * 60)
    else:
        print("❌ Database connection failed. Fix the connection before continuing.")
        print()
        print("DATABASE URL:", settings.DATABASE_URL)
        print()
        print("Things to check:")
        print("1. Is the database server running?")
        print("2. Is the hostname correct?")
        print("3. Are the credentials correct?")
        print("4. Is the database port open (5432)?")


if __name__ == "__main__":
    asyncio.run(main())
