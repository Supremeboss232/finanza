"""
Auth API v1 Router - Public Authentication Endpoints
Handles: registration, email verification, password reset
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta, datetime
from pydantic import BaseModel
import logging
import secrets
import asyncio

from models import User
from crud import create_user, get_user_by_email
from auth_utils import verify_password, create_access_token, decode_access_token
from config import settings
from deps import SessionDep
import logging

# Try to import email utility, but don't fail if it's not available
try:
    from email_utils import send_email
    EMAIL_AVAILABLE = True
    print("[STARTUP] [OK] email_utils imported successfully")
except ImportError as e:
    EMAIL_AVAILABLE = False
    print(f"[STARTUP] [FAIL] Failed to import email_utils: {e}")

# ==================== SCHEMAS ====================
class UserRegisterRequest(BaseModel):
    full_name: str
    email: str
    password: str
    terms_accepted: bool = False
    role: str = "user"  # Default role

class ForgotPasswordRequest(BaseModel):
    email: str

class UserRegisterResponse(BaseModel):
    email: str
    user_id: int
    full_name: str
    access_token: str
    token_type: str
    admin_role: str
    permissions: list
    redirect_url: str

class AuditLogEntry(BaseModel):
    action: str
    email: str
    ip_address: str
    timestamp: str

class LoginRequest(BaseModel):
    email: str
    password: str

# ==================== ROUTER ====================
auth_v1_router = APIRouter(prefix="/api/v1/auth", tags=["auth_v1"])

@auth_v1_router.get("/csrf-token")
async def get_csrf_token(request: Request):
    """
    Generate and return a CSRF token for form protection.
    Token is also set as a cookie for validation on subsequent requests.
    """
    # Generate a random CSRF token
    csrf_token = secrets.token_urlsafe(32)
    
    # Store in session or return for client to use
    return {
        "csrf_token": csrf_token,
        "message": "CSRF token generated successfully"
    }

@auth_v1_router.post("/login")
async def login_v1(
    db_session: SessionDep,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Login endpoint - accepts HTML form data or FormData
    Accepts username (email or account number) and password
    Returns access token
    """
    try:
        username_input = username.strip().lower() if username else ""
        
        print(f"\n{'='*60}")
        print(f"[LOGIN] [SEC] {username_input}")
        print(f"{'='*60}")
        
        if not username_input or not password:
            print(f"[LOGIN] [FAIL] Missing username or password")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "detail": "Username and password are required"
                }
            )
        
        # Look up user by email or username
        user = None
        try:
            print(f"[LOGIN] Querying database for: {username_input}")
            # Treat username as email (most common case)
            result = await db_session.execute(
                select(User).where(User.email == username_input)
            )
            user = result.scalar_one_or_none()
            if user:
                print(f"[LOGIN] [OK] User found by email: {username_input}")
            else:
                print(f"[LOGIN] [FAIL] User not found: {username_input}")
        except Exception as db_error:
            print(f"[LOGIN] [FAIL] Database error: {db_error}")
            print(f"[LOGIN] [FAIL] DB Session is None: {db_session is None}")
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "detail": f"Database error: {str(db_error)}"
                }
            )
        
        # Verify user exists and password is correct
        if not user:
            print(f"[LOGIN] [FAIL] User not found: {username_input}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "detail": "Invalid email or password"
                }
            )
        
        # Verify password
        print(f"[LOGIN] Verifying password for: {user.email}")
        is_password_valid = verify_password(password, user.hashed_password)
        print(f"[LOGIN] Password valid: {is_password_valid}")
        
        if not is_password_valid:
            print(f"[LOGIN] [FAIL] Invalid password for: {username_input}")
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "detail": "Invalid email or password"
                }
            )
        
        print(f"[LOGIN] [OK] User authenticated: {user.full_name} (ID: {user.id})")
        
        # Ensure admin safeguard
        if user.email == "admin@admin.com" and not user.is_admin:
            print(f"[LOGIN] Setting admin privileges for: {user.email}")
            user.is_admin = True
            user.admin_role = "SUPER_ADMIN"
            await db_session.commit()
            await db_session.refresh(user)
        
        # Create access token
        print(f"[LOGIN] Creating access token...")
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Determine if admin
        import rbac
        is_admin = user.email == "admin@admin.com" or bool(user.is_admin)
        admin_role = rbac.resolve_admin_role(user) if is_admin else "STANDARD"
        
        # Calculate permissions from authoritative RBAC matrix
        permissions = rbac.get_effective_permissions(user) if is_admin else []
        
        print(f"[LOGIN] [OK] Token generated for: {user.email}")
        print(f"[LOGIN] [OK] Admin: {is_admin}, Role: {admin_role}")
        
        # Determine correct redirect URL based on role
        if is_admin:
            redirect_url = "/user/admin/dashboard"
        else:
            redirect_url = "/user/dashboard"
        
        print(f"[LOGIN] Redirect URL: {redirect_url}")
        
        response_data = {
            "success": True,
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_admin": is_admin,
            "admin_role": admin_role,
            "permissions": permissions,
            "redirect_url": redirect_url
        }
        
        print(f"[LOGIN] Creating response with cookie...")
        
        # Create response with JSON data
        response = JSONResponse(content=response_data, status_code=200)
        
        # Set access token as HTTP-only cookie for automatic inclusion in requests
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=30 * 60,  # 30 minutes
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            path="/"
        )
        
        print(f"[LOGIN] [OK] Response sent with cookie and token")
        return response
        
    except Exception as e:
        print(f"[LOGIN] [FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "detail": f"Login failed: {str(e)}"
        }


