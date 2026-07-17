from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Annotated
import logging, crud
from database import SessionLocal

import auth_utils
from config import settings 
from crud import get_user_by_username, create_user, create_form_submission
from schemas import FormSubmissionCreate
from deps import SessionDep, validate_password_length
from schemas import Token, UserCreate, User

auth_router = APIRouter(tags=["auth"])
log = logging.getLogger(__name__)

from deps import get_current_user, CurrentUserDep

async def get_current_user_from_cookie(request: Request):
    """Read `access_token` cookie from a Request and return the user or None.

    This helper is intended for middleware use where FastAPI dependency
    injection is not available. It returns the `User` object on success
    or `None` when no valid user is found.
    """
    try:
        token = request.cookies.get("access_token")
        if not token:
            return None

        # Check if token is revoked
        is_revoked = await auth_utils.is_token_revoked(token)
        if is_revoked:
            log.warning("Attempt to use revoked token")
            return None

        email = auth_utils.decode_access_token(token)
        if not email:
            return None

        async with SessionLocal() as db:
            user = await crud.get_user_by_email(db, email=email)
            if user:
                # Ensure the configured admin email ALWAYS has admin rights
                if user.email == settings.ADMIN_EMAIL and not user.is_admin:
                    user.is_admin = True
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)
                
                # Always refresh the user's is_admin status from the database
                # to reflect any changes made by admins in the admin panel
                await db.refresh(user)
            return user
    except Exception:
        # Be conservative in middleware: don't raise, just treat as unauthenticated
        log.exception("Error resolving user from cookie")
        return None


@auth_router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: SessionDep
):
    # Support login by email or account number
    user = None
    username_input = form_data.username.strip()
    
    # Try to get user by email first (standard email format)
    if "@" in username_input:
        user = await get_user_by_username(db_session, username=username_input)
    else:
        # Try account number if no @ symbol
        user = await crud.get_user_by_account_number(db_session, account_number=username_input)
    
    # If not found by account number, try as email anyway (fallback)
    if not user:
        user = await get_user_by_username(db_session, username=username_input)
    
    if not user or not auth_utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Safeguard for Admin User ---
    # Ensure the configured admin email ALWAYS has admin rights upon login.
    if user.email == settings.ADMIN_EMAIL and not user.is_admin:
        user.is_admin = True
        user.admin_role = "SUPER_ADMIN"
        await db_session.commit()
        # Refresh the user object from the database to ensure is_admin is properly set
        await db_session.refresh(user)
    
    # --- Refresh admin status from database ---
    # Always refresh the user's is_admin status from the database to reflect any changes
    # made by admins in the admin panel (e.g., promoting/demoting users)
    await db_session.refresh(user)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Determine if admin
    is_admin = user.email == settings.ADMIN_EMAIL or user.is_admin
    
    # UNIFIED REDIRECT: Both users and admins go to /user/dashboard
    # The /user/dashboard route checks is_admin and serves appropriate content (no 302 redirect)
    redirect_url = "/user/dashboard"

    # Get admin role and calculate permissions based on role
    admin_role = getattr(user, 'admin_role', 'STANDARD') or 'STANDARD'
    
    # Role-based permissions
    permissions = []
    if admin_role == 'SUPER_ADMIN':
        permissions = [
            "view_reports", "manage_funds", "edit_settings", "audit_logs",
            "manage_users", "approve_transactions", "manage_treasury", "manage_compliance"
        ]
    elif admin_role == 'TREASURY':
        permissions = [
            "view_reports", "manage_funds", "approve_transactions", "manage_treasury"
        ]
    elif admin_role == 'ADMIN' or is_admin:
        permissions = [
            "view_reports", "manage_users", "audit_logs"
        ]
    
    # For a JavaScript frontend, it's better to return JSON.
    # The frontend can then handle the redirect.
    response = JSONResponse(content={
        "redirect_url": redirect_url,
        "is_admin": is_admin,
        "admin_role": admin_role,
        "permissions": permissions,
        "email": user.email,
        "user_id": user.id,
        "full_name": user.full_name,
        "token_type": "bearer",
        "access_token": access_token
    })
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False,  # Allow JavaScript to read and backup token to localStorage
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="Lax",
        path="/",
    )
    return response

@auth_router.get("/me")
async def get_current_user_info(current_user: CurrentUserDep):
    """Get current authenticated user info including admin status."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified
    }

@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db_session: SessionDep
):
    # Validate password
    if len(user.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long."
        )
    if len(user.password.encode('utf-8')) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password is too long."
        )
    
    # The username is the email
    try:
        db_user = await get_user_by_username(db_session, username=user.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        # Log registration attempt
        try:
            form_log = FormSubmissionCreate(form_type="registration", data=f"email={user.email}, full_name={user.full_name}")
            await create_form_submission(db_session, submission=form_log, user_id=None)
        except Exception:
            pass
        # Create inactive/unverified user
        new_user = await create_user(db=db_session, user=user, is_active=False, is_verified=False)

        # Auto-login user by issuing access token (they remain inactive for privileged endpoints)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_utils.create_access_token(data={"sub": new_user.email}, expires_delta=access_token_expires)

        response = JSONResponse(content={"redirect_url": "/dashboard"})
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="Lax",
            path="/",
        )
        return response
    except HTTPException as e:
        # Re-raise HTTPException to ensure FastAPI handles it correctly
        raise e
    except Exception as e:
        log.error("Error during user registration", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="An unexpected error occurred during registration.")