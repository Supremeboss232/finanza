#!/usr/bin/env python3
"""Add loan_type column to loans table"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import settings

async def add_loan_type_column():
    """Add loan_type column to loans table if it doesn't exist"""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    try:
        async with engine.begin() as conn:
            # Add column if it doesn't exist
            await conn.execute(text("""
                ALTER TABLE loans 
                ADD COLUMN IF NOT EXISTS loan_type VARCHAR(50) NULL
            """))
            await conn.commit()
            print("✅ Successfully added loan_type column to loans table")
    except Exception as e:
        print(f"❌ Error adding column: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_loan_type_column())
