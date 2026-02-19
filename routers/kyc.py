from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Request
from typing import Annotated, Optional
import os
from deps import SessionDep, get_current_user, get_current_admin_user
from crud import create_kyc_submission
from pathlib import Path
from datetime import datetime
from models import User, KYCInfo
from sqlalchemy import select
from kyc_service import KYCService

kyc_router = APIRouter(tags=["kyc"])

UPLOAD_DIR = Path("private/uploads/kyc")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@kyc_router.post("/kyc/verify")
async def submit_kyc(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    document_type: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a KYC document and update user's KYC tracking status.
    
    Supported document types:
    - id_front: Front of government ID
    - id_back: Back of government ID
    - ssn_tax_id: Social Security Number or Tax ID document
    - proof_of_address: Proof of address document (utility bill, etc.)
    
    When all 4 required documents are uploaded, kyc_status automatically moves to 'submitted'.
    """
    try:
        # Validate document type
        valid_types = {"id_front", "id_back", "ssn_tax_id", "proof_of_address"}
        if document_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document type. Allowed: {valid_types}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Use KYC Service to save document and update status
        success, message, file_path = await KYCService.save_document(
            db_session=db_session,
            user_id=current_user.id,
            document_type=document_type,
            file_content=file_content,
            filename=file.filename or "document"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Get updated KYC status
        kyc_status = await KYCService.get_kyc_status(db_session, current_user.id)
        
        return {
            "status": "success",
            "message": message,
            "document_type": document_type,
            "kyc_status": kyc_status["kyc_status"],
            "all_documents_uploaded": kyc_status["all_required_uploaded"],
            "documents_submitted": kyc_status["documents_uploaded"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


@kyc_router.get("/kyc/status")
async def get_kyc_status_endpoint(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get current user's KYC status and document upload tracking"""
    try:
        kyc_status = await KYCService.get_kyc_status(db_session, current_user.id)
        return kyc_status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving KYC status: {str(e)}"
        )


