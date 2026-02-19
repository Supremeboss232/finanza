#!/usr/bin/env python3
"""
Check the system reserve account balance in the database
"""
import asyncio
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from models import User, Account, Ledger

DATABASE_URL = "postgresql+asyncpg://finbank:Supposedbe5@finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432/finanza_bank"

async def check_balance():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with AsyncSession(engine) as session:
        # Find the system reserve user
        result = await session.execute(
            select(User).where(User.email == 'sysreserve@finanza.com')
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ System reserve user not found!")
            return
        
        print(f"System Reserve User: {user.full_name} ({user.email})")
        print(f"User ID: {user.id}")
        
        # Check account balance
        result = await session.execute(
            select(Account).where(Account.owner_id == user.id)
        )
        account = result.scalar_one_or_none()
        
        if account:
            print(f"\nAccount Balance (from accounts table): ${account.balance:.2f}")
        else:
            print("\n❌ No account found for system reserve user!")
        
        # Check ledger entries
        result = await session.execute(
            select(Ledger).where(Ledger.user_id == user.id)
        )
        ledgers = result.scalars().all()
        
        print(f"\nLedger Entries: {len(ledgers)} total")
        
        if ledgers:
            total_credit = sum(l.amount for l in ledgers if l.entry_type == 'credit')
            total_debit = sum(l.amount for l in ledgers if l.entry_type == 'debit')
            calculated_balance = total_credit - total_debit
            
            print(f"Total Credits: ${total_credit:.2f}")
            print(f"Total Debits: ${total_debit:.2f}")
            print(f"Calculated Balance: ${calculated_balance:.2f}")
            
            # Show last 5 ledger entries
            print("\nLast 5 Ledger Entries:")
            for ledger in ledgers[-5:]:
                print(f"  {ledger.entry_type.upper()}: ${ledger.amount:.2f} - {ledger.description}")
        else:
            print("❌ No ledger entries found!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_balance())
