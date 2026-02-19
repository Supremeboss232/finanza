#!/usr/bin/env python3
"""Add missing columns to accounts table."""

import asyncio
from sqlalchemy import text
from database import SessionLocal

async def fix_missing_columns():
    """Add missing columns to accounts table if they don't exist."""
    async with SessionLocal() as db:
        try:
            # Define required columns - try to add them (they may already exist)
            required_columns = {
                'status': "ALTER TABLE accounts ADD COLUMN status VARCHAR DEFAULT 'active' NOT NULL",
                'kyc_level': "ALTER TABLE accounts ADD COLUMN kyc_level VARCHAR DEFAULT 'basic' NOT NULL",
                'is_admin_account': "ALTER TABLE accounts ADD COLUMN is_admin_account BOOLEAN DEFAULT FALSE NOT NULL",
            }
            
            # Add missing columns
            for col_name, sql_cmd in required_columns.items():
                print(f"Adding missing column: {col_name}")
                try:
                    await db.execute(text(sql_cmd))
                    await db.commit()
                    print(f"✓ Column {col_name} added successfully")
                except Exception as e:
                    error_str = str(e)
                    if "already exists" in error_str or "duplicate" in error_str.lower():
                        print(f"✓ Column {col_name} already exists")
                        await db.rollback()
                    else:
                        print(f"✗ Error adding {col_name}: {e}")
                        await db.rollback()
            
            print("\n✓ All missing columns have been processed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            await db.rollback()

if __name__ == "__main__":
    asyncio.run(fix_missing_columns())
