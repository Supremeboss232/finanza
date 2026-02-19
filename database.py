# database.py
# Establishes connection to SQL database (Postgres/MySQL) and ORM setup.

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from config import settings # Assuming config.py defines DATABASE_URL

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

def get_db_url():
    """Get the database URL for use in migration scripts."""
    return settings.DATABASE_URL

def get_alembic_db_url():
    """Get the synchronous database URL for Alembic migrations."""
    return settings.ALEMBIC_DATABASE_URL or settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

# Use connection pooling for better stability
# NullPool: No pooling, creates new connection for each request (safest for async)
# asyncpg SSL mode: "prefer" = try SSL but don't fail if unavailable, "require" = SSL mandatory
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False,
    poolclass=NullPool,
    connect_args={
        "timeout": 30,
        "server_settings": {"application_name": "financial_services"},
        "ssl": "prefer"  # asyncpg: try SSL, fall back to plain if unavailable
    }
)

SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Better for read-heavy operations
)

Base = declarative_base()
