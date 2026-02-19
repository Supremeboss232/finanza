"""
Database schema migration to add new columns to existing tables.
Run: python migrate_schema.py
"""
import asyncio
from sqlalchemy import text
from database import engine

async def run_migrations():
    async with engine.begin() as conn:
        print("Running database migrations...")
        
        # Card table migrations
        print("\n[Cards Table]")
        try:
            await conn.execute(text("""
                ALTER TABLE cards ADD COLUMN card_holder_name VARCHAR DEFAULT NULL;
            """))
            print("  OK: Added card_holder_name column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: card_holder_name column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE cards ADD COLUMN balance FLOAT DEFAULT 0.0;
            """))
            print("  OK: Added balance column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: balance column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE cards ADD COLUMN credit_limit FLOAT DEFAULT 5000.0;
            """))
            print("  OK: Added credit_limit column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: credit_limit column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE cards ADD COLUMN transaction_limit FLOAT DEFAULT 10000.0;
            """))
            print("  OK: Added transaction_limit column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: transaction_limit column already exists")
            else:
                print(f"  ERROR: {e}")
        
        # Deposit table migrations
        print("\n[Deposits Table]")
        try:
            await conn.execute(text("""
                ALTER TABLE deposits ADD COLUMN current_balance FLOAT;
            """))
            print("  OK: Added current_balance column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: current_balance column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE deposits ADD COLUMN interest_rate FLOAT DEFAULT 0.0;
            """))
            print("  OK: Added interest_rate column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: interest_rate column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE deposits ADD COLUMN term_months INTEGER DEFAULT 12;
            """))
            print("  OK: Added term_months column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: term_months column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE deposits ADD COLUMN maturity_date TIMESTAMP(6) WITH TIME ZONE DEFAULT NULL;
            """))
            print("  OK: Added maturity_date column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: maturity_date column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                UPDATE deposits SET status = 'active' WHERE status = 'completed';
            """))
            print("  OK: Updated deposit statuses")
        except Exception as e:
            print(f"  WARNING: {e}")
        
        # Loan table migrations
        print("\n[Loans Table]")
        try:
            await conn.execute(text("""
                ALTER TABLE loans ADD COLUMN remaining_balance FLOAT;
            """))
            print("  OK: Added remaining_balance column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: remaining_balance column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE loans ADD COLUMN monthly_payment FLOAT DEFAULT 0.0;
            """))
            print("  OK: Added monthly_payment column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: monthly_payment column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE loans ADD COLUMN paid_amount FLOAT DEFAULT 0.0;
            """))
            print("  OK: Added paid_amount column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: paid_amount column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE loans ADD COLUMN purpose VARCHAR DEFAULT NULL;
            """))
            print("  OK: Added purpose column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: purpose column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE loans ADD COLUMN approved_at TIMESTAMP(6) WITH TIME ZONE DEFAULT NULL;
            """))
            print("  OK: Added approved_at column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: approved_at column already exists")
            else:
                print(f"  ERROR: {e}")
        
        # Investment table migrations
        print("\n[Investments Table]")
        try:
            await conn.execute(text("""
                ALTER TABLE investments ADD COLUMN current_value FLOAT DEFAULT NULL;
            """))
            print("  OK: Added current_value column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: current_value column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE investments ADD COLUMN interest_earned FLOAT DEFAULT 0.0;
            """))
            print("  OK: Added interest_earned column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: interest_earned column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE investments ADD COLUMN annual_return_rate FLOAT DEFAULT 0.0;
            """))
            print("  OK: Added annual_return_rate column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: annual_return_rate column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE investments ADD COLUMN purpose VARCHAR DEFAULT NULL;
            """))
            print("  OK: Added purpose column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: purpose column already exists")
            else:
                print(f"  ERROR: {e}")
        
        try:
            await conn.execute(text("""
                ALTER TABLE investments ADD COLUMN maturity_date TIMESTAMP(6) WITH TIME ZONE DEFAULT NULL;
            """))
            print("  OK: Added maturity_date column")
        except Exception as e:
            if "already exists" in str(e):
                print("  INFO: maturity_date column already exists")
            else:
                print(f"  ERROR: {e}")
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_migrations())
