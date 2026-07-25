"""
Run migration to add missing columns to users table
"""

import sys
import asyncio
from sqlalchemy import text
from database import engine

async def run_migration():
    """Add missing columns to users table"""
    async with engine.begin() as conn:
        try:
            print("🔄 Checking existing columns...")
            
            # Check if columns already exist
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
            )
            existing_columns = {row[0] for row in result.fetchall()}
            print(f"   Existing columns: {sorted(existing_columns)}")
            
            migrations = []
            
            if 'address' not in existing_columns:
                migrations.append(
                    text("ALTER TABLE users ADD COLUMN address VARCHAR NULL")
                )
                print("   [OK] Will add 'address' column")
            else:
                print("   [OK] 'address' column already exists")
            
            if 'region' not in existing_columns:
                migrations.append(
                    text("ALTER TABLE users ADD COLUMN region VARCHAR NULL")
                )
                print("   [OK] Will add 'region' column")
            else:
                print("   [OK] 'region' column already exists")
            
            if 'routing_number' not in existing_columns:
                migrations.append(
                    text("ALTER TABLE users ADD COLUMN routing_number VARCHAR NULL")
                )
                print("   [OK] Will add 'routing_number' column")
            else:
                print("   [OK] 'routing_number' column already exists")
            
            # Execute all migrations
            if migrations:
                print("\n⚙  Executing migrations...")
                for migration in migrations:
                    try:
                        await conn.execute(migration)
                        print(f"   [OK] Executed: {str(migration)[:80]}")
                    except Exception as e:
                        print(f"   [FAIL] Migration failed: {e}")
                        raise
                
                print("\n[OK] Migration completed successfully!")
            else:
                print("\n[OK] All columns already exist, no migration needed!")
                
        except Exception as e:
            print(f"\n[FAIL] Migration error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True

async def main():
    """Main entry point"""
    print("=" * 60)
    print("Migration: Add User Profile Fields")
    print("=" * 60)
    
    try:
        success = await run_migration()
        if success:
            print("\n[OK] Migration script completed successfully")
            sys.exit(0)
        else:
            print("\n[FAIL] Migration script failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
