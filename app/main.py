import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .public import public_router
from .database import engine, Base, SessionLocal
from .models import User
from auth_utils import get_password_hash
from auth import auth_router as root_auth_router
from config import settings
from routers.private import private_router
from routers.users import users_router
from routers.admin import admin_router
from routers.kyc import kyc_router
from routers.user_pages import router as user_router
from routers.api_users import router as api_users_router
from routers.transfers import router as transfers_router
from routers.security import router as security_router
from routers.alerts import router as alerts_router
from routers.recipients import router as recipients_router
from routers.business_analysis import router as business_analysis_router
from routers.financial_planning import router as financial_planning_router
from routers.insurance import router as insurance_router
from routers.support import router as support_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

async def create_admin_user():
    """Creates a default admin user if one doesn't exist."""
    async with SessionLocal() as db:
        # Check if admin user exists
        result = await db.execute(select(User).filter(User.email == settings.ADMIN_EMAIL))
        admin_user = result.scalars().first()

        if not admin_user:
            hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            new_admin = User(
                full_name="Admin User",
                email=settings.ADMIN_EMAIL,
                hashed_password=hashed_password,
                is_admin=True,
                is_active=True
            )
            db.add(new_admin)
            await db.commit()
            print("Default admin user created.")

app = FastAPI()
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await create_admin_user()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(public_router)
# Include authenticated UI routes (user + admin pages)
app.include_router(private_router)
# Register the root `auth` router so `/auth/*` endpoints are available
app.include_router(root_auth_router, prefix="/auth")
# API & other routers
app.include_router(users_router, prefix="/api/v1/users")
app.include_router(admin_router, prefix="/api/admin")
app.include_router(api_users_router)  # /api/user/* endpoints
app.include_router(kyc_router, prefix="/api/v1")
# New banking feature routers
app.include_router(transfers_router)  # /api/transfers/* endpoints
app.include_router(security_router)  # /api/security/* endpoints
app.include_router(alerts_router)  # /api/alerts/* endpoints
app.include_router(recipients_router)  # /api/recipients/* endpoints
# Analysis and planning routers
app.include_router(business_analysis_router)  # /api/user/analysis/* endpoints
app.include_router(financial_planning_router)  # /api/v1/financial/* endpoints
app.include_router(insurance_router)  # /api/v1/insurance/* endpoints
app.include_router(support_router)  # /api/v1/support/* endpoints
# Include user-facing pages (prefix defined in the router as /user)
app.include_router(user_router)

# Static mounts for assets (match root `main.py` mounts)
from fastapi.staticfiles import StaticFiles
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/lib", StaticFiles(directory="static/lib"), name="lib")
app.mount("/img", StaticFiles(directory="static/img"), name="img")

# Public static site (last mount)
app.mount("/", StaticFiles(directory="static", html=True), name="public")