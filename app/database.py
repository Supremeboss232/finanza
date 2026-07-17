# database.py
# Establishes connection to SQL database (Postgres/MySQL) and ORM setup.

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from config import settings # Assuming config.py defines DATABASE_URL

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Set up appropriate connect_args based on database type
connect_args = {}
if "postgresql" in SQLALCHEMY_DATABASE_URL:
    # PostgreSQL-specific settings
    connect_args = {
        "server_settings": {"application_name": "financial_services"},
        "timeout": 30
    }
elif "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite-specific settings
    connect_args = {
        "timeout": 30,
        "check_same_thread": False
    }

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # Disable echo in production for better performance
    poolclass=NullPool,  # Avoid connection pool issues with async
    connect_args=connect_args
)

SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False  # Better for read-heavy operations
)

Base = declarative_base()

# Dependency to get DB session
async def get_db():
    async with SessionLocal() as db:
        yield db
