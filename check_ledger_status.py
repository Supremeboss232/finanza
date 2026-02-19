#!/usr/bin/env python3
"""
Check the system reserve ledger entries and their status
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://finbank:Supposedbe5@finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432/finanza_bank"

async def check_ledger():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with AsyncSession(engine) as session:
        # Check system reserve ledger entries
        result = await session.execute(
            text("""
                SELECT id, user_id, amount, entry_type, status, description, created_at
                FROM ledger 
                WHERE user_id = 1
                ORDER BY created_at DESC
            """)
        )
        
        rows = result.fetchall()
        print(f"System Reserve Ledger Entries: {len(rows)} total\n")
        
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"  User ID: {row[1]}")
            print(f"  Amount: ${row[2]:.2f}")
            print(f"  Type: {row[3]}")
            print(f"  Status: {row[4]}")
            print(f"  Description: {row[5]}")
            print(f"  Created: {row[6]}")
            print()
        
        # Calculate balance using the same logic as BalanceServiceLedger
        print("\n--- Balance Calculation ---")
        
        # Credits
        result = await session.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM ledger
                WHERE user_id = 1
                AND entry_type = 'credit'
                AND status = 'posted'
            """)
        )
        credits = result.scalar()
        print(f"Credits (status=posted): ${credits:.2f}")
        
        # Debits
        result = await session.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM ledger
                WHERE user_id = 1
                AND entry_type = 'debit'
                AND status = 'posted'
            """)
        )
        debits = result.scalar()
        print(f"Debits (status=posted): ${debits:.2f}")
        
        print(f"Calculated Balance: ${credits - debits:.2f}")
        
        # Also check ledger entries without status filter
        result = await session.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM ledger
                WHERE user_id = 1
                AND entry_type = 'credit'
            """)
        )
        all_credits = result.scalar()
        
        result = await session.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM ledger
                WHERE user_id = 1
                AND entry_type = 'debit'
            """)
        )
        all_debits = result.scalar()
        
        print(f"\nWithout status filter:")
        print(f"All Credits: ${all_credits:.2f}")
        print(f"All Debits: ${all_debits:.2f}")
        print(f"Balance: ${all_credits - all_debits:.2f}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_ledger())
