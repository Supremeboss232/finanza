#!/usr/bin/env python3
"""
EC2 Database Connection Verification Script
Tests if the database tunnel is working correctly
"""

import os
import sys
import asyncio
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

def check_env_file():
    """Check if .env file exists and has correct DATABASE_URL."""
    print("\n" + "="*70)
    print("1. CHECKING .ENV FILE")
    print("="*70)
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print(f"❌ .env file not found!")
        return False
    
    print(f"✅ Found .env file")
    
    with open(env_path) as f:
        content = f.read()
        if "DATABASE_URL" in content:
            # Extract URL (mask password)
            for line in content.split('\n'):
                if line.startswith('DATABASE_URL='):
                    url = line.split('=', 1)[1]
                    masked_url = url.replace('Supposedbe5', '***')
                    print(f"✅ DATABASE_URL configured: {masked_url}")
                    return True
    
    print(f"❌ DATABASE_URL not found in .env")
    return False

def check_pem_file():
    """Check if BankingBackendKey.pem exists."""
    print("\n" + "="*70)
    print("2. CHECKING SSH KEY FILE")
    print("="*70)
    
    pem_path = Path("BankingBackendKey.pem")
    
    if not pem_path.exists():
        print(f"❌ BankingBackendKey.pem not found!")
        return False
    
    print(f"✅ Found BankingBackendKey.pem")
    return True

def check_python_dependencies():
    """Check if required Python packages are installed."""
    print("\n" + "="*70)
    print("3. CHECKING PYTHON DEPENDENCIES")
    print("="*70)
    
    required = [
        'sqlalchemy',
        'psycopg2',
        'pydantic',
    ]
    
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"   Install with: pip install -r requirements.txt")
        return False
    
    print(f"\n✅ All dependencies installed")
    return True

async def test_database_connection():
    """Test actual database connection."""
    print("\n" + "="*70)
    print("4. TESTING DATABASE CONNECTION")
    print("="*70)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    from config import settings
    
    print(f"\nTesting connection to: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            
        await engine.dispose()
        
        print(f"✅ Database connection successful!")
        print(f"✅ Query executed: SELECT 1 → {value}")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"\n💡 Troubleshooting:")
        print(f"   1. Is SSH tunnel open? Run: .\\setup_ec2_tunnel.ps1")
        print(f"   2. Is database running on localhost:5432?")
        print(f"   3. Are credentials correct in .env?")
        return False

async def main():
    """Run all checks."""
    print("\n" + "="*70)
    print("EC2 DATABASE CONNECTION VERIFICATION")
    print("="*70)
    
    checks = [
        ("Configuration Files", check_env_file),
        ("SSH Key File", check_pem_file),
        ("Python Dependencies", check_python_dependencies),
    ]
    
    results = {}
    
    for name, check in checks:
        try:
            results[name] = check()
        except Exception as e:
            print(f"❌ Error during {name}: {e}")
            results[name] = False
    
    # Test database if everything else passes
    if all(results.values()):
        try:
            results["Database Connection"] = await test_database_connection()
        except Exception as e:
            print(f"❌ Error testing database: {e}")
            results["Database Connection"] = False
    else:
        print("\n⏭️  Skipping database test due to earlier failures")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
    
    if all(results.values()):
        print("\n" + "="*70)
        print("✅ ALL CHECKS PASSED!")
        print("="*70)
        print("\n🚀 You're ready to start developing!")
        print("\nNext steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Run migrations (if needed): alembic upgrade head")
        print("  3. Start your app: python main.py")
        return 0
    else:
        print("\n" + "="*70)
        print("❌ SOME CHECKS FAILED")
        print("="*70)
        print("\nPlease fix the issues above and try again.")
        print("\nFor help, see EC2_CONNECTION_SETUP.md or EC2_QUICK_START.md")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
