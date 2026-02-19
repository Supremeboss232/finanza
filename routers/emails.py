# routers/emails.py
# Email service router for transactional emails

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import logging

from ses_service import ses_service
from email_templates import (
    get_welcome_email_template,
    get_password_reset_email_template,
    get_kyc_submission_template,
    get_transaction_confirmation_template,
    get_account_alert_template,
    get_loan_approval_template
)
from deps import get_current_user, SessionDep
from models import User

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/emails", tags=["emails"])


# Request/Response models
class SendEmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    html_body: str
    text_body: Optional[str] = None
    tags: Optional[dict] = None


class SendWelcomeEmailRequest(BaseModel):
    user_name: str
    verification_link: str


class SendPasswordResetEmailRequest(BaseModel):
    user_name: str
    reset_link: str
    expiry_hours: int = 24


class SendKYCStatusEmailRequest(BaseModel):
    user_name: str
    status: str  # approved, pending, rejected
    message: Optional[str] = None


class SendTransactionConfirmationRequest(BaseModel):
    user_name: str
    transaction_type: str
    amount: str
    recipient: Optional[str] = None
    reference_id: Optional[str] = None


class SendLoanApprovalRequest(BaseModel):
    user_name: str
    loan_id: str
    loan_amount: str
    rate: str
    term_months: int


class EmailResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


# Admin endpoints (require admin access)
@router.post("/send-custom", response_model=EmailResponse)
async def send_custom_email(
    request: SendEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a custom email (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await ses_service.send_email(
        to_email=request.to_email,
        subject=request.subject,
        html_body=request.html_body,
        text_body=request.text_body,
        tags=request.tags
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


# Transactional email endpoints
@router.post("/send-welcome", response_model=EmailResponse)
async def send_welcome_email(
    request: SendWelcomeEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send welcome email"""
    template = get_welcome_email_template(request.user_name, request.verification_link)
    
    result = await ses_service.send_email(
        to_email=current_user.email,
        subject="Welcome to Finanza Bank",
        html_body=template['html'],
        text_body=template['text'],
        tags={'email_type': 'welcome', 'user_id': str(current_user.id)}
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


@router.post("/send-password-reset", response_model=EmailResponse)
async def send_password_reset_email(
    request: SendPasswordResetEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send password reset email"""
    template = get_password_reset_email_template(
        request.user_name,
        request.reset_link,
        request.expiry_hours
    )
    
    result = await ses_service.send_email(
        to_email=current_user.email,
        subject="Password Reset Request",
        html_body=template['html'],
        text_body=template['text'],
        tags={'email_type': 'password_reset', 'user_id': str(current_user.id)}
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


@router.post("/send-kyc-status", response_model=EmailResponse)
async def send_kyc_status_email(
    request: SendKYCStatusEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send KYC verification status email"""
    template = get_kyc_submission_template(
        request.user_name,
        request.status,
        request.message
    )
    
    result = await ses_service.send_email(
        to_email=current_user.email,
        subject="KYC Verification Status Update",
        html_body=template['html'],
        text_body=template['text'],
        tags={'email_type': 'kyc_status', 'user_id': str(current_user.id), 'kyc_status': request.status}
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


@router.post("/send-transaction-confirmation", response_model=EmailResponse)
async def send_transaction_confirmation(
    request: SendTransactionConfirmationRequest,
    current_user: User = Depends(get_current_user)
):
    """Send transaction confirmation email"""
    template = get_transaction_confirmation_template(
        request.user_name,
        request.transaction_type,
        request.amount,
        request.recipient,
        request.reference_id
    )
    
    result = await ses_service.send_email(
        to_email=current_user.email,
        subject="Transaction Confirmation",
        html_body=template['html'],
        text_body=template['text'],
        tags={
            'email_type': 'transaction_confirmation',
            'user_id': str(current_user.id),
            'transaction_type': request.transaction_type
        }
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


@router.post("/send-loan-approval", response_model=EmailResponse)
async def send_loan_approval_email(
    request: SendLoanApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """Send loan approval email"""
    template = get_loan_approval_template(
        request.user_name,
        request.loan_id,
        request.loan_amount,
        request.rate,
        request.term_months
    )
    
    result = await ses_service.send_email(
        to_email=current_user.email,
        subject="Your Loan Has Been Approved",
        html_body=template['html'],
        text_body=template['text'],
        tags={
            'email_type': 'loan_approval',
            'user_id': str(current_user.id),
            'loan_id': request.loan_id
        }
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


@router.post("/send-account-alert", response_model=EmailResponse)
async def send_account_alert_email(
    alert_type: str,
    alert_message: str,
    current_user: User = Depends(get_current_user)
):
    """Send account alert email"""
    template = get_account_alert_template(
        current_user.full_name or current_user.email,
        alert_type,
        alert_message
    )
    
    result = await ses_service.send_email(
        to_email=current_user.email,
        subject=f"Account Alert: {alert_type}",
        html_body=template['html'],
        text_body=template['text'],
        tags={
            'email_type': 'account_alert',
            'user_id': str(current_user.id),
            'alert_type': alert_type
        }
    )
    
    if result['success']:
        return EmailResponse(success=True, message_id=result['message_id'])
    else:
        return EmailResponse(success=False, error=result['message'])


# Admin statistics endpoints
@router.get("/send-quota")
async def get_send_quota(
    current_user: User = Depends(get_current_user)
):
    """Get SES send quota (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    quota = ses_service.get_send_quota()
    return quota


@router.post("/verify-email/{email}")
async def verify_email(
    email: str,
    current_user: User = Depends(get_current_user)
):
    """Verify email identity in SES (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    success = ses_service.verify_email_identity(email)
    return {"success": success, "email": email}
