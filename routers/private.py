from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import selectinload
from pathlib import Path
from datetime import datetime, timezone

from models import User, TokenBlacklist
from deps import get_current_user, get_current_admin_user
from database import SessionLocal
import auth_utils

# --- Path Setup ---
BASE_PATH = Path(__file__).resolve().parent.parent

private_router = APIRouter(
    tags=["Private UI"],
    # Dependencies that apply to all routes in this router
    dependencies=[Depends(get_current_user)]
)

# --- Template Configuration ---
user_templates = Jinja2Templates(directory=str(BASE_PATH / "private/user"))


# --- Authenticated User-Facing UI Routes ---

@private_router.get("/dashboard")
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's main dashboard with data from the database."""
    # Prevent admin users from accessing the user dashboard
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins must use the admin dashboard"
        )
    
    # In a real app, you'd fetch more complex user-specific data from other tables.
    # The relationships (accounts, investments, loans) are now eagerly loaded via the dependency.
    
    total_balance = sum(account.balance for account in current_user.accounts)
    total_investments = sum(investment.amount for investment in current_user.investments)
    total_loans = sum(loan.amount for loan in current_user.loans)

    user_data = {
        "username": current_user.full_name or current_user.email,
        "balance": total_balance,
        "investments_value": total_investments,
        "outstanding_loans": total_loans
    }
    # Include verification and account info so templates can show KYC state
    user_data["is_verified"] = getattr(current_user, "is_verified", False)
    user_data["account_number"] = getattr(current_user, "account_number", None)
    return user_templates.TemplateResponse("dashboard.html", {"request": request, "user": user_data})

@private_router.get("/cards")
async def cards_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's cards page."""
    return user_templates.TemplateResponse("cards.html", {"request": request, "user": current_user})

@private_router.get("/investments")
async def investments_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's investments page."""
    return user_templates.TemplateResponse("investments.html", {"request": request, "user": current_user})

@private_router.get("/loans")
async def loans_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's loans page."""
    return user_templates.TemplateResponse("loans.html", {"request": request, "user": current_user})

@private_router.get("/insurance")
async def insurance_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's insurance page."""
    return user_templates.TemplateResponse("insurance.html", {"request": request, "user": current_user})

@private_router.get("/deposits")
async def deposits_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's deposits page."""
    return user_templates.TemplateResponse("deposits.html", {"request": request, "user": current_user})


@private_router.get("/kyc/verify")
async def kyc_verify_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the KYC submission form for the current user."""
    return user_templates.TemplateResponse("kyc_form.html", {"request": request, "user": current_user})

@private_router.get("/kyc_form")
async def kyc_form_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the KYC submission form (alternate route from /user/kyc_form)."""
    return user_templates.TemplateResponse("kyc_form.html", {"request": request, "user": current_user})

@private_router.get("/kyc_pending")
async def kyc_pending_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the KYC pending status page."""
    return user_templates.TemplateResponse("kyc_pending.html", {"request": request, "user": current_user})

@private_router.get("/kyc_rejected")
async def kyc_rejected_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the KYC rejection page."""
    return user_templates.TemplateResponse("kyc_rejected.html", {"request": request, "user": current_user})

@private_router.get("/kyc_success")
async def kyc_success_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the KYC success/approved page."""
    return user_templates.TemplateResponse("kyc_success.html", {"request": request, "user": current_user})

@private_router.get("/profile")
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's profile page."""
    return user_templates.TemplateResponse("profile.html", {"request": request, "user": current_user})

@private_router.get("/account")
async def account_settings_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's account settings page."""
    return user_templates.TemplateResponse("account.html", {"request": request, "user": current_user})

