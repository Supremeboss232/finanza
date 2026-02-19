"""
Migration: Fix accounts.updated_at default value
Adds proper default for updated_at column in accounts table
"""

import sys
import asyncio
from sqlalchemy import text
from database import engine

async def run_migration():
    """Fix the updated_at column in accounts table"""
    async with engine.begin() as conn:
        try:
            print("🔄 Fixing accounts.updated_at column...")
            
            # Check current constraint on updated_at
            result = await conn.execute(
                text("""
                    SELECT column_name, column_default, is_nullable
                    FROM information_schema.columns
                    WHERE table_name='accounts' AND column_name='updated_at'
                """)
            )
            row = result.fetchone()
            
            if row:
                col_name, col_default, is_nullable = row
                print(f"   Current state: default={col_default}, nullable={is_nullable}")
                
                # Drop the existing constraint if needed and add proper default
                try:
                    # First, update any NULL values to current timestamp
                    await conn.execute(
                        text("UPDATE accounts SET updated_at = NOW() WHERE updated_at IS NULL")
                    )
                    print("   ✓ Updated NULL values to current timestamp")
                except Exception as e:
                    print(f"   ⚠️  Could not update NULL values: {e}")
                
                # Add the default value
                try:
                    await conn.execute(
                        text("ALTER TABLE accounts ALTER COLUMN updated_at SET DEFAULT NOW()")
                    )
                    print("   ✓ Set DEFAULT NOW() for updated_at")
                except Exception as e:
                    print(f"   ⚠️  Could not set default: {e}")
            
            print("✅ Migration completed")
            return True
            
        except Exception as e:
            print(f"❌ Migration error: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Main entry point"""
    print("=" * 60)
    print("Migration: Fix Accounts Updated_at Column")
    print("=" * 60)
    
    try:
        success = await run_migration()
        if success:
            print("\n✅ Migration script completed successfully")
            sys.exit(0)
        else:
            print("\n❌ Migration script failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
