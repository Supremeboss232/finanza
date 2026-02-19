#!/usr/bin/env python3
"""Initialize database with proper tables for Phase 2 testing"""

import asyncio
import sys
sys.path.insert(0, '.')

from database import SessionLocal, engine
from models import Base
import models

async def init_db():
    """Initialize database tables"""
    print("Initializing database tables...")
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("[OK] Database tables created!")

if __name__ == "__main__":
    asyncio.run(init_db())