@private_router.get("/admin/dashboard", tags=["Admin UI"])
async def admin_dashboard(request: Request, current_user: User = Depends(get_current_admin_user)):
    """Serves the admin dashboard HTML file."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    # Serve the standalone HTML file
    admin_file = BASE_PATH / "private/admin/admin_dashboard_hub.html"
    if not admin_file.exists():
        raise HTTPException(status_code=404, detail=f"Admin dashboard not found at {admin_file}")
    return FileResponse(admin_file, media_type="text/html")

@private_router.get("/admin/admin_users.html", tags=["Admin UI"])
async def admin_users_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_users.html", media_type="text/html")

@private_router.get("/admin/profile", tags=["Admin UI"])
async def admin_profile_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_profile.html", media_type="text/html")

@private_router.get("/admin/settings", tags=["Admin UI"])
async def admin_settings_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_settings.html", media_type="text/html")

@private_router.get("/admin/reports", tags=["Admin UI"])
async def admin_reports_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_reports.html", media_type="text/html")

@private_router.get("/admin/submissions", tags=["Admin UI"])
async def admin_submissions_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_kyc.html", media_type="text/html")

@private_router.get("/admin/kyc", tags=["Admin UI"])
async def admin_kyc_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_kyc.html", media_type="text/html")

@private_router.get("/admin/users", tags=["Admin UI"])
async def admin_users_page_route(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_users.html", media_type="text/html")

@private_router.get("/admin/transactions", tags=["Admin UI"])
async def admin_transactions_page_route(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_transactions.html", media_type="text/html")

@private_router.get("/admin/fund", tags=["Admin UI"])
async def admin_fund_page_route(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_fund.html", media_type="text/html")

@private_router.get("/admin/reports", tags=["Admin UI"])
async def admin_reports_page_route(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_reports.html", media_type="text/html")

@private_router.get("/admin/settings", tags=["Admin UI"])
async def admin_settings_page_route(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_settings.html", media_type="text/html")

@private_router.get("/admin/{page}", tags=["Admin UI"])
async def admin_generic_page(page: str, request: Request, current_user: User = Depends(get_current_admin_user)):
    """Serve admin HTML files directly.

    Maps requests like `/admin/transactions` -> `private/admin/admin_transactions.html`.
    If the file doesn't exist, return a 404.
    
    Note: /admin/dashboard is handled by the dedicated route above.
    """
    # Skip dashboard - it's handled by the dedicated route
    if page == "dashboard":
        raise HTTPException(status_code=404, detail="Admin page 'dashboard' not found")
    
    # Normalize requested page to a filename
    filename = page if page.endswith('.html') else f"admin_{page}.html"
    file_path = BASE_PATH / "private/admin" / filename
    
    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Admin page '{page}' not found")
    
    # Serve the HTML file
    return FileResponse(file_path, media_type="text/html")

# --- Phase 4 User Pages ---

@private_router.get("/fraud_detection")
async def fraud_detection_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's fraud detection page."""
    return user_templates.TemplateResponse("fraud_detection.html", {"request": request, "user": current_user})

@private_router.get("/blockchain")
async def blockchain_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's blockchain/crypto wallet page."""
    return user_templates.TemplateResponse("blockchain.html", {"request": request, "user": current_user})

@private_router.get("/analytics")
async def analytics_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's analytics and reporting page."""
    return user_templates.TemplateResponse("analytics.html", {"request": request, "user": current_user})

@private_router.get("/treasury_portfolio")
async def treasury_portfolio_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's treasury/investment portfolio page."""
    return user_templates.TemplateResponse("treasury_portfolio.html", {"request": request, "user": current_user})

@private_router.get("/settlement_status")
async def settlement_status_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's settlement status tracking page."""
    return user_templates.TemplateResponse("settlement_status.html", {"request": request, "user": current_user})

# --- Phase 3 User Pages ---

@private_router.get("/bill_pay")
async def bill_pay_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's bill pay page."""
    return user_templates.TemplateResponse("bill_pay.html", {"request": request, "user": current_user})

@private_router.get("/currency_exchange")
async def currency_exchange_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's currency exchange page."""
    return user_templates.TemplateResponse("currency_exchange.html", {"request": request, "user": current_user})

