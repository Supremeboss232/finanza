"""
Enhanced Rate Limiting Service
================================
Supports multiple backends: memory (in-process), Redis, or database

Configuration via config.py:
- RATE_LIMITER_BACKEND: "memory", "redis", or "database"
- RATE_LIMIT_ADMIN_ENDPOINTS_PER_MIN: Default 30
- RATE_LIMIT_ADMIN_ENDPOINTS_PER_HOUR: Default 500
- RATE_LIMIT_API_ENDPOINTS_PER_MIN: Default 60
- RATE_LIMIT_API_ENDPOINTS_PER_HOUR: Default 1000
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict
import asyncio
from collections import defaultdict
import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RateLimiterBackend(ABC):
    """Abstract base for rate limiter backends"""
    
    @abstractmethod
    async def is_allowed(
        self,
        identifier: str,
        identifier_type: str,
        endpoint: str,
        requests_per_minute: int,
        requests_per_hour: int
    ) -> Tuple[bool, Dict]:
        """Check if request is allowed"""
        pass


class MemoryRateLimiter(RateLimiterBackend):
    """In-memory rate limiter with sliding window algorithm"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(
        self,
        identifier: str,
        identifier_type: str = "user",
        endpoint: str = "",
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ) -> Tuple[bool, Dict]:
        """Check if request is allowed under rate limit"""
        
        async with self.lock:
            key = (identifier_type, identifier, endpoint)
            now = datetime.utcnow()
            
            # Clean old requests (older than 1 hour)
            one_hour_ago = now - timedelta(hours=1)
            self.requests[key] = [
                (ts, count) for ts, count in self.requests[key]
                if ts > one_hour_ago
            ]
            
            # Count requests in last minute
            one_min_ago = now - timedelta(minutes=1)
            requests_last_min = sum(
                count for ts, count in self.requests[key]
                if ts > one_min_ago
            )
            
            # Count requests in last hour
            requests_last_hour = sum(
                count for ts, count in self.requests[key]
            )
            
            # Check minute limit
            if requests_last_min >= requests_per_minute:
                info = {
                    "allowed": False,
                    "requests_remaining": 0,
                    "retry_after_seconds": 60 - (now - one_min_ago).seconds,
                    "limit_window": "per_minute",
                    "requests_used": requests_last_min,
                    "limit": requests_per_minute,
                    "backend": "memory"
                }
                logger.warning(f"Rate limit (per minute) exceeded for {identifier_type}:{identifier}")
                return False, info
            
            # Check hour limit
            if requests_last_hour >= requests_per_hour:
                info = {
                    "allowed": False,
                    "requests_remaining": 0,
                    "retry_after_seconds": 3600,
                    "limit_window": "per_hour",
                    "requests_used": requests_last_hour,
                    "limit": requests_per_hour,
                    "backend": "memory"
                }
                logger.warning(f"Rate limit (per hour) exceeded for {identifier_type}:{identifier}")
                return False, info
            
            # Request allowed - record it
            self.requests[key].append((now, 1))
            
            info = {
                "allowed": True,
                "requests_remaining": requests_per_minute - requests_last_min - 1,
                "retry_after_seconds": 0,
                "limit_window": "per_minute",
                "requests_used": requests_last_min + 1,
                "limit": requests_per_minute,
                "backend": "memory"
            }
            
            return True, info


