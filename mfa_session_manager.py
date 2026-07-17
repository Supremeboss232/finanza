"""
MFA Session State Management
==============================
Manages temporary state during MFA setup/verification workflow.
Stores secrets and provisioning URIs between setup and verify steps.
Uses in-memory dict with TTL for efficient temporary storage.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MFASessionManager:
    """Manages MFA setup session state with TTL cleanup."""
    
    def __init__(self, ttl_minutes: int = 5):
        """
        Initialize MFA session manager.
        
        Args:
            ttl_minutes: Time-to-live for session data (default 5 minutes)
        """
        self.ttl_seconds = ttl_minutes * 60
        # Session storage: admin_id -> {secret, provisioning_uri, qr_code, backup_codes, created_at}
        self._sessions: Dict[int, dict] = {}
        self._cleanup_task = None
    
    async def store_setup_session(
        self,
        admin_id: int,
        secret: str,
        provisioning_uri: str,
        qr_code: str,
        backup_codes: list
    ) -> None:
        """
        Store MFA setup session data.
        
        Args:
            admin_id: Admin user ID
            secret: TOTP secret
            provisioning_uri: URI for QR code
            qr_code: Base64 encoded QR code image
            backup_codes: List of backup codes
        """
        self._sessions[admin_id] = {
            "secret": secret,
            "provisioning_uri": provisioning_uri,
            "qr_code": qr_code,
            "backup_codes": backup_codes,
            "created_at": datetime.utcnow()
        }
        logger.info(f"MFA setup session stored for admin {admin_id}")
    
    async def retrieve_setup_session(
        self,
        admin_id: int
    ) -> Optional[dict]:
        """
        Retrieve MFA setup session data.
        
        Args:
            admin_id: Admin user ID
            
        Returns:
            Session data dict or None if expired/not found
        """
        if admin_id not in self._sessions:
            logger.warning(f"No MFA setup session found for admin {admin_id}")
            return None
        
        session = self._sessions[admin_id]
        created_at = session.get("created_at")
        
        # Check TTL
        if datetime.utcnow() - created_at > timedelta(seconds=self.ttl_seconds):
            logger.info(f"MFA setup session expired for admin {admin_id}")
            del self._sessions[admin_id]
            return None
        
        return session
    
    async def clear_setup_session(self, admin_id: int) -> None:
        """
        Clear MFA setup session after successful verification.
        
        Args:
            admin_id: Admin user ID
        """
        if admin_id in self._sessions:
            del self._sessions[admin_id]
            logger.info(f"MFA setup session cleared for admin {admin_id}")
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_count = 0
        now = datetime.utcnow()
        
        # Create list of expired session IDs to avoid dict modification during iteration
        expired_ids = []
        for admin_id, session in self._sessions.items():
            created_at = session.get("created_at")
            if now - created_at > timedelta(seconds=self.ttl_seconds):
                expired_ids.append(admin_id)
        
        # Delete expired sessions
        for admin_id in expired_ids:
            del self._sessions[admin_id]
            expired_count += 1
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired MFA sessions")
        
        return expired_count
    
    async def start_background_cleanup(self, check_interval_seconds: int = 60) -> None:
        """
        Start background task to clean up expired sessions.
        
        Args:
            check_interval_seconds: How often to check for expired sessions
        """
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(check_interval_seconds)
                    await self.cleanup_expired_sessions()
                except Exception as e:
                    logger.error(f"Error in MFA session cleanup loop: {e}")
        
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(cleanup_loop())
            logger.info("MFA session cleanup task started")
    
    async def stop_background_cleanup(self) -> None:
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("MFA session cleanup task stopped")
    
    def get_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)


# Global singleton instance
_mfa_session_manager: Optional[MFASessionManager] = None


def get_mfa_session_manager() -> MFASessionManager:
    """
    Get or create global MFA session manager instance.
    
    Returns:
        MFASessionManager singleton
    """
    global _mfa_session_manager
    if _mfa_session_manager is None:
        _mfa_session_manager = MFASessionManager(ttl_minutes=5)
    return _mfa_session_manager
