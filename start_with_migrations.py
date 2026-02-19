"""
Startup script with automatic migration
Establishes SSH tunnel, runs migrations, then starts the app
"""

import sys
import os
import time
import atexit
import asyncio
from ssh_tunnel import SSHTunnelManager
from config import settings

# Global tunnel instance
tunnel = None


def setup_tunnel():
    """Setup SSH tunnel if configured"""
    global tunnel
    
    if not settings.USE_SSH_TUNNEL:
        print("ℹ️  SSH tunnel disabled.")
        return True
    
    print("🔐 Setting up SSH tunnel...")
    tunnel = SSHTunnelManager(
        ec2_host=settings.SSH_HOST,
        key_path=settings.SSH_KEY_PATH,
        rds_host=settings.RDS_REMOTE_HOST,
        rds_port=settings.RDS_REMOTE_PORT,
        local_port=5432
    )
    
    if tunnel.start():
        atexit.register(cleanup_tunnel)
        return True
    else:
        print("❌ Failed to setup SSH tunnel")
        return False

def cleanup_tunnel():
    """Cleanup SSH tunnel on exit"""
    global tunnel
    if tunnel:
        tunnel.stop()

async def run_migrations():
    """Run database migrations"""
    print("\n🔄 Running database migrations...")
    
    try:
        from sqlalchemy import text
        from database import engine
        
        async with engine.begin() as conn:
            # Migration 1: Add missing columns to users table
            print("   📋 Migration 1: User profile columns...")
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users'")
            )
            existing_columns = {row[0] for row in result.fetchall()}
            
            migrations = []
            
            columns_needed = ['address', 'region', 'routing_number']
            for col in columns_needed:
                if col not in existing_columns:
                    migrations.append(
                        text(f"ALTER TABLE users ADD COLUMN {col} VARCHAR NULL")
                    )
                    print(f"      + Adding '{col}' column")
            
            for migration in migrations:
                await conn.execute(migration)
            
            if migrations:
                print(f"      ✓ Added {len(migrations)} columns")
            else:
                print("      ✓ All columns already exist")
            
            # Migration 2: Fix accounts.updated_at default
            print("   📋 Migration 2: Accounts updated_at column...")
            try:
                # Update any NULL values
                result = await conn.execute(
                    text("SELECT COUNT(*) FROM accounts WHERE updated_at IS NULL")
                )
                null_count = result.scalar()
                
                if null_count and null_count > 0:
                    await conn.execute(
                        text("UPDATE accounts SET updated_at = NOW() WHERE updated_at IS NULL")
                    )
                    print(f"      + Updated {null_count} NULL values to current timestamp")
                
                # Set default
                await conn.execute(
                    text("ALTER TABLE accounts ALTER COLUMN updated_at SET DEFAULT NOW()")
                )
                print("      ✓ Set DEFAULT NOW() for updated_at")
            except Exception as e:
                print(f"      ⚠️  Skipping (may already be done): {e}")
        
        print("✅ All migrations completed")
        return True
    except Exception as e:
        print(f"⚠️  Migration error: {e}")
        return False

def main():
    """Start the application with tunnel and migrations"""
    
    # Setup tunnel
    if not setup_tunnel():
        sys.exit(1)
    
    # Run migrations
    try:
        success = asyncio.run(run_migrations())
        if not success:
            print("⚠️  Migration had errors, continuing anyway...")
    except Exception as e:
        print(f"⚠️  Could not run migrations: {e}")
    
    # Start the server
    print("\n🚀 Starting Finanza Bank application...")
    print("   Running on http://0.0.0.0:8000")
    
    os.system("python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
        cleanup_tunnel()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        cleanup_tunnel()
        sys.exit(1)
