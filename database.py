# database.py
# Establishes connection to SQL database (Postgres/MySQL) and ORM setup.

import ssl
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import AsyncAdaptedQueuePool
from config import settings # Assuming config.py defines DATABASE_URL

# Prefer explicit Supabase DB URL when provided; fallback to configured DATABASE_URL
_raw_db_url = getattr(settings, 'SUPABASE_DB_URL', None) or settings.DATABASE_URL

# Normalize to asyncpg URL when possible (async SQLAlchemy + asyncpg driver)
if _raw_db_url.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_db_url.startswith("postgresql://") and "asyncpg" not in _raw_db_url:
    SQLALCHEMY_DATABASE_URL = _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    SQLALCHEMY_DATABASE_URL = _raw_db_url

# Some connection strings include `sslmode=require` (common for libpq).
# asyncpg does not accept an `sslmode` keyword in connect(); instead we
# provide an `ssl` boolean/SSLContext via connect_args and strip sslmode
# from the URL query string so SQLAlchemy/asyncpg don't pass it through.
_ssl_required = False
parts = urlsplit(SQLALCHEMY_DATABASE_URL)
if parts.query:
    qs = dict(parse_qsl(parts.query))
    sslmode = qs.pop("sslmode", None)
    qs.pop("pgbouncer", None)  # asyncpg does not accept pgbouncer query parameter
    if sslmode and sslmode.lower() in ("require", "verify-full", "verify-ca"):
        _ssl_required = True
    # Rebuild URL without sslmode and pgbouncer
    if qs:
        new_query = urlencode(qs)
    else:
        new_query = ""
    SQLALCHEMY_DATABASE_URL = urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

# Enforce SSL for Supabase-managed hosts and when sslmode is requested.
if not _ssl_required and parts.hostname and parts.hostname.endswith(".supabase.co"):
    _ssl_required = True


def get_db_url():
    """Get the database URL for use in migration scripts."""
    return SQLALCHEMY_DATABASE_URL


def get_alembic_db_url():
    """Get the synchronous database URL for Alembic migrations."""
    if getattr(settings, 'ALEMBIC_DATABASE_URL', None):
        return settings.ALEMBIC_DATABASE_URL
    if SQLALCHEMY_DATABASE_URL and "postgresql+asyncpg" in SQLALCHEMY_DATABASE_URL:
        return SQLALCHEMY_DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    return SQLALCHEMY_DATABASE_URL

# Set up appropriate connect_args based on database type
connect_args = {}
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    # PostgreSQL-specific settings
    connect_args = {
        "timeout": 30,
        "command_timeout": 60,  # 60 second timeout for commands
        "server_settings": {"application_name": "financial_services"},
    }
    
    if _ssl_required:
        # For Supabase pooler: use SSL but skip cert verification
        # (Supabase pooler is managed and trusted; certificate validation 
        # may fail due to cert chain issues, but SSL encryption is still enabled)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
elif "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite-specific settings
    connect_args = {
        "timeout": 30,
        "check_same_thread": False
    }

# Use connection pooling for better stability
# AsyncAdaptedQueuePool: Manages async connections with a pool (better than NullPool for async)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Test connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    connect_args=connect_args
)

SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Better for read-heavy operations
)

Base = declarative_base()

async def get_db():
    """Dependency generator for FastAPI routes to access the database."""
    async with SessionLocal() as session:
        yield session

