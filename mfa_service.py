"""
Multi-Factor Authentication (MFA) Service
==========================================
Provides TOTP-based 2FA/MFA for admin accounts.

Features:
- TOTP secret generation
- QR code generation for authenticator apps
- TOTP token validation
- Backup codes generation
- Session binding with MFA verification
"""

import pyotp
import qrcode
import io
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import User as DBUser, AuditLog
import logging

logger = logging.getLogger(__name__)


class MFAService:
    """Multi-Factor Authentication Service"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp(secret: str) -> pyotp.TOTP:
        """Get TOTP object from secret"""
        return pyotp.TOTP(secret)
    
    @staticmethod
    def verify_token(secret: str, token: str) -> bool:
        """
        Verify a TOTP token against secret.
        Allows 1 time window (30 sec) of drift for clock skew.
        """
        try:
            totp = pyotp.TOTP(secret)
            # Allow 1 time step (30 sec) of drift
            return totp.verify(token, valid_window=1)
        except Exception as e:
            logger.error(f"TOTP verification error: {e}")
            return False
    
    @staticmethod
    def get_provisioning_uri(secret: str, email: str, app_name: str = "Finanza Bank Admin") -> str:
        """
        Get provisioning URI for QR code.
        Used by authenticator apps (Google Authenticator, Authy, etc.)
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=app_name
        )
    
    @staticmethod
    def generate_qr_code(provisioning_uri: str) -> str:
        """
        Generate QR code image and return as base64 data URL.
        Can be directly embedded in HTML as <img src="data_url">
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """
        Generate backup codes for account recovery.
        Each code is a one-time use code in case user loses authenticator.
        """
        codes = []
        for _ in range(count):
            # Generate 8-character codes
            code = pyotp.random_base32()[:8].upper()
            codes.append(code)
        return codes
    
    @staticmethod
    async def enable_mfa_for_user(
        db_session: AsyncSession,
        user_id: int,
        secret: str,
        backup_codes: List[str],
        admin_id: Optional[int] = None
    ) -> bool:
        """
        Enable MFA for a user.
        Stores MFA secret and backup codes (hashed) in database.
        """
        try:
            user = await db_session.get(DBUser, user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False
            
            # Store MFA secret (in production, encrypt this)
            user.mfa_secret = secret
            user.mfa_enabled = True
            
            # Store hashed backup codes (comma-separated)
            from auth_utils import get_password_hash
            hashed_codes = ",".join([get_password_hash(code) for code in backup_codes])
            user.mfa_backup_codes = hashed_codes
            
            user.mfa_enabled_at = datetime.utcnow()
            
            await db_session.flush()
            
            # Log action
            if admin_id:
                audit = AuditLog(
                    action_type="MFA_ENABLED",
                    admin_id=admin_id,
                    user_id=user_id,
                    resource_type="User",
                    resource_id=str(user_id),
                    details=f"MFA enabled by admin {admin_id}"
                )
                db_session.add(audit)
            
            await db_session.commit()
            logger.info(f"MFA enabled for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling MFA: {e}")
            return False
    
    @staticmethod
    async def disable_mfa_for_user(
        db_session: AsyncSession,
        user_id: int,
        admin_id: Optional[int] = None
    ) -> bool:
        """Disable MFA for a user"""
        try:
            user = await db_session.get(DBUser, user_id)
            if not user:
                return False
            
            user.mfa_enabled = False
            user.mfa_secret = None
            user.mfa_backup_codes = None
            
            await db_session.flush()
            
            # Log action
            if admin_id:
                audit = AuditLog(
                    action_type="MFA_DISABLED",
                    admin_id=admin_id,
                    user_id=user_id,
                    resource_type="User",
                    resource_id=str(user_id),
                    details=f"MFA disabled by admin {admin_id}"
                )
                db_session.add(audit)
            
            await db_session.commit()
            logger.info(f"MFA disabled for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling MFA: {e}")
            return False
    
    @staticmethod
    async def verify_backup_code(
        db_session: AsyncSession,
        user_id: int,
        code: str
    ) -> bool:
        """
        Verify and use a backup code.
        Removes the code from available codes after verification.
        """
        try:
            user = await db_session.get(DBUser, user_id)
            if not user or not user.mfa_backup_codes:
                return False
            
            from auth_utils import verify_password
            
            codes_list = user.mfa_backup_codes.split(",")
            for stored_hash in codes_list:
                if verify_password(code, stored_hash):
                    # Remove used code
                    codes_list.remove(stored_hash)
                    user.mfa_backup_codes = ",".join(codes_list) if codes_list else None
                    await db_session.commit()
                    logger.info(f"Backup code used for user {user_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verifying backup code: {e}")
            return False
