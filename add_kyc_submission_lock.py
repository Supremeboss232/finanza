#!/usr/bin/env python
"""
Migration script to add KYC submission locking fields to kyc_info table.
Adds: kyc_submitted, submission_locked, submission_timestamp
"""

import asyncio
from sqlalchemy import text
from database import SessionLocal


async def migrate_kyc_submission_lock():
    """Add submission lock fields to kyc_info table"""
    
    async with SessionLocal() as db:
        print("🔄 Starting KYC submission lock migration...")
        
        try:
            # Check if columns already exist
            result = await db.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'kyc_info' 
                    AND column_name IN ('kyc_submitted', 'submission_locked', 'submission_timestamp')
                """)
            )
            existing_cols = [row[0] for row in result.fetchall()]
            
            # Add kyc_submitted if it doesn't exist
            if 'kyc_submitted' not in existing_cols:
                print("  Adding kyc_submitted column...")
                await db.execute(
                    text("""
                        ALTER TABLE kyc_info
                        ADD COLUMN kyc_submitted BOOLEAN NOT NULL DEFAULT FALSE
                    """)
                )
                print("  ✅ kyc_submitted column added")
            else:
                print("  ✓ kyc_submitted column already exists")
            
            # Add submission_locked if it doesn't exist
            if 'submission_locked' not in existing_cols:
                print("  Adding submission_locked column...")
                await db.execute(
                    text("""
                        ALTER TABLE kyc_info
                        ADD COLUMN submission_locked BOOLEAN NOT NULL DEFAULT FALSE
                    """)
                )
                print("  ✅ submission_locked column added")
            else:
                print("  ✓ submission_locked column already exists")
            
            # Add submission_timestamp if it doesn't exist
            if 'submission_timestamp' not in existing_cols:
                print("  Adding submission_timestamp column...")
                await db.execute(
                    text("""
                        ALTER TABLE kyc_info
                        ADD COLUMN submission_timestamp TIMESTAMP WITH TIME ZONE NULL
                    """)
                )
                print("  ✅ submission_timestamp column added")
            else:
                print("  ✓ submission_timestamp column already exists")
            
            await db.commit()
            
            # Verify migration
            print("\n📋 Verifying migration...")
            result = await db.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'kyc_info'
                    ORDER BY column_name
                """)
            )
            
            print("  kyc_info table columns:")
            for col_name, data_type, is_nullable in result.fetchall():
                null_str = "NULL" if is_nullable == "YES" else "NOT NULL"
                print(f"    - {col_name}: {data_type} {null_str}")
            
            print("\n✅ KYC submission lock migration completed successfully!")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"\n❌ Migration failed: {str(e)}")
            return False


if __name__ == "__main__":
    result = asyncio.run(migrate_kyc_submission_lock())
    exit(0 if result else 1)
