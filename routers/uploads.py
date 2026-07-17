"""File upload and profile document endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User
from file_upload_service import FileUploadService
import logging

logger = logging.getLogger(__name__)

uploads_router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@uploads_router.post("/profile-picture", status_code=status.HTTP_201_CREATED)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """Upload a profile picture for the current user."""
    result = await FileUploadService.upload_profile_picture(
        user_id=current_user.id,
        file=file,
        db=db_session,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@uploads_router.post("/kyc/{document_type}", status_code=status.HTTP_201_CREATED)
async def upload_kyc_document(
    document_type: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """
    Upload a KYC document.

    document_type must be one of: id_front, id_back, ssn, proof_of_address
    """
    result = await FileUploadService.upload_kyc_document(
        user_id=current_user.id,
        document_type=document_type,
        file=file,
        db=db_session,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@uploads_router.get("/my-uploads")
async def get_my_uploads(
    current_user: User = Depends(get_current_user),
):
    """Get list of all uploads for the current user."""
    result = await FileUploadService.get_user_uploads(current_user.id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@uploads_router.delete("/{file_path}", status_code=status.HTTP_200_OK)
async def delete_upload(
    file_path: str,
    current_user: User = Depends(get_current_user),
):
    """Delete an uploaded file (security: user can only delete their own files)."""
    result = await FileUploadService.delete_file(file_path, current_user.id)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result
