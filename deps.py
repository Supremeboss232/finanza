# deps.py
# Dependency injections for routes, authentication, and admin validation.

import logging
from typing import Annotated, AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status, Form, Cookie
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import constr

import auth_utils
import crud
from database import SessionLocal
from models import User, TokenBlacklist
from config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


# -----------------------
#  DATABASE DEPENDENCY
# -----------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_db)]


# ------------------------------------------------
#  TOKEN BLACKLIST CHECK
# ------------------------------------------------
async def is_token_blacklisted(token: str, db: AsyncSession) -> bool:
    """
    Check if a token has been blacklisted (user logged out).
    Returns True if token is blacklisted, False otherwise.
    """
    from sqlalchemy import select
    try:
        result = await db.execute(
            select(TokenBlacklist).where(TokenBlacklist.token == token).limit(1)
        )
        return result.scalars().first() is not None
    except Exception:
        return False


# ------------------------------------------------
#  FIXED TOKEN HANDLING (COOKIE + BEARER SUPPORT)
# ------------------------------------------------
async def get_current_user(
    db: SessionDep,
    cookie_token: Annotated[Optional[str], Cookie(alias="access_token")] = None,
    bearer_token: Annotated[Optional[str], Depends(oauth2_scheme)] = None,
):
    """
    Accepts authentication from:
    - Cookie: access_token
    - Authorization Header: Bearer <token>
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Token priority: Bearer > Cookie
    token = bearer_token or cookie_token

    if token is None:
        logging.warning("Authentication failed: No token provided.")
        raise credentials_exception

    logging.debug(f"Decoding token: {token}")

    email = auth_utils.decode_access_token(token)

    if email is None:
        logging.warning("Authentication failed: Invalid or expired token.")
        raise credentials_exception

    # Check if token has been blacklisted (user logged out)
    if await is_token_blacklisted(token, db):
        logging.warning("Authentication failed: Token has been blacklisted (user logged out).")
        raise credentials_exception

    logging.info(f"Token decoded successfully for email: {email}")

    # Eagerly load relationships to prevent separate queries later
    user = await crud.get_user_by_email(
        db, 
        email=email, 
        options=[selectinload(User.accounts), selectinload(User.investments), selectinload(User.loans)]
    )
    if user is None:
        logging.warning(f"Authentication failed: User {email} not found.")
        raise credentials_exception

    # Refresh user data to ensure is_admin status is current
    # This allows admin panel changes to take effect immediately
    await db.refresh(user)

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


# -----------------------
#  ACTIVE USER CHECK
# -----------------------
async def get_current_active_user(current_user: CurrentUserDep) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

ActiveUserDep = Annotated[User, Depends(get_current_active_user)]


# -----------------------
#  ADMIN CHECK
# -----------------------
async def get_current_admin_user(current_user: ActiveUserDep) -> User:
    # Admin access: either is_admin=True OR email matches configured admin email
    is_admin = current_user.email == settings.ADMIN_EMAIL or current_user.is_admin
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not an admin user"
        )
    return current_user

CurrentAdminUserDep = Annotated[User, Depends(get_current_admin_user)]


# -----------------------
#  PASSWORD VALIDATION
# -----------------------
def validate_password_length(password: Annotated[constr(min_length=8), Form()]) -> str:
    """
    Validates that the password meets minimum requirements.
    """
    return password
