#!/usr/bin/env python
"""
Initialize database and apply kyc_status column
"""
import asyncio
from sqlalchemy import text
from database import engine
from models import Base

async def init_database():
    """Initialize all tables and add kyc_status column"""
    
    # 1. Create all tables
    print("1️⃣  Creating all database tables...")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    print("✓ Tables created")
    
    # 2. Add kyc_status column if it doesn't exist
    print("\n2️⃣  Adding kyc_status column to users table...")
    async with engine.begin() as connection:
        try:
            # Check if column exists
            result = await connection.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='kyc_status'
                """)
            )
            
            if result.fetchone():
                print("✓ kyc_status column already exists")
            else:
                # Add the column with default
                await connection.execute(
                    text("""
                        ALTER TABLE users 
                        ADD COLUMN kyc_status VARCHAR(20) NOT NULL DEFAULT 'not_started'
                    """)
                )
                print("✓ Added kyc_status column to users table")
                
                # Create index for performance
                try:
                    await connection.execute(
                        text("""
                            CREATE INDEX idx_users_kyc_status ON users (kyc_status)
                        """)
                    )
                    print("✓ Created index on kyc_status")
                except Exception:
                    print("⚠ Index may already exist (skipped)")
        
        except Exception as e:
            print(f"⚠ Warning during column addition: {e}")

async def verify_schema():
    """Verify the schema was created correctly"""
    print("\n3️⃣  Verifying schema...")
    async with engine.begin() as connection:
        try:
            # Check users table columns
            result = await connection.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name='users'
                    ORDER BY ordinal_position
                """)
            )
            
            columns = result.fetchall()
            print(f"\n✓ Users table has {len(columns)} columns:")
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                print(f"  - {col[0]:<25} {col[1]:<15} {nullable}")
            
            # Verify kyc_status exists
            kyc_found = any(col[0] == 'kyc_status' for col in columns)
            if kyc_found:
                print("\n✅ kyc_status column verified!")
                return True
            else:
                print("\n⚠ kyc_status column NOT FOUND in database")
                return False
                
        except Exception as e:
            print(f"Error verifying schema: {e}")
            return False

async def test_admin_query():
    """Test that admin user query works"""
    print("\n4️⃣  Testing admin user query...")
    try:
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.ext.asyncio import AsyncSession
        from models import User
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            # Test query
            from sqlalchemy import select
            result = await session.execute(select(User).limit(1))
            users = result.scalars().all()
            print(f"✓ Admin query works - found {len(users)} users")
            return True
    except Exception as e:
        print(f"⚠ Query test error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(init_database())
    schema_ok = asyncio.run(verify_schema())
    query_ok = asyncio.run(test_admin_query())
    
    if schema_ok and query_ok:
        print("\n✅ Database initialization complete! KYC logic ready to activate.")
    else:
        print("\n⚠ Database initialization completed with warnings.")
