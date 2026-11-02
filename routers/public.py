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
@public_router.get("/about.html", response_class=FileResponse)
@public_router.get("/static/about.html", response_class=FileResponse)
async def public_about():
    return get_html_response("about.html")

@public_router.get("/business_analysis", response_class=FileResponse)
@public_router.get("/business_analysis.html", response_class=FileResponse)
@public_router.get("/static/business_analysis.html", response_class=FileResponse)
async def public_business_analysis():
    return get_html_response("business_analysis.html")

@public_router.get("/cards", response_class=FileResponse)
@public_router.get("/cards.html", response_class=FileResponse)
@public_router.get("/static/cards.html", response_class=FileResponse)
async def public_cards():
    return get_html_response("cards.html")

@public_router.get("/contact", response_class=FileResponse)
@public_router.get("/contact.html", response_class=FileResponse)
@public_router.get("/static/contact.html", response_class=FileResponse)
async def public_contact():
    return get_html_response("contact.html")

@public_router.get("/corporate", response_class=FileResponse)
@public_router.get("/corporate.html", response_class=FileResponse)
@public_router.get("/static/corporate.html", response_class=FileResponse)
async def public_corporate():
    return get_html_response("corporate.html")

@public_router.get("/credits", response_class=FileResponse)
@public_router.get("/credits.html", response_class=FileResponse)
@public_router.get("/static/credits.html", response_class=FileResponse)
async def public_credits():
    return get_html_response("credits.html")

@public_router.get("/deposits", response_class=FileResponse)
@public_router.get("/deposits.html", response_class=FileResponse)
@public_router.get("/static/deposits.html", response_class=FileResponse)
async def public_deposits():
    return get_html_response("deposits.html")

@public_router.get("/feature", response_class=FileResponse)
@public_router.get("/feature.html", response_class=FileResponse)
@public_router.get("/static/feature.html", response_class=FileResponse)
async def public_feature():
    return get_html_response("feature.html")

@public_router.get("/financial_consultancy", response_class=FileResponse)
@public_router.get("/financial_consultancy.html", response_class=FileResponse)
@public_router.get("/static/financial_consultancy.html", response_class=FileResponse)
async def public_financial_consultancy():
    return get_html_response("financial_consultancy.html")

@public_router.get("/financial_planning", response_class=FileResponse)
@public_router.get("/financial_planning.html", response_class=FileResponse)
@public_router.get("/static/financial_planning.html", response_class=FileResponse)
async def public_financial_planning():
    return get_html_response("financial_planning.html")

@public_router.get("/forgot_password", response_class=FileResponse)
@public_router.get("/forgot_password.html", response_class=FileResponse)
@public_router.get("/static/forgot_password.html", response_class=FileResponse)
@public_router.get("/forgot-password", response_class=FileResponse)
async def public_forgot_password():
    return get_html_response("forgot_password.html")

@public_router.get("/insurance", response_class=FileResponse)
@public_router.get("/insurance.html", response_class=FileResponse)
@public_router.get("/static/insurance.html", response_class=FileResponse)
async def public_insurance():
    return get_html_response("insurance.html")

@public_router.get("/investments", response_class=FileResponse)
@public_router.get("/investments.html", response_class=FileResponse)
@public_router.get("/static/investments.html", response_class=FileResponse)
async def public_investments():
    return get_html_response("investments.html")

@public_router.get("/loans", response_class=FileResponse)
@public_router.get("/loans.html", response_class=FileResponse)
@public_router.get("/static/loans.html", response_class=FileResponse)
async def public_loans():
    return get_html_response("loans.html")

@public_router.get("/personal", response_class=FileResponse)
@public_router.get("/personal.html", response_class=FileResponse)
@public_router.get("/static/personal.html", response_class=FileResponse)
async def public_personal():
    return get_html_response("personal.html")

@public_router.get("/project", response_class=FileResponse)
@public_router.get("/project.html", response_class=FileResponse)
@public_router.get("/static/project.html", response_class=FileResponse)
async def public_project():
    return get_html_response("project.html")

@public_router.get("/reset_password", response_class=FileResponse)
@public_router.get("/reset_password.html", response_class=FileResponse)
@public_router.get("/static/reset_password.html", response_class=FileResponse)
@public_router.get("/reset-password", response_class=FileResponse)
async def public_reset_password():
    return get_html_response("reset_password.html")

@public_router.get("/service", response_class=FileResponse)
@public_router.get("/service.html", response_class=FileResponse)
@public_router.get("/static/service.html", response_class=FileResponse)
async def public_service():
    return get_html_response("service.html")

@public_router.get("/team", response_class=FileResponse)
@public_router.get("/team.html", response_class=FileResponse)
@public_router.get("/static/team.html", response_class=FileResponse)
async def public_team():
    return get_html_response("team.html")

@public_router.get("/testimonial", response_class=FileResponse)
@public_router.get("/testimonial.html", response_class=FileResponse)
@public_router.get("/static/testimonial.html", response_class=FileResponse)
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
@public_router.get("/sitemap.html", response_class=FileResponse)
@public_router.get("/static/sitemap.html", response_class=FileResponse)
async def public_sitemap():
    return get_html_response("sitemap.html")


@public_router.get("/index.html", response_class=FileResponse)
async def public_index_html():
    return get_html_response("index.html")

@public_router.get("/404", response_class=FileResponse)
@public_router.get("/404.html", response_class=FileResponse)
async def public_404():
    return get_html_response("404.html")

@public_router.get("/unauthorized", response_class=FileResponse)
@public_router.get("/unauthorized.html", response_class=FileResponse)
async def public_unauthorized():
    return get_html_response("unauthorized.html")

@public_router.get("/verify-email", response_class=FileResponse)
@public_router.get("/verify_email.html", response_class=FileResponse)
async def public_verify_email():
    return get_html_response("verify_email.html")
