"""
Rate Limiting Service
====================
Prevents abuse of admin endpoints and API endpoints.

Features:
- Per-user rate limiting
- Per-IP rate limiting
- Per-endpoint rate limiting
- Sliding window algorithm
- Configurable limits by endpoint
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import asyncio
from collections import defaultdict

import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter with sliding window algorithm"""
    
    def __init__(self):
        # Format: {(identifier_type, identifier, endpoint): [(timestamp, request_count)]}
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(
        self,
        identifier: str,
        identifier_type: str = "user",  # "user", "ip", "endpoint"
        endpoint: str = "",
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ) -> Tuple[bool, dict]:
        """
        Check if request is allowed under rate limit.
        
        Returns: (is_allowed, info)
        - is_allowed: bool
        - info: {
            "allowed": bool,
            "requests_remaining": int,
            "retry_after_seconds": int,
            "limit_window": str,
            "requests_used": int,
            "limit": int
          }
        """
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
                    "limit": requests_per_minute
                }
                logger.warning(f"Rate limit (per minute) exceeded for {identifier_type}:{identifier} on {endpoint}")
                return False, info
            
            # Check hour limit
            if requests_last_hour >= requests_per_hour:
                info = {
                    "allowed": False,
                    "requests_remaining": 0,
                    "retry_after_seconds": 3600,
                    "limit_window": "per_hour",
                    "requests_used": requests_last_hour,
                    "limit": requests_per_hour
                }
                logger.warning(f"Rate limit (per hour) exceeded for {identifier_type}:{identifier} on {endpoint}")
                return False, info
            
            # Request allowed - record it
            self.requests[key].append((now, 1))
            
            info = {
                "allowed": True,
                "requests_remaining": requests_per_minute - requests_last_min - 1,
                "retry_after_seconds": 0,
                "limit_window": "per_minute",
                "requests_used": requests_last_min + 1,
                "limit": requests_per_minute
            }
            
            return True, info


# Singleton instance
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# Rate limit configurations by endpoint type
RATE_LIMIT_CONFIG = {
    # Admin endpoints - stricter limits
    "admin_users": {"per_minute": 30, "per_hour": 500},
    "admin_transactions": {"per_minute": 30, "per_hour": 500},
    "admin_kyc": {"per_minute": 20, "per_hour": 300},
    "admin_balance": {"per_minute": 20, "per_hour": 300},
    "admin_suspend_freeze": {"per_minute": 10, "per_hour": 100},
    
    # API endpoints - normal limits
    "auth_login": {"per_minute": 5, "per_hour": 50},
    "auth_register": {"per_minute": 3, "per_hour": 30},
    "user_transactions": {"per_minute": 60, "per_hour": 1000},
    "user_transfers": {"per_minute": 30, "per_hour": 300},
    "user_deposits": {"per_minute": 20, "per_hour": 200},
}


def get_rate_limit_config(endpoint_key: str) -> dict:
    """Get rate limit config for endpoint"""
    return RATE_LIMIT_CONFIG.get(endpoint_key, {
        "per_minute": 60,
        "per_hour": 1000
    })
