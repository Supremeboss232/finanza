#!/usr/bin/env python3
"""Check what data exists for the logged-in user."""

import asyncio
from sqlalchemy import select
from database import SessionLocal
from models import User, Deposit, Loan, Investment, Transaction, Account

async def check_user_data():
    """Check data for Supremercyworld@gmail.com user."""
    async with SessionLocal() as db:
        # Get the user
        result = await db.execute(
            select(User).filter(User.email == "Supremercyworld@gmail.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found!")
            return
        
        print(f"✅ Found user: {user.email} (ID: {user.id})")
        print(f"   Full name: {user.full_name}")
        print(f"   Account number: {user.account_number}")
        
        # Check deposits
        result = await db.execute(
            select(Deposit).filter(Deposit.user_id == user.id)
        )
        deposits = result.scalars().all()
        print(f"\n📊 Deposits: {len(deposits)}")
        for dep in deposits:
            print(f"   - ${dep.amount} ({dep.status}) - {dep.created_at}")
        
        # Check loans
        result = await db.execute(
            select(Loan).filter(Loan.user_id == user.id)
        )
        loans = result.scalars().all()
        print(f"\n💰 Loans: {len(loans)}")
        for loan in loans:
            print(f"   - ${loan.amount} ({loan.status}) - {loan.created_at}")
        
        # Check investments
        result = await db.execute(
            select(Investment).filter(Investment.user_id == user.id)
        )
        investments = result.scalars().all()
        print(f"\n📈 Investments: {len(investments)}")
        for inv in investments:
            print(f"   - ${inv.amount} ({inv.status}) - {inv.created_at}")
        
        # Check accounts
        result = await db.execute(
            select(Account).filter(Account.owner_id == user.id)
        )
        accounts = result.scalars().all()
        print(f"\n🏦 Accounts: {len(accounts)}")
        for acc in accounts:
            print(f"   - {acc.account_number} (${acc.balance}) - {acc.currency}")

if __name__ == "__main__":
    asyncio.run(check_user_data())
