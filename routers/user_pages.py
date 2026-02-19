"""User routes for FastAPI application."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from deps import get_current_user
from models import User

# Setup template directories
BASE_PATH = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory="templates")
user_templates = Jinja2Templates(directory=str(BASE_PATH / "private" / "user"))

# Map Flask-style route names to FastAPI URLs for compatibility with existing templates
ROUTE_MAPPING = {
    'home': '/',
    'read_about': '/about',
    'services': '/service',
    'read_contact': '/contact',
    'read_dashboard': '/user/dashboard',
    'signin': '/signin',
}

def url_for(endpoint: str) -> str:
    """Map Flask-style endpoint names to FastAPI routes for template compatibility."""
    return ROUTE_MAPPING.get(endpoint, '/')

router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(get_current_user)]
)


# MAIN ROUTES
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """User dashboard - overview and key metrics.

    The user-facing templates are stored under `private/user/` in this
    project (not the top-level `templates/` directory). Render the
    correct template path so Jinja can locate the file.
    """
    # Render the dashboard from the `private/user` templates directory
    return user_templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "page_title": "Dashboard",
        "url_for": url_for
    })


@router.get("/account", response_class=HTMLResponse)
async def account(request: Request, current_user: User = Depends(get_current_user)):
    """User account and profile management."""
    return user_templates.TemplateResponse("account.html", {
        "request": request,
        "user": current_user,
        "page_title": "Account",
        "url_for": url_for
    })


@router.get("/kyc", response_class=HTMLResponse)
async def kyc(request: Request, current_user: User = Depends(get_current_user)):
    """KYC (Know Your Customer) verification."""
    return user_templates.TemplateResponse("kyc.html", {
        "request": request,
        "user": current_user,
        "page_title": "KYC Verification",
        "url_for": url_for
    })


# FINANCIAL PRODUCTS
@router.get("/cards", response_class=HTMLResponse)
async def cards(request: Request, current_user: User = Depends(get_current_user)):
    """User cards management."""
    return user_templates.TemplateResponse("cards.html", {
        "request": request,
        "user": current_user,
        "page_title": "Cards",
        "url_for": url_for
    })


@router.get("/deposits", response_class=HTMLResponse)
async def deposits(request: Request, current_user: User = Depends(get_current_user)):
    """User deposits management."""
    return user_templates.TemplateResponse("deposits.html", {
        "request": request,
        "user": current_user,
        "page_title": "Deposits",
        "url_for": url_for
    })


@router.get("/loans", response_class=HTMLResponse)
async def loans(request: Request, current_user: User = Depends(get_current_user)):
    """User loans management."""
    return user_templates.TemplateResponse("loans.html", {
        "request": request,
        "user": current_user,
        "page_title": "Loans",
        "url_for": url_for
    })


@router.get("/investments", response_class=HTMLResponse)
async def investments(request: Request, current_user: User = Depends(get_current_user)):
    """User investments management."""
    return user_templates.TemplateResponse("investments.html", {
        "request": request,
        "user": current_user,
        "page_title": "Investments",
        "url_for": url_for
    })


# TOOLS & ANALYTICS
@router.get("/business_analysis", response_class=HTMLResponse)
async def business_analysis(request: Request, current_user: User = Depends(get_current_user)):
    """Business analysis tools."""
    return user_templates.TemplateResponse("business_analysis.html", {
        "request": request,
        "user": current_user,
        "page_title": "Business Analysis",
        "url_for": url_for
    })


@router.get("/financial_planning", response_class=HTMLResponse)
async def financial_planning(request: Request, current_user: User = Depends(get_current_user)):
    """Financial planning tools."""
    return user_templates.TemplateResponse("financial_planning.html", {
        "request": request,
        "user": current_user,
        "page_title": "Financial Planning",
        "url_for": url_for
    })


@router.get("/insurance", response_class=HTMLResponse)
async def insurance(request: Request, current_user: User = Depends(get_current_user)):
    """Insurance products."""
    return user_templates.TemplateResponse("insurance.html", {
        "request": request,
        "user": current_user,
        "page_title": "Insurance",
        "url_for": url_for
    })


@router.get("/project", response_class=HTMLResponse)
async def project(request: Request, current_user: User = Depends(get_current_user)):
    """User projects."""
    return user_templates.TemplateResponse("project.html", {
        "request": request,
        "user": current_user,
        "page_title": "Projects",
        "url_for": url_for
    })


# USER UTILITIES
@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, current_user: User = Depends(get_current_user)):
    """User settings."""
    return user_templates.TemplateResponse("settings.html", {
        "request": request,
        "user": current_user,
        "page_title": "Settings",
        "url_for": url_for
    })


@router.get("/notifications", response_class=HTMLResponse)
async def notifications(request: Request, current_user: User = Depends(get_current_user)):
    """User notifications."""
    return user_templates.TemplateResponse("notifications.html", {
        "request": request,
        "user": current_user,
        "page_title": "Notifications",
        "url_for": url_for
    })


# NEW BANKING FEATURES
@router.get("/transactions", response_class=HTMLResponse)
async def transactions(request: Request, current_user: User = Depends(get_current_user)):
    """Transaction history and management."""
    return user_templates.TemplateResponse("transactions.html", {
        "request": request,
        "user": current_user,
        "page_title": "Transactions",
        "url_for": url_for
    })


@router.get("/transfers", response_class=HTMLResponse)
async def transfers(request: Request, current_user: User = Depends(get_current_user)):
    """Money transfers and bill pay."""
    return user_templates.TemplateResponse("transfers.html", {
        "request": request,
        "user": current_user,
        "page_title": "Transfers",
        "url_for": url_for
    })


@router.get("/security", response_class=HTMLResponse)
async def security(request: Request, current_user: User = Depends(get_current_user)):
    """Security settings and authentication."""
    return user_templates.TemplateResponse("security.html", {
        "request": request,
        "user": current_user,
        "page_title": "Security",
        "url_for": url_for
    })


@router.get("/alerts", response_class=HTMLResponse)
async def alerts(request: Request, current_user: User = Depends(get_current_user)):
    """Alert and notification preferences."""
    return user_templates.TemplateResponse("alerts.html", {
        "request": request,
        "user": current_user,
        "page_title": "Alerts",
        "url_for": url_for
    })


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, current_user: User = Depends(get_current_user)):
    """Contact and support."""
    return user_templates.TemplateResponse("contact.html", {
        "request": request,
        "user": current_user,
        "page_title": "Contact Support",
        "url_for": url_for
    })


@router.get("/scheduled_transfers", response_class=HTMLResponse)
async def scheduled_transfers(request: Request, current_user: User = Depends(get_current_user)):
    """Scheduled and recurring transfers."""
    return user_templates.TemplateResponse("scheduled_transfers.html", {
        "request": request,
        "user": current_user,
        "page_title": "Scheduled Transfers",
        "url_for": url_for
    })


@router.get("/webhooks_config", response_class=HTMLResponse)
async def webhooks_config(request: Request, current_user: User = Depends(get_current_user)):
    """User webhook configuration and management."""
    return user_templates.TemplateResponse("webhooks_config.html", {
        "request": request,
        "user": current_user,
        "page_title": "Webhook Configuration",
        "url_for": url_for
    })
