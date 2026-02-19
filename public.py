from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.status import HTTP_303_SEE_OTHER
#
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from fastapi import Depends
# import models
# from deps import get_db
# from auth_utils import get_password_hash, verify_password

public_router = APIRouter()
# STATIC_DIR = "static"
#
# @public_router.get("/", response_class=FileResponse)
# async def home(request: Request):
#     return FileResponse(f"{STATIC_DIR}/index.html")
#
# @public_router.get("/about.html", response_class=FileResponse)
# async def about(request: Request):
#     return FileResponse(f"{STATIC_DIR}/about.html")
#
# @public_router.get("/service.html", response_class=FileResponse)
# async def service(request: Request):
#     return FileResponse(f"{STATIC_DIR}/service.html")
#
# @public_router.get("/contact.html", response_class=FileResponse)
# async def contact(request: Request):
#     return FileResponse(f"{STATIC_DIR}/contact.html")
#
# @public_router.get("/deposits.html", response_class=FileResponse)
# async def deposits(request: Request):
#     return FileResponse(f"{STATIC_DIR}/deposits.html")
#
# @public_router.get("/credits.html", response_class=FileResponse)
# async def credits(request: Request):
#     return FileResponse(f"{STATIC_DIR}/credits.html")
#
# @public_router.get("/cards.html", response_class=FileResponse)
# async def cards(request: Request):
#     return FileResponse(f"{STATIC_DIR}/cards.html")
#
# @public_router.get("/investments.html", response_class=FileResponse)
# async def investments(request: Request):
#     return FileResponse(f"{STATIC_DIR}/investments.html")
#
# @public_router.get("/loans.html", response_class=FileResponse)
# async def loans(request: Request):
#     return FileResponse(f"{STATIC_DIR}/loans.html")
#
# @public_router.get("/insurance.html", response_class=FileResponse)
# async def insurance(request: Request):
#     return FileResponse(f"{STATIC_DIR}/insurance.html")
#
# @public_router.get("/personal.html", response_class=FileResponse)
# async def personal(request: Request):
#     return FileResponse(f"{STATIC_DIR}/personal.html")
#
# @public_router.get("/corporate.html", response_class=FileResponse)
# async def corporate(request: Request):
#     return FileResponse(f"{STATIC_DIR}/corporate.html")
#     
# @public_router.get("/features.html", response_class=FileResponse)
# async def features(request: Request):
#     return FileResponse(f"{STATIC_DIR}/features.html")
#
# @public_router.get("/e-banking.html", response_class=FileResponse)
# async def e_banking(request: Request):
#     return FileResponse(f"{STATIC_DIR}/signin.html")