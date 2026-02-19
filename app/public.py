from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.status import HTTP_303_SEE_OTHER

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends
from . import models
from .database import get_db, SessionLocal
from auth_utils import get_password_hash, verify_password

public_router = APIRouter()
STATIC_DIR = "static"

@public_router.get("/", response_class=FileResponse)
async def home(request: Request):
    return FileResponse(f"{STATIC_DIR}/index.html")

@public_router.get("/about.html", response_class=FileResponse)
async def about(request: Request):
    return FileResponse(f"{STATIC_DIR}/about.html")

@public_router.get("/service.html", response_class=FileResponse)
async def service(request: Request):
    return FileResponse(f"{STATIC_DIR}/service.html")

@public_router.get("/contact.html", response_class=FileResponse)
async def contact(request: Request):
    return FileResponse(f"{STATIC_DIR}/contact.html")

@public_router.get("/deposits.html", response_class=FileResponse)
async def deposits(request: Request):
    return FileResponse(f"{STATIC_DIR}/deposits.html")

@public_router.get("/credits.html", response_class=FileResponse)
async def credits(request: Request):
    return FileResponse(f"{STATIC_DIR}/credits.html")

@public_router.get("/cards.html", response_class=FileResponse)
async def cards(request: Request):
    return FileResponse(f"{STATIC_DIR}/cards.html")

@public_router.get("/investments.html", response_class=FileResponse)
async def investments(request: Request):
    return FileResponse(f"{STATIC_DIR}/investments.html")

@public_router.get("/loans.html", response_class=FileResponse)
async def loans(request: Request):
    return FileResponse(f"{STATIC_DIR}/loans.html")

@public_router.get("/insurance.html", response_class=FileResponse)
async def insurance(request: Request):
    return FileResponse(f"{STATIC_DIR}/insurance.html")

@public_router.get("/personal.html", response_class=FileResponse)
async def personal(request: Request):
    return FileResponse(f"{STATIC_DIR}/personal.html")

@public_router.get("/corporate.html", response_class=FileResponse)
async def corporate(request: Request):
    return FileResponse(f"{STATIC_DIR}/corporate.html")

@public_router.get("/signup.html", response_class=FileResponse)
async def signup(request: Request):
    return FileResponse(f"{STATIC_DIR}/signup.html")

@public_router.get("/signin.html", response_class=FileResponse)
async def signin_page(request: Request):
    return FileResponse(f"{STATIC_DIR}/signin.html")

@public_router.post("/register")
async def register_user(full_name: str = Form(...), email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(models.User).filter(models.User.email == email))
    db_user = result.scalars().first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password and create the new user
    hashed_password = get_password_hash(password)
    new_user = models.User(full_name=full_name, email=email, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return JSONResponse(content={"message": "Registration successful! Redirecting to sign in..."}, status_code=201)

@public_router.post("/signin")
async def signin_post(username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    # The 'username' from the form is treated as the email
    result = await db.execute(select(models.User).filter(models.User.email == username))
    user = result.scalars().first()

    # Check if user exists and password is correct
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    # Successful login: Return a success response.
    # The frontend will handle the redirect.
    # In a real production app, you would create a session or JWT here.
    return JSONResponse(content={"message": "Sign in successful!"})