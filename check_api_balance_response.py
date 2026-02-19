#!/usr/bin/env python3
"""
Check what the API returns for system reserve user balance
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from models import User
from balance_service import BalanceService as BalanceServiceOld
from balance_service_ledger import BalanceServiceLedger

DATABASE_URL = "postgresql+asyncpg://finbank:Supposedbe5@finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com:5432/finanza_bank"

async def check_api_response():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    async with AsyncSession(engine) as session:
        # Get system reserve user
        result = await session.execute(
            select(User).where(User.email == 'sysreserve@finanza.com')
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ System reserve user not found!")
            return
        
        print(f"System Reserve User: {user.full_name}")
        print(f"User ID: {user.id}")
        
        # Get balance using BalanceServiceLedger (what the API uses)
        balance = await BalanceServiceLedger.get_user_balance(session, user.id)
        print(f"\nBalanceServiceLedger.get_user_balance(user_id=1): ${balance:.2f}")
        
        # Test what the admin_service.get_all_users would return
        from admin_service import admin_service
        users = await admin_service.get_all_users(session, skip=0, limit=100)
        
        # Find system reserve user in the list
        sys_user = None
        for u in users:
            if u.get('email') == 'sysreserve@finanza.com':
                sys_user = u
                break
        
        if sys_user:
            print(f"\nadmin_service.get_all_users() result:")
            print(f"  Email: {sys_user.get('email')}")
            print(f"  Balance: ${sys_user.get('balance', 0):.2f}")
        else:
            print("System reserve user not found in admin_service results")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_api_response())