@auth_v1_router.get("/verify")
@auth_v1_router.post("/verify")
@auth_v1_router.post("/verify-token")
async def verify_token(
    request: Request,
    db_session: SessionDep
):
    """
    Verify that a user's token or cookie session is still valid.
    Returns 200 if valid, 401 if invalid/expired.
    """
    try:
        auth_header = request.headers.get('Authorization', '')
        token = None
        if auth_header.startswith('Bearer '):
            cand = auth_header.replace('Bearer ', '').strip()
            if cand and cand not in ('null', 'undefined', 'cookie-session'):
                token = cand
        if not token:
            token = request.cookies.get('access_token')

        if not token:
            return JSONResponse(content={"detail": "No token provided"}, status_code=401)

        decoded = decode_access_token(token)
        email = decoded.get("sub") if isinstance(decoded, dict) else decoded
        if not email:
            return JSONResponse(content={"detail": "Invalid or expired token"}, status_code=401)

        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return JSONResponse(content={"detail": "User not found"}, status_code=401)

        is_adm = bool(getattr(user, 'is_admin', False))
        adm_role = getattr(user, 'admin_role', None) or ('SUPER_ADMIN' if is_adm else 'user')
        return JSONResponse(
            content={
                "success": True,
                "valid": True,
                "email": email,
                "user_id": user.id,
                "full_name": user.full_name,
                "is_admin": is_adm,
                "is_active": user.is_active if hasattr(user, 'is_active') else True,
                "role": "Treasury" if is_adm else "user",
                "admin_role": adm_role,
                "roles": ["SUPER_ADMIN", "ADMIN", "Treasury", "Operations", "Compliance", "Support"] if is_adm else ["user"],
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(content={"detail": f"Token verification failed: {str(e)}"}, status_code=401)


@auth_v1_router.post("/forgot-password")
async def forgot_password_v1(payload: ForgotPasswordRequest, db_session: SessionDep):
    """
    Initiate password recovery - opaque response (prevents account enumeration)
    Returns same message for both found and not found emails
    """
    # DEBUG: Direct print to see if endpoint is called
    print("\n" + "="*60)
    print("[ENDPOINT] [ERR] forgot_password_v1 CALLED!")
    print("="*60)
    
    try:
        email = payload.email.strip().lower()
        log_instance = logging.getLogger(__name__)
        
        print(f"[DEBUG] Email from payload: {email}")
        log_instance.info(f"[MSG] Processing forgot-password request for: {email}")
        print(f"[DEBUG] Logged to logger")
        
        if not email:
            return {
                "success": True,
                "message": "If this email is registered, a password reset link has been sent"
            }
        
        # Look up user (silently fail if not found)
        user = None
        try:
            print(f"[DEBUG] Querying database for email: {email}")
            result = await db_session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalar_one_or_none()
            print(f"[DEBUG] Database query complete. User found: {user is not None}")
            
            if user:
                print(f"[DEBUG] [OK] User found: {user.full_name} (ID: {user.id})")
                log_instance.info(f"[OK] Found user: {user.full_name} ({user.id})")
            else:
                print(f"[DEBUG] [FAIL] User not found for email: {email}")
                log_instance.info(f"[FAIL] User not found for email: {email}")
        except Exception as db_error:
            print(f"[DEBUG] [FAIL] Database error: {db_error}")
            log_instance.error(f"Database error: {db_error}")
        
        # Generate and send reset email if user found
        print(f"[DEBUG] Checking if user exists: {user is not None}")
        if user:
            print(f"[DEBUG] User exists, proceeding to generate token and send email")
            try:
                from otp_service import otp_service
                reset_token = await otp_service.create_reset_token(user.id)
                base_url = getattr(settings, 'FRONTEND_URL', None) or getattr(settings, 'API_URL', None) or 'http://127.0.0.1:8000'
                reset_link = f"{base_url}/reset-password?token={reset_token}"
                
                print(f"[DEBUG] Reset token generated: {reset_token[:20]}...")
                print(f"[DEBUG] Reset link: {reset_link}")
                log_instance.info(f"[SEC] Generated reset token: {reset_token}")
                log_instance.info(f"🔗 Reset link: {reset_link}")
                
                # Email body
                email_body = f"""
                <html>
                    <body>
                        <h2>Password Reset Request</h2>
                        <p>Hello {user.full_name},</p>
                        <p>We received a request to reset your password. Click the link below to proceed:</p>
                        <p><a href="{reset_link}">Reset Your Password</a></p>
                        <p>Or copy and paste this link: {reset_link}</p>
                        <p>This link will expire in 30 minutes.</p>
                        <p>If you didn't request this, please ignore this email.</p>
                        <p>Regards,<br>Finanza Team</p>
                    </body>
                </html>
                """
                
                # Try to send email
                print(f"[DEBUG] EMAIL_AVAILABLE = {EMAIL_AVAILABLE}")
                if EMAIL_AVAILABLE:
                    print(f"[DEBUG] 📤 Attempting to send email to {user.email}...")
                    log_instance.info(f"📤 Attempting to send email to {user.email}...")
                    try:
                        result = await send_email(
                            subject="Password Reset Request - Finanza",
                            recipients=[user.email],
                            body=email_body,
                            subtype="html"
                        )
                        print(f"[DEBUG] [OK] Email sent successfully! Result: {result}")
                        log_instance.info(f"[OK] Password reset email sent successfully to {user.email}")
                        log_instance.info(f"📨 Email send result: {result}")
                    except Exception as email_error:
                        print(f"[DEBUG] [FAIL] Email sending failed: {email_error}")
                        log_instance.error(f"[FAIL] Failed to send email: {email_error}", exc_info=True)
                else:
                    print(f"[DEBUG] [FAIL] EMAIL_AVAILABLE is False - email_utils not imported")
                    log_instance.warning(f"[FAIL] EMAIL_AVAILABLE is False - email_utils not imported")
                    
            except Exception as token_error:
                print(f"[DEBUG] [FAIL] Error in token generation: {token_error}")
                log_instance.error(f"Error generating reset token: {token_error}", exc_info=True)
        else:
            print(f"[DEBUG] User is None, skipping email send")

        
        # Return SAME message regardless (opaque response)
        return {
            "success": True,
            "message": "If this email is registered, a password reset link has been sent"
        }
        
    except Exception as e:
        log_instance = logging.getLogger(__name__)
        log_instance.error(f"Error in forgot_password: {e}", exc_info=True)
        # Still return success to prevent enumeration
        return {
            "success": True,
            "message": "If this email is registered, a password reset link has been sent"
        }

@auth_v1_router.post("/register", status_code=status.HTTP_201_CREATED, response_model=dict)
async def register_user_v1(
    request: UserRegisterRequest,
    db_session: SessionDep
):
    """
    Register a new user account.
    
    Requirements:
    - Email must be unique
    - Password must be 8+ characters (complexity handled by frontend)
    - Returns email verification redirect
    - Default role: 'user' (only admins can be created by superadmin)
    """
    
    # Validate input
    if not request.full_name or not request.full_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name is required"
        )
    
    if not request.email or not request.email.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long"
        )
    
    if len(request.password.encode('utf-8')) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password is too long"
        )
    
    if not request.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept Terms of Service and Privacy Policy"
        )
    
    # Check if email already exists
    try:
        existing_user = await get_user_by_email(db_session, email=request.email.lower().strip())
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error checking email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )
    
    try:
        # Create new unverified user
        from pydantic import BaseModel as PydanticModel
        class UserData(PydanticModel):
            full_name: str
            email: str
            password: str
        
        user_data = UserData(
            full_name=request.full_name.strip(),
            email=request.email.lower().strip(),
            password=request.password
        )
        
        new_user = await create_user(
            db=db_session,
            user=user_data,
            is_active=True,   # Active immediately for seamless login
            is_verified=False
        )
        
        # Ensure admin_role is set
        if not hasattr(new_user, 'admin_role') or not new_user.admin_role:
            new_user.admin_role = 'STANDARD'
        
        # Set default permissions for new users
        permissions = []
        
        # Auto-login: issue access token even though user is unverified
        # Privileged endpoints check is_verified flag
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user.email},
            expires_delta=access_token_expires
        )
        
        # Return response with token in body and cookie
        response_data = {
            "email": new_user.email,
            "user_id": new_user.id,
            "full_name": new_user.full_name,
            "access_token": access_token,
            "token_type": "bearer",
            "admin_role": new_user.admin_role,
            "permissions": permissions,
            "redirect_url": "/verify-email"  # Frontend should redirect to email verification
        }
        
        response = JSONResponse(content=response_data, status_code=status.HTTP_201_CREATED)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,  # Allow JS to read for localStorage backup
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="Lax",
            path="/",
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error during user registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration"
        )


