# deps.py
# Dependency injections for routes, e.g., JWT verification, role checks, and authentication requirements.

from typing import Annotated, AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status, Form, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import constr
from . import auth_utils
from .database import SessionLocal
from . import crud
from .models import User

# Keep oauth2_scheme for compatibility with API clients that send Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/signin")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: SessionDep):
    """Resolve the current user from either an Authorization Bearer header
    or an `access_token` cookie. This allows browser HTML routes (which set
    httponly cookies) to work while preserving API behavior for header-based
    clients.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token: Optional[str] = None

    # Try Authorization header first (API clients)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
    else:
        # Fall back to cookie set by the login endpoint for browser flows
        token = request.cookies.get("access_token")

    if not token:
        raise credentials_exception

    decoded = auth_utils.decode_access_token(token)
    if decoded is None:
        raise credentials_exception

    # `app.auth_utils.decode_access_token` returns a `TokenData` Pydantic model
    # while the top-level `auth_utils` returns a string email. Handle both.
    if isinstance(decoded, str):
        email = decoded
    else:
        # Pydantic model or other object with `username` attribute
        email = getattr(decoded, "username", None)

    if not email:
        raise credentials_exception

    user = await crud.get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

CurrentUserDep = Annotated[User, Depends(get_current_user)]

async def get_current_active_user(current_user: CurrentUserDep) -> User:
    # You might add checks here for user activity status
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

ActiveUserDep = Annotated[User, Depends(get_current_active_user)]

async def get_current_admin_user(current_user: ActiveUserDep) -> User:
    # Assuming 'is_admin' attribute in User model or a role-based access control (RBAC) system
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an admin user")
    return current_user

CurrentAdminUserDep = Annotated[User, Depends(get_current_admin_user)]
