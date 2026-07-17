"""
Supabase Client Integration

Provides a centralized Supabase client for the application.
Uses Supabase REST API (HTTPS) for database operations, which avoids DNS/network issues
with direct PostgreSQL connections and provides better compatibility across environments.

Environment: HTTPS-based, no direct PostgreSQL hostname resolution required.
"""

import logging
from supabase import create_client
from config import settings

logger = logging.getLogger(__name__)

# Verify Supabase credentials are configured
if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
    logger.warning(
        "⚠️  Supabase credentials not configured. "
        "Set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
    )
    supabase = None
    supabase_admin = None
else:
    try:
        # Initialize Supabase client with anon key (use for user operations)
        # The anon key has Row Level Security (RLS) enabled
        supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_ANON_KEY
        )
        logger.info("✅ Supabase REST API client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")
        supabase = None

    try:
        # Initialize admin client with service role key (use for admin/privileged operations)
        # The service role key bypasses RLS and should only be used server-side
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            supabase_admin = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("✅ Supabase admin client initialized")
        else:
            supabase_admin = supabase  # Fall back to anon key if service role not available
            logger.warning("⚠️  SUPABASE_SERVICE_ROLE_KEY not configured, using anon key for admin operations")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase admin client: {e}")
        supabase_admin = supabase


def get_supabase_client():
    """Get the Supabase client (anon key - use for user operations)"""
    if supabase is None:
        raise RuntimeError(
            "Supabase client not initialized. Check SUPABASE_URL and SUPABASE_ANON_KEY in .env"
        )
    return supabase


def get_supabase_admin_client():
    """Get the Supabase admin client (service role - use for admin operations)"""
    if supabase_admin is None:
        raise RuntimeError(
            "Supabase admin client not initialized. Check SUPABASE_SERVICE_ROLE_KEY in .env"
        )
    return supabase_admin


async def test_supabase_connection():
    """Test Supabase REST API connection with a simple query"""
    try:
        client = get_supabase_client()
        # Try to query a table (will fail initially if schema not migrated, but proves connection)
        response = client.table('users').select("id").limit(1).execute()
        logger.info("✅ Supabase REST API connection successful!")
        return True
    except Exception as e:
        error_msg = str(e)
        # Check if error is just missing table (expected during setup)
        if "table" in error_msg.lower() and "not found" in error_msg.lower():
            logger.info("✅ Supabase REST API connection successful (schema not yet migrated)")
            return True
        else:
            logger.error(f"❌ Supabase connection test failed: {e}")
            return False


if __name__ == "__main__":
    import asyncio
    print("\n🧪 Testing Supabase connection...")
    result = asyncio.run(test_supabase_connection())
    print(f"Result: {'✅ PASS' if result else '❌ FAIL'}\n")

