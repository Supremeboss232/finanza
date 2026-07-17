"""
Token Blacklist Cleanup Service

Automatically cleans up expired tokens from the blacklist table.

This prevents the database from growing indefinitely with expired token entries.
A scheduled job runs periodically to delete tokens that have already expired.

Configuration:
- Cleanup interval: every 60 minutes (configurable)
- Cleanup window: deletes tokens where expires_at < NOW()
- Logging: logs count of deleted tokens for audit trail
"""

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from models import TokenBlacklist
from database import SessionLocal
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


class TokenCleanupService:
    """Service for cleaning up expired tokens from the blacklist"""

    @staticmethod
    async def cleanup_expired_tokens(db: AsyncSession) -> int:
        """
        Delete expired tokens from the blacklist.
        
        Returns:
            int: Number of tokens deleted
        """
        try:
            now = datetime.utcnow()
            
            # Find tokens that have expired
            result = await db.execute(
                select(TokenBlacklist).where(TokenBlacklist.expires_at < now)
            )
            expired_tokens = result.scalars().all()
            count = len(expired_tokens)
            
            if count == 0:
                logger.debug("Token cleanup: No expired tokens found")
                return 0
            
            # Delete the expired tokens
            await db.execute(
                delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
            )
            await db.commit()
            
            logger.info(
                f"Token cleanup completed: Deleted {count} expired token(s). "
                f"Cleanup time: {now.isoformat()}"
            )
            return count
            
        except Exception as e:
            logger.error(f"Error during token cleanup: {str(e)}", exc_info=True)
            await db.rollback()
            return 0

    @staticmethod
    async def cleanup_wrapper():
        """
        Wrapper function for scheduler to call.
        Creates its own database session.
        """
        async with SessionLocal() as db:
            await TokenCleanupService.cleanup_expired_tokens(db)

    @staticmethod
    def register_cleanup_scheduler(app_scheduler: AsyncIOScheduler, interval_minutes: int = 60):
        """
        Register the token cleanup job with APScheduler.
        
        Args:
            app_scheduler: AsyncIOScheduler instance
            interval_minutes: How often to run cleanup (default: 60 minutes)
        """
        app_scheduler.add_job(
            TokenCleanupService.cleanup_wrapper,
            "interval",
            minutes=interval_minutes,
            id="token_cleanup",
            name="Token Blacklist Cleanup",
            coalesce=True,
            max_instances=1
        )
        logger.info(
            f"Token cleanup scheduled: Every {interval_minutes} minutes"
        )


# Configuration constants
TOKEN_CLEANUP_INTERVAL_MINUTES = 60  # Run cleanup every hour
TOKEN_CLEANUP_ENABLED = True  # Can be controlled via environment variable