class RedisRateLimiter(RateLimiterBackend):
    """Redis-based rate limiter for distributed systems"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
    
    async def connect(self):
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, falling back to memory limiter")
            return False
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis rate limiter backend")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def is_allowed(
        self,
        identifier: str,
        identifier_type: str = "user",
        endpoint: str = "",
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ) -> Tuple[bool, Dict]:
        """Check if request is allowed using Redis"""
        
        if not self.redis_client:
            logger.warning("Redis client not available")
            return True, {"allowed": True, "backend": "redis-unavailable"}
        
        try:
            key_min = f"rate_limit:min:{identifier_type}:{identifier}:{endpoint}"
            key_hour = f"rate_limit:hour:{identifier_type}:{identifier}:{endpoint}"
            now = datetime.utcnow().timestamp()
            
            # Increment minute counter
            await self.redis_client.incr(key_min)
            await self.redis_client.expire(key_min, 60)
            
            # Increment hour counter
            await self.redis_client.incr(key_hour)
            await self.redis_client.expire(key_hour, 3600)
            
            requests_last_min = int(await self.redis_client.get(key_min) or 0)
            requests_last_hour = int(await self.redis_client.get(key_hour) or 0)
            
            # Check limits
            if requests_last_min > requests_per_minute:
                return False, {
                    "allowed": False,
                    "requests_remaining": 0,
                    "limit_window": "per_minute",
                    "requests_used": requests_last_min,
                    "limit": requests_per_minute,
                    "backend": "redis"
                }
            
            if requests_last_hour > requests_per_hour:
                return False, {
                    "allowed": False,
                    "requests_remaining": 0,
                    "limit_window": "per_hour",
                    "requests_used": requests_last_hour,
                    "limit": requests_per_hour,
                    "backend": "redis"
                }
            
            return True, {
                "allowed": True,
                "requests_remaining": requests_per_minute - requests_last_min,
                "requests_used": requests_last_min,
                "limit": requests_per_minute,
                "backend": "redis"
            }
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fail open - allow request if Redis fails
            return True, {"allowed": True, "backend": "redis-error"}


class DatabaseRateLimiter(RateLimiterBackend):
    """Database-based rate limiter for persistence"""
    
    def __init__(self):
        self.db_session = None
    
    async def is_allowed(
        self,
        identifier: str,
        identifier_type: str = "user",
        endpoint: str = "",
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ) -> Tuple[bool, Dict]:
        """Check if request is allowed using database"""
        
        if not self.db_session:
            logger.warning("Database session not available for rate limiting")
            return True, {"allowed": True, "backend": "database-unavailable"}
        
        try:
            from sqlalchemy import select, func, and_
            from models import RateLimitLog
            
            now = datetime.utcnow()
            one_min_ago = now - timedelta(minutes=1)
            one_hour_ago = now - timedelta(hours=1)
            
            # Count requests in last minute
            min_query = select(func.count(RateLimitLog.id)).where(
                and_(
                    RateLimitLog.identifier == identifier,
                    RateLimitLog.identifier_type == identifier_type,
                    RateLimitLog.endpoint == endpoint,
                    RateLimitLog.created_at > one_min_ago
                )
            )
            requests_last_min = await self.db_session.scalar(min_query) or 0
            
            # Count requests in last hour
            hour_query = select(func.count(RateLimitLog.id)).where(
                and_(
                    RateLimitLog.identifier == identifier,
                    RateLimitLog.identifier_type == identifier_type,
                    RateLimitLog.endpoint == endpoint,
                    RateLimitLog.created_at > one_hour_ago
                )
            )
            requests_last_hour = await self.db_session.scalar(hour_query) or 0
            
            # Check limits
            if requests_last_min >= requests_per_minute:
                return False, {
                    "allowed": False,
                    "requests_remaining": 0,
                    "limit_window": "per_minute",
                    "requests_used": requests_last_min,
                    "limit": requests_per_minute,
                    "backend": "database"
                }
            
            if requests_last_hour >= requests_per_hour:
                return False, {
                    "allowed": False,
                    "requests_remaining": 0,
                    "limit_window": "per_hour",
                    "requests_used": requests_last_hour,
                    "limit": requests_per_hour,
                    "backend": "database"
                }
            
            # Log this request
            log = RateLimitLog(
                identifier=identifier,
                identifier_type=identifier_type,
                endpoint=endpoint
            )
            self.db_session.add(log)
            await self.db_session.commit()
            
            return True, {
                "allowed": True,
                "requests_remaining": requests_per_minute - requests_last_min - 1,
                "requests_used": requests_last_min + 1,
                "limit": requests_per_minute,
                "backend": "database"
            }
        except Exception as e:
            logger.error(f"Database rate limiting error: {e}")
            return True, {"allowed": True, "backend": "database-error"}


class EnhancedRateLimiter:
    """
    Rate limiter that can use different backends
    Configured via config.py RATE_LIMITER_BACKEND setting
    """
    
    def __init__(self, backend: str = "memory", redis_url: str = None):
        self.backend_type = backend.lower()
        
        if self.backend_type == "redis":
            self.backend = RedisRateLimiter(redis_url or "redis://localhost:6379")
        elif self.backend_type == "database":
            self.backend = DatabaseRateLimiter()
        else:  # Default to memory
            self.backend = MemoryRateLimiter()
            self.backend_type = "memory"
    
    async def is_allowed(
        self,
        identifier: str,
        identifier_type: str = "user",
        endpoint: str = "",
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ) -> Tuple[bool, Dict]:
        """Check if request is allowed"""
        return await self.backend.is_allowed(
            identifier,
            identifier_type,
            endpoint,
            requests_per_minute,
            requests_per_hour
        )


# Singleton instance
_rate_limiter = None


def get_rate_limiter() -> EnhancedRateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        from config import settings
        _rate_limiter = EnhancedRateLimiter(
            backend=settings.RATE_LIMITER_BACKEND,
            redis_url=settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else None
        )
    return _rate_limiter


# Rate limit configurations (can be overridden via config)
def get_rate_limit_config_from_settings():
    """Get rate limit config from settings"""
    from config import settings
    return {
        "admin_endpoints_per_min": settings.RATE_LIMIT_ADMIN_ENDPOINTS_PER_MIN,
        "admin_endpoints_per_hour": settings.RATE_LIMIT_ADMIN_ENDPOINTS_PER_HOUR,
        "api_endpoints_per_min": settings.RATE_LIMIT_API_ENDPOINTS_PER_MIN,
        "api_endpoints_per_hour": settings.RATE_LIMIT_API_ENDPOINTS_PER_HOUR,
        "auth_per_min": settings.RATE_LIMIT_AUTH_PER_MIN,
        "auth_per_hour": settings.RATE_LIMIT_AUTH_PER_HOUR,
    }
