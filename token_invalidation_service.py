"""
Token Invalidation Service
============================
Manages JWT token blacklisting for force logout and session termination.
Implements in-memory blacklist with TTL expiration.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """
    In-memory JWT token blacklist with TTL expiration.
    Tokens are hashed for security and automatically cleaned up after expiry.
    """
    
    def __init__(self, ttl_minutes: int = 30):
        """
        Initialize token blacklist.
        
        Args:
            ttl_minutes: How long to keep tokens in blacklist (default 30 = JWT expiry)
        """
        self.ttl_seconds = ttl_minutes * 60
        # Stores: token_hash -> {user_id, admin_id, created_at, reason}
        self._blacklist: Dict[str, dict] = {}
        # Stores: user_id -> set of token hashes (for bulk invalidation)
        self._user_tokens: Dict[int, Set[str]] = {}
        self._cleanup_task = None
    
    @staticmethod
    def _hash_token(token: str) -> str:
        """
        Hash token for secure storage.
        
        Args:
            token: JWT token string
            
        Returns:
            SHA256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def add_to_blacklist(
        self,
        token: str,
        user_id: int,
        admin_id: Optional[int] = None,
        reason: str = "force_logout"
    ) -> None:
        """
        Add token to blacklist.
        
        Args:
            token: JWT token to blacklist
            user_id: User ID who owns the token
            admin_id: Admin ID if this is an admin token
            reason: Reason for blacklisting (force_logout, password_change, etc.)
        """
        token_hash = self._hash_token(token)
        
        self._blacklist[token_hash] = {
            "user_id": user_id,
            "admin_id": admin_id,
            "created_at": datetime.utcnow(),
            "reason": reason
        }
        
        # Track by user for bulk operations
        if user_id not in self._user_tokens:
            self._user_tokens[user_id] = set()
        self._user_tokens[user_id].add(token_hash)
        
        logger.info(f"Token blacklisted for user {user_id}, reason: {reason}")
    
    async def is_blacklisted(self, token: str) -> bool:
        """
        Check if token is blacklisted.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if token is blacklisted and not expired, False otherwise
        """
        token_hash = self._hash_token(token)
        
        if token_hash not in self._blacklist:
            return False
        
        entry = self._blacklist[token_hash]
        created_at = entry.get("created_at")
        
        # Check TTL
        if datetime.utcnow() - created_at > timedelta(seconds=self.ttl_seconds):
            # Expired, remove from blacklist
            del self._blacklist[token_hash]
            user_id = entry.get("user_id")
            if user_id in self._user_tokens:
                self._user_tokens[user_id].discard(token_hash)
            return False
        
        return True
    
    async def invalidate_user_sessions(
        self,
        user_id: int,
        reason: str = "admin_forced_logout"
    ) -> int:
        """
        Invalidate all tokens for a specific user.
        
        Args:
            user_id: User ID whose sessions to invalidate
            reason: Reason for invalidation
            
        Returns:
            Number of tokens invalidated
        """
        if user_id not in self._user_tokens:
            logger.info(f"No active tokens found for user {user_id}")
            return 0
        
        count = 0
        # Get copies of token hashes before modifying the set
        token_hashes = list(self._user_tokens[user_id])
        
        for token_hash in token_hashes:
            # Update reason if already blacklisted
            if token_hash in self._blacklist:
                self._blacklist[token_hash]["reason"] = reason
            else:
                # This shouldn't happen but handle gracefully
                self._blacklist[token_hash] = {
                    "user_id": user_id,
                    "admin_id": None,
                    "created_at": datetime.utcnow(),
                    "reason": reason
                }
            count += 1
        
        logger.info(f"Invalidated {count} sessions for user {user_id}, reason: {reason}")
        return count
    
    async def invalidate_admin_sessions(
        self,
        admin_id: int,
        reason: str = "admin_revoked"
    ) -> int:
        """
        Invalidate all tokens for a specific admin.
        
        Args:
            admin_id: Admin ID whose sessions to invalidate
            reason: Reason for invalidation
            
        Returns:
            Number of tokens invalidated
        """
        count = 0
        
        # Find all tokens belonging to this admin
        for token_hash, entry in list(self._blacklist.items()):
            if entry.get("admin_id") == admin_id:
                entry["reason"] = reason
                count += 1
        
        logger.info(f"Invalidated {count} admin sessions for admin {admin_id}, reason: {reason}")
        return count
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from blacklist.
        
        Returns:
            Number of tokens removed
        """
        expired_count = 0
        now = datetime.utcnow()
        
        # Create list of expired token hashes
        expired_hashes = []
        for token_hash, entry in self._blacklist.items():
            created_at = entry.get("created_at")
            if now - created_at > timedelta(seconds=self.ttl_seconds):
                expired_hashes.append(token_hash)
        
        # Remove expired tokens
        for token_hash in expired_hashes:
            entry = self._blacklist[token_hash]
            user_id = entry.get("user_id")
            
            del self._blacklist[token_hash]
            
            # Remove from user tracking
            if user_id in self._user_tokens:
                self._user_tokens[user_id].discard(token_hash)
                if not self._user_tokens[user_id]:  # Clean up empty sets
                    del self._user_tokens[user_id]
            
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired blacklist entries")
        
        return expired_count
    
    async def start_background_cleanup(self, check_interval_seconds: int = 60) -> None:
        """
        Start background task to clean up expired tokens.
        
        Args:
            check_interval_seconds: How often to check for expired tokens
        """
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(check_interval_seconds)
                    await self.cleanup_expired_tokens()
                except Exception as e:
                    logger.error(f"Error in token blacklist cleanup loop: {e}")
        
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(cleanup_loop())
            logger.info("Token blacklist cleanup task started")
    
    async def stop_background_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Token blacklist cleanup task stopped")
    
    def get_blacklist_size(self) -> int:
        """Get current size of blacklist."""
        return len(self._blacklist)
    
    def get_user_session_count(self, user_id: int) -> int:
        """Get number of invalidated sessions for a user."""
        return len(self._user_tokens.get(user_id, set()))


# Global singleton instance
_token_blacklist: Optional[TokenBlacklist] = None


def get_token_blacklist() -> TokenBlacklist:
    """
    Get or create global token blacklist instance.
    
    Returns:
        TokenBlacklist singleton
    """
    global _token_blacklist
    if _token_blacklist is None:
        _token_blacklist = TokenBlacklist(ttl_minutes=30)  # Match JWT expiry
    return _token_blacklist
