#!/usr/bin/env python
"""
Migration: Add missing 'direction' column to transactions table
This column was defined in models.py but never created in the database
"""
import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    """Add direction column to transactions table if it doesn't exist"""
    async with engine.begin() as connection:
        try:
            # Check if column exists
            result = await connection.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='transactions' AND column_name='direction'
                """)
            )
            
            if result.fetchone():
                print("✅ 'direction' column already exists")
                return
            
            # Add the column
            await connection.execute(
                text("""
                    ALTER TABLE transactions 
                    ADD COLUMN direction VARCHAR(20) NULL
                """)
            )
            print("✅ Added 'direction' column to transactions table")
            
        except Exception as e:
            print(f"❌ Error adding direction column: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
