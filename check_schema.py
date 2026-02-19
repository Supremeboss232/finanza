#!/usr/bin/env python3
"""Check the actual database schema."""

import asyncio
from sqlalchemy import inspect, text
from database import SessionLocal

async def check_schema():
    """Check transactions table columns."""
    async with SessionLocal() as db:
        # Get inspector
        inspector = inspect(await db.get_bind().raw_connection())
        
        # Get columns for transactions table
        columns = inspector.get_columns('transactions')
        print("✅ Transactions table columns:")
        for col in columns:
            print(f"   - {col['name']}: {col['type']}")

if __name__ == "__main__":
    asyncio.run(check_schema())
