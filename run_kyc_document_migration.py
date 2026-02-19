#!/usr/bin/env python
"""
Migration script to add KYC document tracking fields to kyc_info table
"""

import asyncio
from sqlalchemy import text
from database import SessionLocal, engine
from models import Base

async def run_migration():
    """Add KYC document tracking columns to kyc_info table"""
    
    async with engine.begin() as conn:
        try:
            # Check if columns already exist
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='kyc_info'")
            )
            existing_columns = {row[0] for row in result.fetchall()}
            print(f"Existing KYC Info columns: {existing_columns}\n")
            
            # Add missing columns
            columns_to_add = [
                ("id_front_uploaded", "BOOLEAN DEFAULT FALSE"),
                ("id_back_uploaded", "BOOLEAN DEFAULT FALSE"),
                ("ssn_uploaded", "BOOLEAN DEFAULT FALSE"),
                ("proof_of_address_uploaded", "BOOLEAN DEFAULT FALSE"),
                ("id_front_path", "VARCHAR NULL"),
                ("id_back_path", "VARCHAR NULL"),
                ("ssn_path", "VARCHAR NULL"),
                ("proof_of_address_path", "VARCHAR NULL"),
                ("id_expiry_date", "TIMESTAMP WITH TIME ZONE NULL"),
                ("proof_of_address_date", "TIMESTAMP WITH TIME ZONE NULL"),
                ("date_of_birth", "TIMESTAMP WITH TIME ZONE NULL"),
                ("kyc_status", "VARCHAR DEFAULT 'not_started' NOT NULL"),
                ("rejection_reason", "VARCHAR NULL"),
                ("documents_submitted_at", "TIMESTAMP WITH TIME ZONE NULL"),
                ("reviewed_at", "TIMESTAMP WITH TIME ZONE NULL"),
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    alter_sql = f"ALTER TABLE kyc_info ADD COLUMN {col_name} {col_type}"
                    try:
                        await conn.execute(text(alter_sql))
                        print(f"✅ Added column: {col_name}")
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print(f"⚠️  Column {col_name} already exists")
                        else:
                            print(f"❌ Error adding {col_name}: {e}")
                else:
                    print(f"ℹ️  Column {col_name} already exists")
            
            # Create index on kyc_status for faster queries
            try:
                await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_kyc_status ON kyc_info(kyc_status)"))
                print(f"✅ Created index on kyc_status")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print(f"ℹ️  Index already exists")
                else:
                    print(f"❌ Error creating index: {e}")
            
            await conn.commit()
            print("\n✅ KYC Info migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(run_migration())
