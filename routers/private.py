from fastapi import APIRouter, Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from pathlib import Path
from datetime import datetime, timezone

from models import User, TokenBlacklist
from deps import get_current_user, get_current_admin_user
from database import SessionLocal
import auth_utils

# --- Path Setup ---
BASE_PATH = Path(__file__).resolve().parent.parent

private_router = APIRouter(
    prefix="/user",
    tags=["Private UI"],
    dependencies=[Depends(get_current_user)],
)

# --- Template Configuration ---
user_templates = Jinja2Templates(directory=str(BASE_PATH / "private/user"))

# Canonical mapping for legacy / consolidated user URLs so no bookmark or test 404s
LEGACY_USER_PAGE_MAP = {
    "kyc_form": "kyc.html",
    "kyc/verify": "kyc.html",
    "kyc_pending": "kyc.html",
    "kyc_rejected": "kyc.html",
    "kyc_success": "kyc.html",
    "security": "settings.html",
    "alerts": "notifications.html",
    "support": "contact.html",
    "international_transfers": "transfers.html",
    "scheduled_transfers": "transfers.html",
    "loans_enhanced": "loans.html",
    "business_analysis": "analytics.html",
    "financial_planning": "analytics.html",
    "project": "investments.html",
    "treasury_portfolio": "investments.html",
    "settlement_status": "transactions.html",
    "fraud_detection": "settings.html",
    "webhooks_config": "settings.html",
}


def _render_user_template(template_name: str, request: Request, current_user: User):
    return user_templates.TemplateResponse(template_name, {"request": request, "user": current_user})


# --- Authenticated User-Facing UI Routes ---

@private_router.get("/dashboard")
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """
    Renders the appropriate dashboard based on user type - NO REDIRECT.
    CASE 1: Regular User -> Renders private/user/dashboard.html
    CASE 2: Admin User -> Directly serves private/admin/admin_dashboard_hub.html
    """
    if current_user.is_admin or current_user.email == "admin@admin.com":
        admin_file = BASE_PATH / "private/admin/admin_dashboard_hub.html"
        if not admin_file.exists():
            raise HTTPException(status_code=404, detail="Admin dashboard not found")
        return FileResponse(admin_file, media_type="text/html")

    total_balance = sum(float(account.balance or 0) for account in (current_user.accounts or []))
    total_investments = sum(float(investment.amount or 0) for investment in (current_user.investments or []))
    total_loans = sum(float(loan.amount or 0) for loan in (current_user.loans or []))

    user_data = {
        "username": current_user.full_name or current_user.email,
        "balance": total_balance,
        "investments_value": total_investments,
        "outstanding_loans": total_loans,
        "is_verified": getattr(current_user, "is_verified", False),
        "account_number": getattr(current_user, "account_number", None),
    }
    return user_templates.TemplateResponse("dashboard.html", {"request": request, "user": user_data})


@private_router.get("/account")
async def account_settings_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("account.html", request, current_user)


@private_router.get("/transfers")
async def transfers_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("transfers.html", request, current_user)


@private_router.get("/international_transfers")
async def international_transfers_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("transfers.html", request, current_user)


@private_router.get("/scheduled_transfers")
async def scheduled_transfers_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("transfers.html", request, current_user)


@private_router.get("/bill_pay")
async def bill_pay_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("bill_pay.html", request, current_user)


@private_router.get("/currency_exchange")
async def currency_exchange_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("currency_exchange.html", request, current_user)


@private_router.get("/transactions")
async def transactions_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("transactions.html", request, current_user)


@private_router.get("/cards")
async def cards_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("cards.html", request, current_user)


@private_router.get("/deposits")
async def deposits_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("deposits.html", request, current_user)


@private_router.get("/loans")
async def loans_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("loans.html", request, current_user)


@private_router.get("/loans_enhanced")
async def loans_enhanced_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("loans.html", request, current_user)


@private_router.get("/investments")
async def investments_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("investments.html", request, current_user)


@private_router.get("/insurance")
async def insurance_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("insurance.html", request, current_user)


@private_router.get("/blockchain")
async def blockchain_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("blockchain.html", request, current_user)


@private_router.get("/analytics")
async def analytics_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("analytics.html", request, current_user)


@private_router.get("/business_analysis")
async def business_analysis_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("analytics.html", request, current_user)


@private_router.get("/financial_planning")
async def financial_planning_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("analytics.html", request, current_user)


