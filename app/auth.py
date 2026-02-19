from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from typing import Annotated

from . import auth_utils
from .config import settings
from .crud import get_user_by_username, create_user, create_form_submission
from .schemas import FormSubmissionCreate
from .deps import SessionDep
from .schemas import Token, UserCreate, User

auth_router = APIRouter(tags=["auth"])


@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db_session: SessionDep
):
    user = await get_user_by_username(db_session, username=form_data.username)
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
        await db_session.commit()
        # Refresh the user object from the database to ensure is_admin is properly set
        await db_session.refresh(user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    # Determine redirect URL - admin email always goes to admin dashboard
    is_admin = user.email == settings.ADMIN_EMAIL or user.is_admin
    redirect_url = "/user/admin/dashboard" if is_admin else "/user/dashboard"
    
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "is_admin": is_admin,
        "redirect_url": redirect_url,
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name
    }
    
    # Create response with cookie
    response = JSONResponse(content=response_data)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return response


@auth_router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db_session: SessionDep):
    db_user = await get_user_by_username(db_session, username=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    # Log the registration attempt
    try:
        form_log = FormSubmissionCreate(form_type="registration", data=f"email={user.email}, full_name={user.full_name}")
        await create_form_submission(db_session, submission=form_log, user_id=None)
    except Exception:
        # Logging must not prevent registration — continue
        pass

    # Create user as inactive/unverified — user completes KYC next
    return await create_user(db_session, user=user, is_active=False, is_verified=False)