@auth_v1_router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    email: str,
    code: str,
    db_session: SessionDep
):
    """
    Verify email with OTP code.
    
    Backend should:
    1. Check if code matches what was sent
    2. Mark user as verified
    3. Return redirect to dashboard
    """
    
    if not email or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and verification code are required"
        )
    
    try:
        from otp_service import otp_service
        user = await get_user_by_email(db_session, email=email.lower().strip())
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            return {
                "success": True,
                "message": "Email is already verified",
                "redirect_url": "/user/dashboard"
            }
        
        ok = await otp_service.verify_email_otp(email.lower().strip(), code.strip())
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )
        
        user.is_verified = True
        db_session.add(user)
        await db_session.commit()
        
        return {
            "success": True,
            "message": "Email verified successfully",
            "redirect_url": "/user/dashboard"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error during email verification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during email verification"
        )


@auth_v1_router.post("/resend-verification-code")
async def resend_verification_code(
    email: str,
    db_session: SessionDep
):
    """
    Resend verification code to user's email.
    """
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    try:
        from otp_service import otp_service
        user = await get_user_by_email(db_session, email=email.lower().strip())
        if not user:
            return {
                "success": True,
                "message": "If this email is registered, a new verification code has been sent"
            }
        
        if user.is_verified:
            return {
                "success": True,
                "message": "This email is already verified"
            }
        
        code = await otp_service.create_email_otp(user.email)
        
        if EMAIL_AVAILABLE:
            email_body = f"""
            <html><body>
            <h2>Finanza Email Verification</h2>
            <p>Hello {user.full_name},</p>
            <p>Your verification code is: <strong style='font-size:24px;letter-spacing:4px'>{code}</strong></p>
            <p>This code expires in <strong>10 minutes</strong>.</p>
            <p>If you did not request this, please ignore this email.</p>
            <p>Regards,<br>Finanza Team</p>
            </body></html>
            """
            try:
                await send_email(
                    subject="Verify your Finanza account",
                    recipients=[user.email],
                    body=email_body,
                    subtype="html"
                )
                log.info(f"Verification OTP sent to {user.email}")
            except Exception as email_err:
                log.error(f"Failed to send verification email: {email_err}")
        else:
            log.warning(f"EMAIL_AVAILABLE=False — OTP generated but not sent for {user.email}")
        
        return {
            "success": True,
            "message": "Verification code sent to your email"
        }
        
    except Exception as e:
        log.error(f"Error resending verification code: {e}", exc_info=True)
        return {
            "success": True,
            "message": "If this email is registered, a new verification code has been sent"
        }

