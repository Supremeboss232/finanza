#!/usr/bin/env python3
"""
Add missing columns to existing tables
"""
import asyncio
from sqlalchemy import text
from database import SessionLocal

async def add_missing_columns():
    async with SessionLocal() as db:
        try:
            # Add description column to transactions if it doesn't exist
            print("Checking transactions table...")
            await db.execute(text("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS description VARCHAR NULL
            """))
            await db.commit()
            print("✓ Added description column to transactions table")
        except Exception as e:
            print(f"✗ Error adding description column: {e}")
            await db.rollback()
        
        try:
            # Add reference_number column to transactions if it doesn't exist
            await db.execute(text("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS reference_number VARCHAR NULL
            """))
            await db.commit()
            print("✓ Added reference_number column to transactions table")
        except Exception as e:
            print(f"✗ Error adding reference_number column: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