@private_router.get("/international_transfers")
async def international_transfers_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's international transfers page."""
    return user_templates.TemplateResponse("international_transfers.html", {"request": request, "user": current_user})

# --- Phase 4 Admin Pages ---

@private_router.get("/admin/fraud_detection", tags=["Admin UI"])
async def admin_fraud_detection_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_fraud_detection.html", media_type="text/html")

@private_router.get("/admin/blockchain", tags=["Admin UI"])
async def admin_blockchain_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_blockchain.html", media_type="text/html")

@private_router.get("/admin/reporting", tags=["Admin UI"])
async def admin_reporting_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_reporting.html", media_type="text/html")

@private_router.get("/admin/treasury", tags=["Admin UI"])
async def admin_treasury_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_treasury.html", media_type="text/html")

@private_router.get("/admin/settlement", tags=["Admin UI"])
async def admin_settlement_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_settlement.html", media_type="text/html")

# --- Phase 3 Admin Pages ---

@private_router.get("/admin/bill_pay", tags=["Admin UI"])
async def admin_bill_pay_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_bill_pay.html", media_type="text/html")

@private_router.get("/admin/currency_exchange", tags=["Admin UI"])
async def admin_currency_exchange_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_currency_exchange.html", media_type="text/html")

@private_router.get("/admin/monitoring", tags=["Admin UI"])
async def admin_monitoring_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_monitoring.html", media_type="text/html")

# --- Priority 3 User Pages ---

@private_router.get("/scheduled_transfers")
async def scheduled_transfers_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's scheduled transfers page."""
    return user_templates.TemplateResponse("scheduled_transfers.html", {"request": request, "user": current_user})

@private_router.get("/webhooks_config")
async def webhooks_config_page(request: Request, current_user: User = Depends(get_current_user)):
    """Renders the user's webhook configuration page."""
    return user_templates.TemplateResponse("webhooks_config.html", {"request": request, "user": current_user})

# --- Priority 3 Admin Pages ---

@private_router.get("/admin/webhooks", tags=["Admin UI"])
async def admin_webhooks_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_webhooks.html", media_type="text/html")

@private_router.get("/admin/mobile_deposit", tags=["Admin UI"])
async def admin_mobile_deposit_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_mobile_deposit.html", media_type="text/html")

@private_router.get("/admin/international_compliance", tags=["Admin UI"])
async def admin_international_compliance_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_international_compliance.html", media_type="text/html")

@private_router.get("/logout")
async def logout(request: Request):
    """
    Logs out the user by:
    1. Extracting the JWT token from cookie or Authorization header
    2. Adding it to the TokenBlacklist table to prevent future use (replay attack prevention)
    3. Deleting the access_token cookie
    4. Redirecting to the sign-in page
    """
    import logging
    
    # Extract token from cookie or Authorization header
    token = request.cookies.get("access_token")  # Try cookie first
    
    if not token:
        # Try Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
    
    # If we have a token, add it to the blacklist
    db = None
    if token:
        try:
            # Decode token to get expiration time and user email
            payload = auth_utils.decode_access_token_full(token)
            if payload:
                user_email = payload.get("sub")
                exp_timestamp = payload.get("exp")
                
                if user_email and exp_timestamp:
                    # Convert Unix timestamp to datetime
                    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                    
                    # Get database session and add token to blacklist
                    db = SessionLocal()
                    try:
                        # Get user by email to get their ID
                        from crud import get_user_by_email
                        user = await get_user_by_email(db, email=user_email)
                        
                        if user:
                            # Create blacklist entry
                            blacklist_entry = TokenBlacklist(
                                token=token,
                                user_id=user.id,
                                expires_at=expires_at
                            )
                            db.add(blacklist_entry)
                            await db.commit()
                    finally:
                        await db.close() if db else None
        except Exception as e:
            # Log error but don't fail logout if blacklist fails
            logging.error(f"Error adding token to blacklist during logout: {e}")
    
    # Delete the access_token cookie and redirect to signin
    response = RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/")
    return response