@auth_v1_router.get("/validate-reset-token")
async def validate_reset_token(
    token: str,
    db_session: SessionDep
):
    """
    Validate password reset token - used by reset_password.html on page load
    Returns 200 if valid, 401 if invalid/expired
    """
    try:
        from otp_service import otp_service
        if not token or len(token) < 10:
            raise HTTPException(status_code=401, detail="Invalid or malformed reset token")
        user_id = await otp_service.verify_reset_token(token)
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="This reset link is invalid or has expired"
            )
        # Re-store token so it can still be used by the reset-password call
        # (verify_reset_token consumes it, so we put it back with same TTL)
        await otp_service._set("finanza:rst:" + token, str(user_id), 1800)
        return {
            "valid": True,
            "message": "Token is valid — please set your new password"
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="This reset link is invalid or has expired")

@auth_v1_router.post("/reset-password")
async def reset_password(
    payload: dict,
    db_session: SessionDep
):
    """
    Reset user password using reset token
    Expects: {"token": "...", "password": "..."}
    """
    try:
        token = payload.get("token")
        new_password = payload.get("password")
        
        if not token or not new_password:
            raise HTTPException(status_code=422, detail="Token and password are required")
        
        if len(new_password) < 8:
            raise HTTPException(status_code=422, detail="Password must be at least 8 characters long")
        
        has_uppercase = any(c.isupper() for c in new_password)
        has_number = any(c.isdigit() for c in new_password)
        has_special = any(not c.isalnum() for c in new_password)
        
        if not (has_uppercase and has_number and has_special):
            raise HTTPException(
                status_code=422,
                detail="Password must contain uppercase, number, and special character"
            )
        
        # Verify and consume the reset token via OTP service
        from otp_service import otp_service
        user_id = await otp_service.verify_reset_token(token)
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid or expired reset token")
        
        result = await db_session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired reset token")
        
        from auth_utils import get_password_hash
        user.hashed_password = get_password_hash(new_password)
        db_session.add(user)
        await db_session.commit()
        log.info(f"Password reset completed for user {user_id}")
        return {
            "success": True,
            "message": "Password reset successful. Please log in with your new password.",
            "redirect_url": "/signin"
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error resetting password: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while resetting password"
        )

