"""
JWT Token Blacklist Service
============================
Manages token revocation for force logout and security incidents.
Stores blacklisted JWT tokens with expiration timestamps.
"""

from datetime import datetime, timedelta
from typing import Set, Dict
import logging
import asyncio

logger = logging.getLogger(__name__)


class TokenBlacklistService:
    """Manages JWT token blacklisting for logout and revocation."""
    
    # Token blacklist: {token_jti: expiration_timestamp}
    _blacklist: Dict[str, datetime] = {}
    _lock = asyncio.Lock()
    
    @classmethod
    async def revoke_token(
        cls,
        token_jti: str,
        expires_at: datetime
    ) -> bool:
        """
        Add token to blacklist.
        
        Args:
            token_jti: JWT JTI (JWT ID) claim - unique identifier
            expires_at: Token expiration datetime
            
        Returns:
            True if added successfully
        """
        try:
            cls._blacklist[token_jti] = expires_at
            logger.info(f"Token revoked: {token_jti}, expires: {expires_at}")
            return True
        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False
    
    @classmethod
    async def revoke_user_tokens(
        cls,
        user_id: int,
        token_list: list
    ) -> bool:
        """
        Revoke all tokens for a specific user.
        
        Args:
            user_id: User ID (for logging)
            token_list: List of token JTI strings to revoke
            
        Returns:
            True if all revoked successfully
        """
        try:
            now = datetime.now()
            for token_jti in token_list:
                cls._blacklist[token_jti] = now + timedelta(days=1)
            
            logger.info(f"Revoked {len(token_list)} tokens for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error revoking user tokens: {e}")
            return False
    
    @classmethod
    async def is_token_revoked(cls, token_jti: str) -> bool:
        """
        Check if token is revoked.
        
        Args:
            token_jti: JWT JTI claim
            
        Returns:
            True if token is revoked and still valid (not expired), False otherwise
        """
        try:
            # Clean up expired tokens
            await cls._cleanup_expired()
            
            # Check if token is in blacklist
            if token_jti in cls._blacklist:
                expiration = cls._blacklist[token_jti]
                if datetime.now() < expiration:
                    logger.warning(f"Access attempt with revoked token: {token_jti}")
                    return True
                else:
                    # Token expired from blacklist, remove it
                    del cls._blacklist[token_jti]
            
            return False
        except Exception as e:
            logger.error(f"Error checking token revocation: {e}")
            return False
    
    @classmethod
    async def _cleanup_expired(cls) -> None:
        """Remove expired tokens from blacklist (automatic)."""
        try:
            now = datetime.now()
            expired_jtis = [
                jti for jti, exp_time in cls._blacklist.items()
                if now > exp_time
            ]
            
            for jti in expired_jtis:
                del cls._blacklist[jti]
            
            if expired_jtis:
                logger.debug(f"Cleaned up {len(expired_jtis)} expired blacklist entries")
                
        except Exception as e:
            logger.error(f"Error during blacklist cleanup: {e}")
    
    @classmethod
    async def clear_all(cls) -> bool:
        """Clear entire blacklist (for testing/reset)."""
        try:
            cls._blacklist.clear()
            logger.info("Token blacklist cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing blacklist: {e}")
            return False
    
    @classmethod
    async def get_stats(cls) -> dict:
        """Get blacklist statistics."""
        try:
            await cls._cleanup_expired()
            return {
                "total_revoked_tokens": len(cls._blacklist),
                "cleanup_candidate": sum(
                    1 for exp_time in cls._blacklist.values()
                    if datetime.now() > exp_time
                )
            }
        except Exception as e:
            logger.error(f"Error getting blacklist stats: {e}")
            return {"error": str(e)}


# Singleton instance
token_blacklist_service = TokenBlacklistService()


def get_token_blacklist_service() -> TokenBlacklistService:
    """Dependency injection for token blacklist service."""
    return token_blacklist_service
