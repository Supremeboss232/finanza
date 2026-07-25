#!/usr/bin/env python3
"""
Migration: Add email column to kyc_info table if it doesn't exist
"""
import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    """Add email column to kyc_info if needed"""
    async with engine.begin() as conn:
        print("🔄 Checking if kyc_info.email column exists...")
        
        # Check if column exists
        result = await conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name='kyc_info'")
        )
        existing_columns = {row[0] for row in result.fetchall()}
        
        if 'email' in existing_columns:
            print("[OK] email column already exists")
            return
        
        print("➕ Adding email column to kyc_info table...")
        await conn.execute(
            text("ALTER TABLE kyc_info ADD COLUMN email VARCHAR NULL")
        )
        print("[OK] Migration complete: email column added to kyc_info")

if __name__ == "__main__":
    asyncio.run(migrate())