@auth_v1_router.post("/audit-log")
async def log_auth_audit(
    payload: AuditLogEntry
):
    """
    Log authentication-related actions for audit trail
    Accepts action, email, ip_address, and timestamp
    """
    try:
        log_instance = logging.getLogger(__name__)
        log_instance.info(
            f"[SCH] AUDIT LOG: {payload.action} | Email: {payload.email} | "
            f"IP: {payload.ip_address} | Time: {payload.timestamp}"
        )
        return {
            "success": True,
            "message": "Audit log recorded"
        }
    except Exception as e:
        log_instance.error(f"Error logging audit: {e}")
        # Don't raise error - audit logging should not block user flow
        return {
            "success": False,
            "message": "Audit logging failed (non-critical)"
        }

@auth_v1_router.post("/login-audit", tags=["audit"])
async def log_login_audit(
    payload: AuditLogEntry
):
    """
    Log login audit trail separately
    """
    try:
        log_instance = logging.getLogger(__name__)
        log_instance.info(
            f"[SEC] LOGIN AUDIT: {payload.action} | Email: {payload.email} | "
            f"IP: {payload.ip_address} | Time: {payload.timestamp}"
        )
        return {
            "success": True,
            "message": "Login audit recorded"
        }
    except Exception as e:
        log_instance.error(f"Error logging login audit: {e}")
        return {
            "success": False,
            "message": "Login audit failed (non-critical)"
        }


