"""
Add account_type column to accounts table
"""
import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    """Add account_type column to accounts table"""
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'accounts' 
                    AND column_name = 'account_type'
                """)
            )
            column_exists = result.fetchone() is not None
            
            if not column_exists:
                # Add the column
                await conn.execute(
                    text("""
                        ALTER TABLE accounts 
                        ADD COLUMN account_type VARCHAR DEFAULT 'savings'
                    """)
                )
                print("✓ Added account_type column to accounts table")
            else:
                print("✓ account_type column already exists")
                
        except Exception as e:
            print(f"Error during migration: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(migrate())
