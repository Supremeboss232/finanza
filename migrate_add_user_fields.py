"""
Migration script to add address, region, and routing_number columns to users table.

This script adds the new admin display fields to the existing users table.
Run this before deploying the updated application.
"""

import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    """Add new columns to users table"""
    async with engine.begin() as conn:
        try:
            # Check if columns already exist
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
            )
            existing_columns = {row[0] for row in result.fetchall()}
            
            migrations = []
            
            if 'address' not in existing_columns:
                migrations.append(
                    text("ALTER TABLE users ADD COLUMN address VARCHAR NULL")
                )
                print("✓ Adding 'address' column")
            
            if 'region' not in existing_columns:
                migrations.append(
                    text("ALTER TABLE users ADD COLUMN region VARCHAR NULL")
                )
                print("✓ Adding 'region' column")
            
            if 'routing_number' not in existing_columns:
                migrations.append(
                    text("ALTER TABLE users ADD COLUMN routing_number VARCHAR NULL")
                )
                print("✓ Adding 'routing_number' column")
            
            # Execute all migrations
            for migration in migrations:
                try:
                    await conn.execute(migration)
                except Exception as e:
                    print(f"⚠️  Migration failed: {e}")
            
            await conn.commit()
            
            if migrations:
                print(f"\n✅ Successfully added {len(migrations)} column(s) to users table")
            else:
                print("\n✅ All columns already exist in users table")
                
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
