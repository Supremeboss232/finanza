"""User routes for FastAPI application."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from deps import get_current_user
from models import User

BASE_PATH = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory="templates")
user_templates = Jinja2Templates(directory=str(BASE_PATH / "private" / "user"))

ROUTE_MAPPING = {
    "home": "/",
    "read_about": "/about",
    "services": "/service",
    "read_contact": "/contact",
    "read_dashboard": "/user/dashboard",
    "signin": "/signin",
}


def url_for(endpoint: str) -> str:
    return ROUTE_MAPPING.get(endpoint, "/")


router = APIRouter(
    prefix="/user",
    tags=["user"],
    dependencies=[Depends(get_current_user)],
)


def _render(tpl: str, title: str, request: Request, current_user: User):
    context = {
        "request": request,
        "user": current_user,
        "page_title": title,
        "url_for": url_for,
    }
    try:
        return user_templates.TemplateResponse(request=request, name=tpl, context=context)
    except TypeError:
        return user_templates.TemplateResponse(tpl, context)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    return _render("dashboard.html", "Dashboard", request, current_user)


@router.get("/account", response_class=HTMLResponse)
async def account(request: Request, current_user: User = Depends(get_current_user)):
    return _render("account.html", "Accounts & Statements", request, current_user)


@router.get("/kyc", response_class=HTMLResponse)
async def kyc(request: Request, current_user: User = Depends(get_current_user)):
    return _render("kyc.html", "KYC Verification", request, current_user)


@router.get("/cards", response_class=HTMLResponse)
async def cards(request: Request, current_user: User = Depends(get_current_user)):
    return _render("cards.html", "Cards", request, current_user)


@router.get("/deposits", response_class=HTMLResponse)
async def deposits(request: Request, current_user: User = Depends(get_current_user)):
    return _render("deposits.html", "Savings & Deposits", request, current_user)


@router.get("/loans", response_class=HTMLResponse)
async def loans(request: Request, current_user: User = Depends(get_current_user)):
    return _render("loans.html", "Loans & Credit", request, current_user)


@router.get("/investments", response_class=HTMLResponse)
async def investments(request: Request, current_user: User = Depends(get_current_user)):
    return _render("investments.html", "Investments", request, current_user)


@router.get("/business_analysis", response_class=HTMLResponse)
async def business_analysis(request: Request, current_user: User = Depends(get_current_user)):
    return _render("analytics.html", "Financial Analytics", request, current_user)


@router.get("/financial_planning", response_class=HTMLResponse)
async def financial_planning(request: Request, current_user: User = Depends(get_current_user)):
    return _render("analytics.html", "Financial Analytics", request, current_user)


@router.get("/insurance", response_class=HTMLResponse)
async def insurance(request: Request, current_user: User = Depends(get_current_user)):
    return _render("insurance.html", "Insurance", request, current_user)


@router.get("/project", response_class=HTMLResponse)
async def project(request: Request, current_user: User = Depends(get_current_user)):
    return _render("investments.html", "Investments", request, current_user)


@router.get("/settings", response_class=HTMLResponse)
async def settings(request: Request, current_user: User = Depends(get_current_user)):
    return _render("settings.html", "Settings & Security", request, current_user)


@router.get("/notifications", response_class=HTMLResponse)
async def notifications(request: Request, current_user: User = Depends(get_current_user)):
    return _render("notifications.html", "Notifications", request, current_user)


@router.get("/transactions", response_class=HTMLResponse)
async def transactions(request: Request, current_user: User = Depends(get_current_user)):
    return _render("transactions.html", "Transactions", request, current_user)


@router.get("/transfers", response_class=HTMLResponse)
async def transfers(request: Request, current_user: User = Depends(get_current_user)):
    return _render("transfers.html", "Transfers", request, current_user)


@router.get("/security", response_class=HTMLResponse)
async def security(request: Request, current_user: User = Depends(get_current_user)):
    return _render("settings.html", "Security & Settings", request, current_user)


@router.get("/alerts", response_class=HTMLResponse)
async def alerts(request: Request, current_user: User = Depends(get_current_user)):
    return _render("notifications.html", "Alerts & Notifications", request, current_user)


@router.get("/contact", response_class=HTMLResponse)
async def contact(request: Request, current_user: User = Depends(get_current_user)):
    return _render("contact.html", "Concierge Support", request, current_user)


@router.get("/scheduled_transfers", response_class=HTMLResponse)
async def scheduled_transfers(request: Request, current_user: User = Depends(get_current_user)):
    return _render("transfers.html", "Scheduled Transfers", request, current_user)


@router.get("/webhooks_config", response_class=HTMLResponse)
async def webhooks_config(request: Request, current_user: User = Depends(get_current_user)):
    return _render("settings.html", "Settings & Security", request, current_user)