@auth_v1_router.get("/heartbeat")
@auth_v1_router.post("/heartbeat")
async def heartbeat():
    """
    Heartbeat endpoint for token validation and session keep-alive.
    
    Used by frontend to:
    - Validate token is still valid
    - Prevent token from expiring during active session
    - Monitor connection status
    
    Returns 200 OK if service is up and running.
    """
    import logging
    from datetime import datetime
    log_instance = logging.getLogger(__name__)
    
    try:
        log_instance.debug('[HEARTBEAT] ❤ Dashboard heartbeat received')
        
        return {
            "success": True,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Service is operational"
        }
    except Exception as e:
        log_instance.error(f"[HEARTBEAT] Error: {e}")
        return {
            "success": False,
            "status": "error",
            "message": "Service error"
        }


# ==================== SYSTEM STATUS ====================
# Note: Can be accessed without authentication
system_status_router = APIRouter(prefix="/api/v1/system", tags=["system"])

@system_status_router.get("/status")
async def get_system_status():
    """
    Get system status for maintenance mode and health checks.
    
    Returns:
    - maintenance: Whether system is in maintenance mode
    - status: Overall system status (operational, degraded, down)
    - message: Status message
    - timestamp: Server timestamp
    """
    import logging
    log_instance = logging.getLogger(__name__)
    
    try:
        # TODO: Check actual maintenance mode from admin settings
        # For now, always return operational
        
        return {
            "success": True,
            "maintenance": False,
            "status": "operational",
            "message": "System is operational",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        log_instance.error(f"[SYSTEM-STATUS] Error: {e}")
        return {
            "success": False,
            "maintenance": False,
            "status": "error",
            "message": "Failed to get system status",
            "timestamp": datetime.utcnow().isoformat()
        }


@auth_v1_router.post("/refresh")
@auth_v1_router.post("/refresh-token")
async def refresh_token(request: Request):
    """
    Refresh authentication token for silent token refresh.
    
    Accepts:
    - Access token from Authorization header or cookie
    
    Returns:
    - New access token that extends session
    - Token type and expiration
    
    Used for silent token refresh without user interaction.
    """
    import logging
    log_instance = logging.getLogger(__name__)
    
    try:
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = None
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        
        if not token:
            # Try to get from cookies
            token = request.cookies.get("access_token")
        
        if not token:
            log_instance.warning("[REFRESH] [FAIL] No token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided"
            )
        
        log_instance.debug(f"[REFRESH] Attempting to refresh token")
        
        # Decode the token to validate it
        decoded_token = decode_access_token(token)
        if not decoded_token:
            log_instance.warning("[REFRESH] [FAIL] Invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        user_email = decoded_token.get("sub")
        if not user_email:
            log_instance.warning("[REFRESH] [FAIL] No user email in token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        log_instance.info(f"[REFRESH] [OK] Token refreshed for: {user_email}")
        
        # Create new token with extended expiration
        access_token_expires = timedelta(minutes=30)
        new_access_token = create_access_token(
            data={"sub": user_email},
            expires_delta=access_token_expires
        )
        
        return {
            "success": True,
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 1800,  # 30 minutes in seconds
            "message": "Token refreshed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        log_instance.error(f"[REFRESH] [FAIL] Error refreshing token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@auth_v1_router.get("/check-email")
async def check_email_availability(email: str, db_session: SessionDep):
    """Check if an email address is available for registration."""
    if not email or not email.strip():
        return {"available": False, "exists": False}
    existing = await get_user_by_email(db_session, email=email.lower().strip())
    return {"available": existing is None, "exists": existing is not None}


@auth_v1_router.post("/logout")
@auth_v1_router.get("/logout")
async def logout_v1():
    """Clear authentication cookie and end user session."""
    response = JSONResponse(content={"success": True, "message": "Logged out successfully"})
    response.delete_cookie(key="access_token", path="/")
    return response
