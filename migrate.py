"""
Migration runner script to apply database schema changes
Run: python migrate.py
"""
import asyncio
from sqlalchemy import text
from database import engine

async def run_migrations():
    async with engine.begin() as conn:
        # Add is_verified column if it doesn't exist
        try:
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE;
            """))
            print("✓ Added is_verified column to users table")
        except Exception as e:
            if "already exists" in str(e):
                print("✓ is_verified column already exists")
            else:
                print(f"✗ Error adding is_verified column: {e}")

if __name__ == "__main__":
    asyncio.run(run_migrations())