@kyc_router.get("/kyc/submissions")
async def get_kyc_submissions(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get current user's KYC submission history and status"""
    try:
        result = await db_session.execute(
            select(KYCInfo).filter(KYCInfo.user_id == current_user.id)
        )
        kyc_info = result.scalars().first()
        
        if not kyc_info:
            # Create a default KYC record if none exists
            kyc_info = KYCInfo(user_id=current_user.id)
            db_session.add(kyc_info)
            await db_session.commit()
        
        return {
            "id": kyc_info.id,
            "user_id": kyc_info.user_id,
            "kyc_status": kyc_info.kyc_status,
            "kyc_submitted": kyc_info.kyc_submitted,
            "submission_timestamp": kyc_info.submission_timestamp,
            "id_front_uploaded": kyc_info.id_front_uploaded,
            "id_back_uploaded": kyc_info.id_back_uploaded,
            "ssn_uploaded": kyc_info.ssn_uploaded,
            "proof_of_address_uploaded": kyc_info.proof_of_address_uploaded,
            "id_front_path": kyc_info.id_front_path,
            "id_back_path": kyc_info.id_back_path,
            "ssn_path": kyc_info.ssn_path,
            "proof_of_address_path": kyc_info.proof_of_address_path,
            "submitted_at": kyc_info.submitted_at,
            "approved_at": kyc_info.approved_at
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving submissions: {str(e)}"
        )


@kyc_router.post("/kyc/validate")
async def validate_kyc_documents(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    date_of_birth: Optional[str] = Form(None),
    id_expiry_date: Optional[str] = Form(None),
    proof_of_address_date: Optional[str] = Form(None)
):
    """
    Validate KYC documents for:
    - Age >= 18
    - ID not expired
    - Proof of address within 3 months
    
    Dates should be in ISO format (YYYY-MM-DD)
    """
    try:
        # Parse dates
        dob = None
        id_exp = None
        addr_date = None
        
        if date_of_birth:
            dob = datetime.fromisoformat(date_of_birth)
        if id_expiry_date:
            id_exp = datetime.fromisoformat(id_expiry_date)
        if proof_of_address_date:
            addr_date = datetime.fromisoformat(proof_of_address_date)
        
        is_valid, error_msg = await KYCService.validate_kyc_documents(
            db_session=db_session,
            user_id=current_user.id,
            date_of_birth=dob,
            id_expiry_date=id_exp,
            proof_of_address_date=addr_date
        )
        
        return {
            "is_valid": is_valid,
            "message": error_msg if not is_valid else "All validations passed!"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating documents: {str(e)}"
        )


@kyc_router.post("/kyc/submit")
async def submit_kyc_form(
    request: Request,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """
    USER ENDPOINT: Finalize and lock KYC submission.
    
    This endpoint:
    1. Accepts email, document_type, and document_number from the form
    2. Validates all required documents are uploaded
    3. Validates personal details are complete
    4. Locks the form (sets kyc_submitted=True)
    5. Updates kyc_status to 'submitted'
    6. Sets submission_timestamp
    7. Prevents any further edits to documents or personal details
    
    After calling this endpoint, the form becomes read-only until admin approves or rejects.
    
    Request body:
    {
        "email": "user@example.com",
        "document_type": "passport",
        "document_number": "ABC123456"
    }
    """
    try:
        # Parse request body
        body = await request.json()
        
        # Extract and validate required fields
        email = body.get('email', '').strip()
        document_type = body.get('document_type', '').strip()
        document_number = body.get('document_number', '').strip()
        
        # Log what we received
        print(f"\n📥 KYC SUBMIT - Received from frontend:")
        print(f"   Email: {email}")
        print(f"   Document Type: {document_type}")
        print(f"   Document Number: {document_number}")
        print(f"   User ID: {current_user.id}")
        
        # Validate required fields
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is required"
            )
        if not document_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document type is required"
            )
        if not document_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document number is required"
            )
        
        # Verify email matches current user
        if email.lower() != current_user.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match your account email"
            )
        
        # Call KYC service to complete submission
        success, message, kyc_data = await KYCService.submit_kyc_form(
            db_session=db_session,
            user_id=current_user.id,
            email=email,
            document_type=document_type,
            document_number=document_number
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        # Log successful submission
        print(f"\n✅ KYC SUBMIT - Success")
        print(f"   KYC ID: {kyc_data.get('kyc_id')}")
        print(f"   User ID: {current_user.id}")
        print(f"   Email: {email}")
        print(f"   Document: {document_type} {document_number}")
        print(f"   Timestamp: {kyc_data.get('submission_timestamp')}")
        
        return {
            "status": "success",
            "message": message,
            "kyc_status": "submitted",
            "kyc_submitted": True,
            "submission_locked": True,
            "submission_timestamp": kyc_data.get("submission_timestamp"),
            "user_email": email,
            "document_type": document_type,
            "document_number": document_number,
            "user_message": "Your KYC has been submitted successfully. You cannot modify your documents or personal details while verification is in progress."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n❌ KYC SUBMIT - Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error submitting KYC: {str(e)}"
        )


@kyc_router.post("/kyc/admin/approve")
async def admin_approve_kyc(
    user_id: int,
    reviewer_notes: str = Form(""),
    db_session: SessionDep = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """[ADMIN ONLY] Approve a user's KYC submission"""
    if db_session is None:
        # This shouldn't happen with proper dependency injection
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session error"
        )
    
    try:
        success, message = await KYCService.approve_kyc(
            db_session=db_session,
            user_id=user_id,
            reviewer_notes=reviewer_notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return {
            "status": "success",
            "message": message,
            "user_id": user_id,
            "kyc_status": "approved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving KYC: {str(e)}"
        )


@kyc_router.post("/kyc/admin/reject")
async def admin_reject_kyc(
    user_id: int,
    rejection_reason: str = Form(...),
    db_session: SessionDep = None,
    current_admin: User = Depends(get_current_admin_user)
):
    """[ADMIN ONLY] Reject a user's KYC submission with reason"""
    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session error"
        )
    
    try:
        success, message = await KYCService.reject_kyc(
            db_session=db_session,
            user_id=user_id,
            rejection_reason=rejection_reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
        
        return {
            "status": "success",
            "message": message,
            "user_id": user_id,
            "kyc_status": "rejected",
            "rejection_reason": rejection_reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting KYC: {str(e)}"
        )
