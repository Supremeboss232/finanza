#!/usr/bin/env python
"""
Migration: Add all missing columns to transactions table
Columns defined in models.py but missing from actual database:
- direction (VARCHAR, nullable)
- kyc_status_at_time (VARCHAR, nullable)  
- updated_at (TIMESTAMP, nullable)
"""
import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    """Add missing columns to transactions table"""
    print("Starting migration: Adding missing transaction columns...\n")
    
    async with engine.begin() as connection:
        # First, get all existing columns
        result = await connection.execute(
            text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='transactions'
                ORDER BY ordinal_position
            """)
        )
        existing_columns = {row[0] for row in result.fetchall()}
        print(f"Existing columns: {sorted(existing_columns)}\n")
        
        # Columns to add with their definitions
        columns_to_add = [
            ("direction", "VARCHAR(20) NULL"),
            ("kyc_status_at_time", "VARCHAR(50) NULL"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE NULL")
        ]
        
        added_count = 0
        for col_name, col_def in columns_to_add:
            if col_name in existing_columns:
                print(f"✅ Column '{col_name}' already exists")
                continue
            
            try:
                # Add the column
                await connection.execute(
                    text(f"""
                        ALTER TABLE transactions 
                        ADD COLUMN {col_name} {col_def}
                    """)
                )
                print(f"✅ Added column '{col_name}' to transactions table")
                added_count += 1
                
            except Exception as e:
                print(f"❌ Error adding column '{col_name}': {e}")
                raise
        
        if added_count == 0:
            print("\n✅ All columns already exist - no migration needed")
        else:
            print(f"\n✅ Migration complete - Added {added_count} column(s)")

if __name__ == "__main__":
    asyncio.run(migrate())
