"""
Quick Database Migration Script
Adds missing columns to users table
"""

import asyncio
from sqlalchemy import text
from database import engine

async def migrate_add_missing_columns():
    """Add missing columns to users table"""
    
    async with engine.begin() as conn:
        try:
            # Check if columns exist before adding
            print("[*] Checking for missing columns...")
            
            columns_to_add = [
                ("mfa_secret", "VARCHAR(255)"),
                ("mfa_enabled", "BOOLEAN DEFAULT FALSE"),
                ("mfa_backup_codes", "TEXT"),
                ("mfa_enabled_at", "TIMESTAMP"),
                ("is_suspended", "BOOLEAN DEFAULT FALSE"),
                ("is_frozen", "BOOLEAN DEFAULT FALSE"),
                ("custom_permissions", "TEXT"),
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    # Try to add the column
                    query = text(f"""
                        ALTER TABLE users 
                        ADD COLUMN {col_name} {col_type}
                    """)
                    await conn.execute(query)
                    print(f"✅ Added column: {col_name}")
                except Exception as e:
                    if "already exists" in str(e):
                        print(f"⚠️  Column already exists: {col_name}")
                    else:
                        print(f"❌ Error adding {col_name}: {e}")
            
            # Add index on common query columns
            try:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
                print("✅ Added index on email")
            except:
                print("⚠️  Index on email already exists")
            
            try:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_admin_role ON users(admin_role)"))
                print("✅ Added index on admin_role")
            except:
                print("⚠️  Index on admin_role already exists")
            
            try:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_is_suspended ON users(is_suspended)"))
                print("✅ Added index on is_suspended")
            except:
                print("⚠️  Index on is_suspended already exists")
            
            await conn.commit()
            print("\n✅ Database migration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate_add_missing_columns())