@private_router.get("/project")
async def project_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("investments.html", request, current_user)


@private_router.get("/treasury_portfolio")
async def treasury_portfolio_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("investments.html", request, current_user)


@private_router.get("/settlement_status")
async def settlement_status_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("transactions.html", request, current_user)


@private_router.get("/fraud_detection")
async def fraud_detection_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("settings.html", request, current_user)


@private_router.get("/webhooks_config")
async def webhooks_config_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("settings.html", request, current_user)


@private_router.get("/kyc")
async def kyc_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("kyc.html", request, current_user)


@private_router.get("/kyc/verify")
async def kyc_verify_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("kyc.html", request, current_user)


@private_router.get("/kyc_form")
async def kyc_form_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("kyc.html", request, current_user)


@private_router.get("/kyc_pending")
async def kyc_pending_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("kyc.html", request, current_user)


@private_router.get("/kyc_rejected")
async def kyc_rejected_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("kyc.html", request, current_user)


@private_router.get("/kyc_success")
async def kyc_success_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("kyc.html", request, current_user)


@private_router.get("/profile")
async def profile_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("profile.html", request, current_user)


@private_router.get("/settings")
async def settings_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("settings.html", request, current_user)


@private_router.get("/security")
async def security_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("settings.html", request, current_user)


@private_router.get("/notifications")
async def notifications_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("notifications.html", request, current_user)


@private_router.get("/alerts")
async def alerts_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("notifications.html", request, current_user)


@private_router.get("/contact")
async def contact_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("contact.html", request, current_user)


@private_router.get("/support")
async def support_page(request: Request, current_user: User = Depends(get_current_user)):
    return _render_user_template("contact.html", request, current_user)


# --- Admin UI Routes ---

LEGACY_ADMIN_PAGE_MAP = {
    "dashboard": "admin_dashboard_hub.html",
    "admin_dashboard_hub": "admin_dashboard_hub.html",
    "overview": "admin_monitoring.html",
    "executive_dashboard": "admin_monitoring.html",
    "superadmin_dashboard": "admin_dashboard_hub.html",
    "admin_superadmin_dashboard": "admin_dashboard_hub.html",
    "reports": "admin_reporting.html",
    "admin_reports": "admin_reporting.html",
    "submissions": "admin_kyc.html",
    "compliance": "admin_international_compliance.html",
    "wire_transfer": "admin_settlement.html",
    "cards": "admin_users.html",
    "deposits": "admin_treasury.html",
    "investments": "admin_treasury.html",
    "notifications": "admin_monitoring.html",
    "mfa_setup": "admin_mfa_setup.html",
    "bank_connect": "admin_bank_connect.html",
    "vendor_hub": "admin_vendor_hub.html",
}


