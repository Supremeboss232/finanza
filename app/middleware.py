"""Middleware for enforcing user route access control."""

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class UserAccessControlMiddleware(BaseHTTPMiddleware):
    """
    Enforce access control rules:
    - Authenticated users trying to access routes NOT starting with /user (except /logout, /api)
      are redirected to /user/dashboard
    - Protects against escape routes
    """
    
    # Whitelisted routes that don't start with /user
    WHITELIST = {
        "/",
        "/login",
        "/signup",
        "/forgot-password",
        "/reset-password",
        "/logout",
        "/health",
    }
    
    # Patterns to allow (API, static, etc.)
    ALLOWED_PREFIXES = {
        "/api",
        "/static",
        "/admin",
        "/public",
    }

    async def dispatch(self, request: Request, call_next):
        """Check access control on each request."""
        path = request.url.path
        
        # Skip middleware checks for allowed prefixes
        for prefix in self.ALLOWED_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        
        # Skip middleware checks for whitelisted routes
        if path in self.WHITELIST:
            return await call_next(request)
        
        # Check if user is authenticated
        user = request.session.get("user") if hasattr(request, "session") else None
        
        # If authenticated user tries to access non-/user routes, redirect to dashboard
        if user and not path.startswith("/user"):
            return RedirectResponse(url="/user/dashboard", status_code=302)
        
        # Continue with normal request processing
        response = await call_next(request)
        return response
