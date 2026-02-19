import asyncio
import sys
from sqlalchemy import text, inspect
from app.database import SessionLocal, engine

async def check_database():
    try:
        # Get database inspector
        async with engine.begin() as conn:
            inspector = inspect(conn)
            tables = inspector.get_table_names()
            
        if not tables:
            print("❌ No tables found in database")
            return
            
        print("✅ Connected to AWS Database!")
        print(f"\n📋 Tables found: {len(tables)}")
        print("-" * 50)
        
        for table in tables:
            print(f"\n📊 TABLE: {table}")
            print("=" * 50)
            
            async with SessionLocal() as db:
                result = await db.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
                count = result.scalar()
                print(f"   Records: {count}")
                
                # Show first few records
                result = await db.execute(text(f"SELECT * FROM {table} LIMIT 3"))
                rows = result.fetchall()
                if rows:
                    print(f"   Sample data:")
                    for row in rows:
                        print(f"      {row}")
                print()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_database())
