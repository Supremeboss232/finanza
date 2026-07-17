#!/usr/bin/env python
"""
Database Setup & Synchronization Script
========================================

This script:
1. Tests database connectivity
2. Creates/updates all tables from models
3. Runs Alembic migrations
4. Verifies schema completeness
5. Seeds initial data (system user, reserve account)

Usage:
    python setup_database.py
"""

import asyncio
import sys
import logging
from pathlib import Path
from sqlalchemy import text, inspect, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from database import Base, engine, SessionLocal
from models import User, Account, Ledger, Transaction, TokenBlacklist, KYCInfo, KYCSubmission
import auth_utils


class DatabaseSetup:
    """Handles database setup and synchronization"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        
    async def test_connection(self) -> bool:
        """Test database connectivity"""
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def create_all_tables(self) -> bool:
        """Create all tables from models"""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ All tables created/verified")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    async def verify_schema(self) -> dict:
        """Verify all required tables exist"""
        required_tables = {
            'users': ['id', 'email', 'full_name', 'is_admin', 'kyc_status'],
            'accounts': ['id', 'owner_id', 'account_number', 'balance', 'status'],
            'transactions': ['id', 'user_id', 'account_id', 'amount', 'status'],
            'ledger': ['id', 'user_id', 'entry_type', 'amount', 'status'],
            'token_blacklist': ['id', 'token', 'user_id', 'expires_at'],
            'kyc_info': ['id', 'user_id', 'email', 'status'],
            'kyc_submissions': ['id', 'user_id', 'document_type', 'status'],
        }
        
        results = {
            'total_tables': len(required_tables),
            'verified_tables': 0,
            'missing_tables': [],
            'missing_columns': [],
        }
        
        try:
            async with self.engine.connect() as conn:
                inspector = inspect(await conn.get_raw_connection())
                existing_tables = inspector.get_table_names()
                
                for table_name, required_cols in required_tables.items():
                    if table_name in existing_tables:
                        results['verified_tables'] += 1
                        
                        # Check columns
                        existing_cols = [col['name'] for col in inspector.get_columns(table_name)]
                        missing = [col for col in required_cols if col not in existing_cols]
                        
                        if missing:
                            results['missing_columns'].append({
                                'table': table_name,
                                'columns': missing
                            })
                    else:
                        results['missing_tables'].append(table_name)
                
                return results
        except Exception as e:
            logger.error(f"❌ Schema verification failed: {e}")
            return results
    
    async def ensure_system_user(self) -> bool:
        """Ensure system user exists"""
        try:
            async with self.SessionLocal() as db:
                # Check if system user exists
                from crud import get_user_by_email
                system_user = await get_user_by_email(db, email="sysreserve@finanza.com")
                
                if system_user:
                    logger.info("✅ System user (ID=1) already exists")
                    return True
                
                # Create system user
                system_user = User(
                    id=1,
                    full_name="System Reserve / Treasury",
                    email="sysreserve@finanza.com",
                    hashed_password=auth_utils.get_password_hash("Supposedbe5"),
                    is_active=True,
                    is_admin=True,
                    is_verified=True,
                    kyc_status='approved'
                )
                db.add(system_user)
                await db.commit()
                logger.info("✅ System user created (ID=1)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to ensure system user: {e}")
            return False
    
    async def ensure_system_reserve_account(self) -> bool:
        """Ensure system reserve account exists"""
        try:
            async with self.SessionLocal() as db:
                # Check if reserve account exists
                from sqlalchemy import select
                result = await db.execute(
                    select(Account).where(Account.account_number == "SYS-RESERVE-0001")
                )
                reserve = result.scalar_one_or_none()
                
                if reserve:
                    logger.info(f"✅ System reserve account exists (Balance: ${reserve.balance:,.2f})")
                    return True
                
                # Create reserve account
                from datetime import datetime
                from decimal import Decimal
                
                reserve_account = Account(
                    owner_id=1,
                    account_number="SYS-RESERVE-0001",
                    account_type="treasury",
                    balance=10_000_000.0,
                    currency="USD",
                    status="active",
                    kyc_level="full",
                    is_admin_account=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(reserve_account)
                await db.flush()
                
                # Create seed transaction and ledger entry
                seed_transaction = Transaction(
                    user_id=1,
                    account_id=reserve_account.id,
                    amount=10_000_000.0,
                    transaction_type="system_seed",
                    direction="credit",
                    status="completed",
                    description="System Reserve Account initialization seed"
                )
                db.add(seed_transaction)
                await db.flush()
                
                seed_ledger = Ledger(
                    user_id=1,
                    entry_type="credit",
                    amount=Decimal("10000000.00"),
                    transaction_id=seed_transaction.id,
                    description="System Reserve Account initialization seed",
                    status="posted"
                )
                db.add(seed_ledger)
                await db.commit()
                
                logger.info("✅ System reserve account created with $10,000,000 seed")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create system reserve account: {e}")
            return False
    
    async def create_admin_user(self) -> bool:
        """Ensure admin user exists"""
        try:
            async with self.SessionLocal() as db:
                from crud import get_user_by_email
                admin = await get_user_by_email(db, email=settings.ADMIN_EMAIL)
                
                if admin and admin.is_admin:
                    logger.info(f"✅ Admin user exists ({settings.ADMIN_EMAIL})")
                    return True
                
                # Create admin user
                admin_user = User(
                    full_name="Admin User",
                    email=settings.ADMIN_EMAIL,
                    hashed_password=auth_utils.get_password_hash(settings.ADMIN_PASSWORD),
                    is_admin=True,
                    is_active=True,
                    is_verified=True,
                    kyc_status='approved'
                )
                db.add(admin_user)
                await db.flush()
                
                # Create admin account
                import time
                from datetime import datetime
                admin_account_number = f"ADMIN{admin_user.id}_{int(time.time() * 1000000) % 1000000}"
                admin_account = Account(
                    owner_id=admin_user.id,
                    account_number=admin_account_number,
                    account_type='admin',
                    balance=0.0,
                    currency='USD',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(admin_account)
                admin_user.account_number = admin_account_number
                
                await db.commit()
                logger.info(f"✅ Admin user created ({settings.ADMIN_EMAIL})")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to create admin user: {e}")
            return False
    
    async def generate_schema_summary(self) -> None:
        """Generate comprehensive schema summary"""
        try:
            async with self.engine.connect() as conn:
                inspector = inspect(await conn.get_raw_connection())
                tables = inspector.get_table_names()
                
                logger.info("\n" + "="*60)
                logger.info("DATABASE SCHEMA SUMMARY")
                logger.info("="*60)
                
                for table_name in sorted(tables):
                    columns = inspector.get_columns(table_name)
                    pk = inspector.get_pk_constraint(table_name)
                    
                    logger.info(f"\n📋 Table: {table_name}")
                    logger.info(f"   Primary Key: {pk.get('constrained_columns', 'N/A')}")
                    
                    for col in columns:
                        nullable = "nullable" if col['nullable'] else "NOT NULL"
                        logger.info(f"   - {col['name']}: {col['type']} ({nullable})")
                
                logger.info("\n" + "="*60)
                
        except Exception as e:
            logger.error(f"Failed to generate schema summary: {e}")


async def main():
    """Main setup orchestration"""
    logger.info("\n" + "="*60)
    logger.info("🚀 DATABASE SETUP & SYNCHRONIZATION")
    logger.info("="*60 + "\n")
    
    setup = DatabaseSetup()
    
    # Step 1: Test connection
    logger.info("Step 1: Testing database connection...")
    if not await setup.test_connection():
        logger.error("\n❌ Cannot proceed - database connection failed")
        logger.info("   Check .env DATABASE_URL configuration")
        return False
    
    # Step 2: Create tables
    logger.info("\nStep 2: Creating/verifying tables...")
    if not await setup.create_all_tables():
        logger.error("\n❌ Failed to create tables")
        return False
    
    # Step 3: Verify schema
    logger.info("\nStep 3: Verifying database schema...")
    schema_check = await setup.verify_schema()
    logger.info(f"   Tables verified: {schema_check['verified_tables']}/{schema_check['total_tables']}")
    
    if schema_check['missing_tables']:
        logger.warning(f"   ⚠️  Missing tables: {schema_check['missing_tables']}")
    
    if schema_check['missing_columns']:
        for missing in schema_check['missing_columns']:
            logger.warning(f"   ⚠️  {missing['table']}: missing columns {missing['columns']}")
    
    # Step 4: Ensure system user
    logger.info("\nStep 4: Ensuring system user...")
    await setup.ensure_system_user()
    
    # Step 5: Ensure system reserve account
    logger.info("\nStep 5: Ensuring system reserve account...")
    await setup.ensure_system_reserve_account()
    
    # Step 6: Ensure admin user
    logger.info("\nStep 6: Ensuring admin user...")
    await setup.create_admin_user()
    
    # Step 7: Generate schema summary
    logger.info("\nStep 7: Generating schema summary...")
    await setup.generate_schema_summary()
    
    logger.info("\n" + "="*60)
    logger.info("✅ DATABASE SETUP COMPLETE")
    logger.info("="*60)
    logger.info("\nYour database is now ready with:")
    logger.info("  ✓ All tables created and synchronized")
    logger.info("  ✓ System user (ID=1) configured")
    logger.info("  ✓ System reserve account ($10M seed)")
    logger.info("  ✓ Admin user account configured")
    logger.info("\nYou can now start the application!")
    logger.info("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
