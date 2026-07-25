from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os

public_router = APIRouter(tags=["Public UI"])
STATIC_DIR = "static"

def get_html_response(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@public_router.get("/about", response_class=FileResponse)
async def public_about():
    return get_html_response("about.html")

@public_router.get("/business_analysis", response_class=FileResponse)
async def public_business_analysis():
    return get_html_response("business_analysis.html")

@public_router.get("/cards", response_class=FileResponse)
async def public_cards():
    return get_html_response("cards.html")

@public_router.get("/contact", response_class=FileResponse)
async def public_contact():
    return get_html_response("contact.html")

@public_router.get("/corporate", response_class=FileResponse)
async def public_corporate():
    return get_html_response("corporate.html")

@public_router.get("/credits", response_class=FileResponse)
async def public_credits():
    return get_html_response("credits.html")

@public_router.get("/deposits", response_class=FileResponse)
async def public_deposits():
    return get_html_response("deposits.html")

@public_router.get("/feature", response_class=FileResponse)
async def public_feature():
    return get_html_response("feature.html")

@public_router.get("/financial_consultancy", response_class=FileResponse)
async def public_financial_consultancy():
    return get_html_response("financial_consultancy.html")

@public_router.get("/financial_planning", response_class=FileResponse)
async def public_financial_planning():
    return get_html_response("financial_planning.html")

@public_router.get("/forgot_password", response_class=FileResponse)
@public_router.get("/forgot-password", response_class=FileResponse)
async def public_forgot_password():
    return get_html_response("forgot_password.html")

@public_router.get("/insurance", response_class=FileResponse)
async def public_insurance():
    return get_html_response("insurance.html")

@public_router.get("/investments", response_class=FileResponse)
async def public_investments():
    return get_html_response("investments.html")

@public_router.get("/loans", response_class=FileResponse)
async def public_loans():
    return get_html_response("loans.html")

@public_router.get("/personal", response_class=FileResponse)
async def public_personal():
    return get_html_response("personal.html")

@public_router.get("/project", response_class=FileResponse)
async def public_project():
    return get_html_response("project.html")

@public_router.get("/reset_password", response_class=FileResponse)
@public_router.get("/reset-password", response_class=FileResponse)
async def public_reset_password():
    return get_html_response("reset_password.html")

@public_router.get("/service", response_class=FileResponse)
async def public_service():
    return get_html_response("service.html")

@public_router.get("/team", response_class=FileResponse)
async def public_team():
    return get_html_response("team.html")

@public_router.get("/testimonial", response_class=FileResponse)
async def public_testimonial():
    return get_html_response("testimonial.html")

@public_router.get("/signin", response_class=FileResponse)
@public_router.get("/signin.html", response_class=FileResponse)
async def public_signin():
    return get_html_response("signin.html")

@public_router.get("/signup", response_class=FileResponse)
@public_router.get("/signup.html", response_class=FileResponse)
async def public_signup():
    return get_html_response("signup.html")

@public_router.get("/sitemap", response_class=FileResponse)
async def public_sitemap():
    return get_html_response("sitemap.html")