"""
Rate Limiting Middleware with Device ID Tracking
================================================

Implements token bucket-style rate limiting using in-memory cache.
Tracks requests per device_id and enforces configurable limits.

RULES:
1. Each device_id gets separate rate limit bucket
2. Buckets reset every minute (configurable)
3. Admin operations have higher limits than normal users
4. Excessive violations trigger automatic blocking
"""

import asyncio
import time
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

log = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """Rate limit tiers based on user role"""
    STANDARD = {"requests_per_minute": 10, "burst_size": 20}
    ADMIN = {"requests_per_minute": 100, "burst_size": 200}
    TREASURY = {"requests_per_minute": 150, "burst_size": 300}
    SUPER_ADMIN = {"requests_per_minute": 300, "burst_size": 500}


@dataclass
class TokenBucket:
    """Token bucket for rate limiting"""
    capacity: float
    tokens: float = field(init=False)
    last_refill: float = field(default_factory=time.time)
    refill_rate: float = 0.0  # tokens added per second
    blocked_until: Optional[float] = None
    violation_count: int = 0
    
    def __post_init__(self):
        self.tokens = self.capacity
        # Calculate refill rate based on capacity (1 minute window)
        self.refill_rate = self.capacity / 60.0
    
    def is_blocked(self) -> bool:
        """Check if device is currently blocked"""
        if self.blocked_until is None:
            return False
        if time.time() > self.blocked_until:
            self.blocked_until = None
            self.violation_count = 0
            return False
        return True
    
    def refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self.refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def block(self, seconds: int = 300):
        """Block device for specified seconds (default 5 minutes)"""
        self.blocked_until = time.time() + seconds
        self.violation_count += 1
        log.warning(f"Device blocked. Violation count: {self.violation_count}")


class RateLimiter:
    """
    Rate limiter with device ID tracking.
    
    Usage:
        limiter = RateLimiter(default_tier=RateLimitTier.ADMIN)
        
        # Check if request allowed
        is_allowed, remaining, reset_time = limiter.check_rate_limit(
            device_id="DEV-abc123",
            user_role="SUPER_ADMIN"
        )
        
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Reset in {reset_time}s"
            )
    """
    
    def __init__(self, default_tier: RateLimitTier = RateLimitTier.STANDARD):
        self.buckets: Dict[str, TokenBucket] = {}
        self.default_tier = default_tier
        self.lock = asyncio.Lock()
        self.blocked_devices: Dict[str, datetime] = {}
    
    def _get_tier(self, user_role: Optional[str] = None) -> RateLimitTier:
        """Get rate limit tier based on user role"""
        if not user_role:
            return self.default_tier
        
        role_upper = user_role.upper()
        if role_upper == "SUPER_ADMIN":
            return RateLimitTier.SUPER_ADMIN
        elif role_upper == "TREASURY":
            return RateLimitTier.TREASURY
        elif role_upper in ["ADMIN", "STANDARD_ADMIN"]:
            return RateLimitTier.ADMIN
        else:
            return RateLimitTier.STANDARD
    
    def _get_or_create_bucket(self, device_id: str, tier: RateLimitTier) -> TokenBucket:
        """Get or create rate limit bucket for device"""
        if device_id not in self.buckets:
            tier_config = tier.value
            self.buckets[device_id] = TokenBucket(
                capacity=tier_config["burst_size"],
            )
            self.buckets[device_id].refill_rate = tier_config["requests_per_minute"] / 60.0
        return self.buckets[device_id]
    
    def check_rate_limit(
        self,
        device_id: str,
        user_role: Optional[str] = None,
        cost: float = 1.0
    ) -> Tuple[bool, int, float]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            device_id: Unique device identifier
            user_role: User role for tier selection
            cost: Token cost of this request (default 1.0)
        
        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        tier = self._get_tier(user_role)
        bucket = self._get_or_create_bucket(device_id, tier)
        
        # Check if blocked
        if bucket.is_blocked():
            reset_time = bucket.blocked_until - time.time()
            return False, 0, max(0, reset_time)
        
        # Try to consume tokens
        if bucket.consume(cost):
            tier_config = tier.value
            remaining = int(bucket.tokens)
            return True, remaining, 0.0
        else:
            # Rate limit exceeded
            bucket.violation_count += 1
            
            # Progressive blocking: more violations = longer block
            block_duration = min(3600, 60 * (2 ** bucket.violation_count))  # Max 1 hour
            bucket.block(block_duration)
            
            reset_time = bucket.blocked_until - time.time()
            return False, 0, reset_time
    
    def get_status(self, device_id: str) -> Dict:
        """Get rate limit status for device"""
        if device_id not in self.buckets:
            return {"status": "new_device", "requests_remaining": "unlimited"}
        
        bucket = self.buckets[device_id]
        bucket.refill()
        
        return {
            "status": "blocked" if bucket.is_blocked() else "active",
            "requests_remaining": int(bucket.tokens),
            "blocked_until": bucket.blocked_until,
            "violation_count": bucket.violation_count,
            "capacity": int(bucket.capacity)
        }
    
    def reset_device(self, device_id: str):
        """Reset rate limit for device (admin only)"""
        if device_id in self.buckets:
            self.buckets[device_id].tokens = self.buckets[device_id].capacity
            self.buckets[device_id].blocked_until = None
            self.buckets[device_id].violation_count = 0
            log.info(f"Rate limit reset for device: {device_id}")
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Get rate limit status for all devices (admin only)"""
        return {
            device_id: self.get_status(device_id)
            for device_id in self.buckets
        }
    
    def cleanup_old_buckets(self, max_age_hours: int = 24):
        """Remove unused buckets to prevent memory bloat"""
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        
        old_devices = [
            device_id for device_id, bucket in self.buckets.items()
            if bucket.last_refill < cutoff
        ]
        
        for device_id in old_devices:
            del self.buckets[device_id]
        
        if old_devices:
            log.info(f"Cleaned up {len(old_devices)} old rate limit buckets")
        
        return len(old_devices)


# Global rate limiter instance
rate_limiter = RateLimiter(default_tier=RateLimitTier.ADMIN)


# FastAPI rate limit dependency
async def check_rate_limit(
    device_id: str,
    user_role: Optional[str] = None,
    cost: float = 1.0
) -> Dict:
    """
    FastAPI dependency for rate limiting.
    
    Usage in endpoint:
        @app.post("/api/fund/transfer")
        async def fund_transfer(
            payload: FundTransferRequest,
            rate_limit_result: Dict = Depends(lambda: check_rate_limit(...))
        ):
            if not rate_limit_result['allowed']:
                raise HTTPException(429, "Rate limit exceeded")
    """
    is_allowed, remaining, reset_time = rate_limiter.check_rate_limit(
        device_id=device_id,
        user_role=user_role,
        cost=cost
    )
    
    return {
        "allowed": is_allowed,
        "remaining": remaining,
        "reset_time": reset_time,
        "device_id": device_id,
        "role": user_role or "unknown"
    }


# Middleware to extract device_id from headers
async def extract_device_id(request):
    """Extract device_id from request headers or generate new one"""
    device_id = request.headers.get("X-Device-Id")
    
    if not device_id:
        device_id = request.headers.get("Device-ID")
    
    if not device_id:
        device_id = request.headers.get("User-Agent", "unknown")
    
    return device_id or "unknown"