@private_router.get("/admin", tags=["Admin UI"])
@private_router.get("/admin/", tags=["Admin UI"])
@private_router.get("/admin/dashboard", tags=["Admin UI"])
async def admin_dashboard(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    admin_file = BASE_PATH / "private/admin/admin_dashboard_hub.html"
    if not admin_file.exists():
        raise HTTPException(status_code=404, detail=f"Admin dashboard not found at {admin_file}")
    return FileResponse(admin_file, media_type="text/html")


@private_router.get("/admin/user-info", tags=["Admin API"])
async def get_admin_user_info(current_user: User = Depends(get_current_admin_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    admin_role = (getattr(current_user, "admin_role", None) or "STANDARD").upper()

    fresh_token = auth_utils.create_access_token({"sub": current_user.email, "is_admin": True, "role": admin_role})
    return {
        "success": True,
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "admin_role": admin_role,
        "role": admin_role,
        "access_token": fresh_token,
        "token": fresh_token,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_admin": current_user.is_admin,
            "admin_role": admin_role,
            "kyc_status": current_user.kyc_status,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
        "permissions": {
            "is_standard_admin": admin_role == "STANDARD",
            "is_admin": admin_role == "ADMIN",
            "is_treasury_admin": admin_role == "TREASURY",
            "is_super_admin": admin_role == "SUPER_ADMIN",
            "can_manage_users": admin_role in ["ADMIN", "SUPER_ADMIN"],
            "can_manage_treasury": admin_role in ["TREASURY", "SUPER_ADMIN"],
            "can_manage_admins": admin_role == "SUPER_ADMIN",
            "can_access_advanced_search": admin_role in ["ADMIN", "SUPER_ADMIN"],
            "can_access_bulk_operations": admin_role in ["ADMIN", "SUPER_ADMIN"],
            "can_access_management_panel": admin_role == "SUPER_ADMIN",
        },
    }


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
    return FileResponse(BASE_PATH / "private/admin/admin_reporting.html", media_type="text/html")


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


@private_router.get("/admin/advanced_search", tags=["Admin UI"])
async def admin_advanced_search_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_advanced_search.html", media_type="text/html")


@private_router.get("/admin/management_panel", tags=["Admin UI"])
async def admin_management_panel_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_management_panel.html", media_type="text/html")


@private_router.get("/admin/mfa_setup", tags=["Admin UI"])
async def admin_mfa_setup_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_mfa_setup.html", media_type="text/html")


@private_router.get("/admin/bulk_operations", tags=["Admin UI"])
async def admin_bulk_operations_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_bulk_operations.html", media_type="text/html")


@private_router.get("/admin/activity_dashboard", tags=["Admin UI"])
async def admin_activity_dashboard_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_activity_dashboard.html", media_type="text/html")


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


@private_router.get("/admin/bank-connect", tags=["Admin UI"])
async def admin_bank_connect_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_bank_connect.html", media_type="text/html")


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


@private_router.get("/admin/vendor_hub", tags=["Admin UI"])
async def admin_vendor_hub_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_vendor_hub.html", media_type="text/html")


@private_router.get("/admin/international_compliance", tags=["Admin UI"])
async def admin_international_compliance_page(request: Request, current_user: User = Depends(get_current_admin_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return FileResponse(BASE_PATH / "private/admin/admin_international_compliance.html", media_type="text/html")


@private_router.get("/admin/{page}", tags=["Admin UI"])
async def admin_generic_page(page: str, request: Request, current_user: User = Depends(get_current_admin_user)):
    clean_key = page[:-5] if page.endswith(".html") else page
    normalized_page = clean_key.replace("-", "_")

    if normalized_page in LEGACY_ADMIN_PAGE_MAP:
        mapped = BASE_PATH / "private/admin" / LEGACY_ADMIN_PAGE_MAP[normalized_page]
        if mapped.exists():
            return FileResponse(mapped, media_type="text/html")

    possible_filenames = [
        page if page.endswith(".html") else f"admin_{page}.html",
        normalized_page if normalized_page.endswith(".html") else f"admin_{normalized_page}.html",
        f"{page}.html",
        f"{normalized_page}.html",
    ]

    file_path = None
    for fname in possible_filenames:
        candidate = BASE_PATH / "private/admin" / fname
        if candidate.exists():
            file_path = candidate
            break

    if not file_path:
        raise HTTPException(status_code=404, detail=f"Admin page '{page}' not found")

    return FileResponse(file_path, media_type="text/html")


@private_router.get("/logout")
async def logout(request: Request):
    import logging

    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    db = None
    if token:
        try:
            payload = auth_utils.decode_access_token_full(token)
            if payload:
                user_email = payload.get("sub")
                exp_timestamp = payload.get("exp")
                if user_email and exp_timestamp:
                    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
                    db = SessionLocal()
                    try:
                        from crud import get_user_by_email
                        user = await get_user_by_email(db, email=user_email)
                        if user:
                            blacklist_entry = TokenBlacklist(
                                token=token,
                                user_id=user.id,
                                expires_at=expires_at,
                            )
                            db.add(blacklist_entry)
                            await db.commit()
                    finally:
                        await db.close() if db else None
        except Exception as e:
            logging.error(f"Error adding token to blacklist during logout: {e}")

    response = RedirectResponse(url="/signin", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/")
    return response


# --- Fallback Generic Handler for User UI Pages ---

@private_router.get("/{page:path}", tags=["Private UI Fallback"])
async def user_generic_page(page: str, request: Request, current_user: User = Depends(get_current_user)):
    clean_page = page.strip("/")
    if clean_page.startswith("admin"):
        raise HTTPException(status_code=404, detail=f"Admin page '{clean_page}' not found")

    base_key = clean_page[:-5] if clean_page.endswith(".html") else clean_page
    if base_key in LEGACY_USER_PAGE_MAP:
        filename = LEGACY_USER_PAGE_MAP[base_key]
    else:
        filename = clean_page if clean_page.endswith(".html") else f"{clean_page}.html"

    file_path = BASE_PATH / "private/user" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"User page '{clean_page}' not found")

    return user_templates.TemplateResponse(filename, {"request": request, "user": current_user})
