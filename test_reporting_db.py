#!/usr/bin/env python
"""Quick test of reporting API endpoints"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_

# Import models and router
from models import Transaction, User
from config import settings

async def test_queries():
    """Test database queries work"""
    try:
        # Create async engine
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Test 1: Basic transaction count
            from datetime import datetime, timedelta
            start_dt = datetime.now() - timedelta(days=30)
            end_dt = datetime.now()
            
            query1 = select(Transaction).where(
                and_(
                    Transaction.created_at >= start_dt,
                    Transaction.created_at <= end_dt,
                )
            )
            result1 = await session.execute(query1)
            txs = result1.scalars().all()
            print(f"✓ Query 1: Found {len(txs)} transactions")
            
            # Test 2: Distinct users count
            from sqlalchemy import func
            query2 = select(func.count(func.distinct(Transaction.user_id))).where(
                and_(
                    Transaction.created_at >= start_dt,
                    Transaction.created_at <= end_dt,
                )
            )
            result2 = await session.execute(query2)
            user_count = result2.scalar()
            print(f"✓ Query 2: Found {user_count} distinct users")
            
            # Test 3: User lookup
            if txs:
                first_user_id = txs[0].user_id
                query3 = select(User).where(User.id == first_user_id)
                result3 = await session.execute(query3)
                user = result3.scalars().first()
                print(f"✓ Query 3: Found user {user.email if user else 'not found'}")
            
            print("\n✅ All database queries work!")
            await engine.dispose()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_queries())
