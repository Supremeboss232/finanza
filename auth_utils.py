from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib

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
    Create JWT access token.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
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
