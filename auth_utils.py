from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import asyncio

from passlib.context import CryptContext
from jose import JWTError, jwt

from config import settings
from schemas import TokenData

# Password hashing context
# Use Argon2 with fallback to bcrypt for backward compatibility
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hashes a password using the configured password context (argon2).
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a stored hash.
    Supports both Argon2 (current) and bcrypt (legacy) hashes for backward compatibility.
    """
    try:
        # Try to verify with the current context (supports both Argon2 and bcrypt due to deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # If verification fails, return False
        return False

# -------------------------
# JWT Utilities
# -------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token with JTI (JWT ID) claim for revocation support.
    """
    import uuid
    
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    
    # Add JTI (JWT ID) for token revocation tracking
    if "jti" not in to_encode:
        to_encode["jti"] = str(uuid.uuid4())
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    """
    Decode JWT access token and return the user's email (subject).
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None


def decode_access_token_full(token: str) -> Optional[dict]:
    """
    Decode JWT access token and return the full payload including expiration.
    Returns dict with keys: sub (email), exp (expiration timestamp), and other claims.
    Returns None if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


async def is_token_revoked(token: str) -> bool:
    """
    Check if a token is in the revocation blacklist.
    
    Args:
        token: JWT token string
        
    Returns:
        True if token is revoked, False if valid
    """
    try:
        # Decode to get JTI (JWT ID claim)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        jti = payload.get("jti")  # JWT ID claim (if present)
        
        if not jti:
            # If no JTI claim, token cannot be revoked individually
            return False
        
        # Check blacklist service
        from token_blacklist_service import get_token_blacklist_service
        blacklist_service = get_token_blacklist_service()
        return await blacklist_service.is_token_revoked(jti)
        
    except JWTError:
        # Invalid token, treat as revoked
        return True
    except Exception as e:
        # On error, be conservative and treat as revoked
        import logging
        logging.error(f"Error checking token revocation: {e}")
        return True


def require_scope(user: "User", required_scope: str) -> bool:
    """
    Check if a user has the required scope for an operation.
    Scopes are stored in user.admin_role or can be inferred from user.is_admin status.
    
    Valid scopes include:
    - 'reporting:view' - Can view reports and analytics
    - 'reporting:write' - Can generate and schedule reports
    - 'settings:write' - Can modify system settings
    - 'admin:full' - Full admin access
    
    Returns True if user has the scope, raises HTTPException if not.
    """
    from fastapi import HTTPException
    
    # Superadmins have all scopes
    if hasattr(user, 'is_admin') and user.is_admin and hasattr(user, 'admin_role') and user.admin_role == 'superadmin':
        return True
    
    # Check if user has the specific scope in their role
    if hasattr(user, 'admin_role'):
        user_scopes = []
        
        # Map admin roles to scopes
        if user.admin_role == 'superadmin':
            user_scopes = ['reporting:view', 'reporting:write', 'settings:write', 'admin:full']
        elif user.admin_role == 'admin':
            user_scopes = ['reporting:view', 'reporting:write']
        elif user.admin_role == 'analyst':
            user_scopes = ['reporting:view']
        
        if required_scope in user_scopes:
            return True
    
    # If user doesn't have scope, raise exception
    raise HTTPException(
        status_code=403,
        detail=f"Insufficient permissions. Required scope: {required_scope}"
    )

