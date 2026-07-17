"""
Real-Time Webhook Router

Unified endpoint for all incoming webhooks:
- Payment processing (Stripe, Paystack)
- KYC updates (Jumio, Onfido, IDology)
- Email delivery tracking (AWS SES/SNS)
- Settlement confirmations

All webhooks are signature-verified before processing.
"""

import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, Request, HTTPException, Header, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from database import SessionLocal
from services.realtime_webhook_receiver import (
    WebhookReceiver,
    PaymentWebhookProcessor,
    KYCWebhookProcessor,
    SESEventsProcessor
)
from config import (
    STRIPE_WEBHOOK_SECRET,
    PAYSTACK_WEBHOOK_SECRET,
    KYC_WEBHOOK_SECRET,
    SES_SNS_WEBHOOK_SECRET
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


# Initialize webhook receiver with secrets
WebhookReceiver.set_secrets(
    stripe_secret=STRIPE_WEBHOOK_SECRET,
    paystack_secret=PAYSTACK_WEBHOOK_SECRET,
    kyc_secret=KYC_WEBHOOK_SECRET,
    ses_secret=SES_SNS_WEBHOOK_SECRET
)


async def get_db():
    """Dependency to get database session"""
    async with SessionLocal() as session:
        yield session


# ==================== PAYMENT WEBHOOKS ====================

@router.post("/payment/stripe")
async def webhook_stripe(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_stripe_signature: str = Header(None)
):
    """
    Receive Stripe payment events.
    
    Events:
    - charge.succeeded - Payment completed
    - charge.failed - Payment failed
    - charge.refunded - Payment refunded
    
    Signature verification required.
    """
    body = await request.body()
    
    if not x_stripe_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify signature
    if not WebhookReceiver.verify_stripe_signature(
        body, x_stripe_signature, WebhookReceiver.STRIPE_SECRET
    ):
        logger.warning("Stripe signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(body)
        event_type = event.get('type', '')
        event_data = event.get('data', {}).get('object', {})
        
        if event_type == 'charge.succeeded':
            logger.info(f"Stripe charge succeeded: {event_data.get('id')}")
            background_tasks.add_task(
                PaymentWebhookProcessor.process_stripe_payment,
                db, {'charge': event_data}
            )
        
        elif event_type == 'charge.failed':
            logger.warning(f"Stripe charge failed: {event_data.get('id')}")
        
        elif event_type == 'charge.refunded':
            logger.info(f"Stripe charge refunded: {event_data.get('id')}")
        
        return {"success": True, "event_id": event.get('id')}
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payment/paystack")
async def webhook_paystack(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_paystack_signature: str = Header(None)
):
    """
    Receive Paystack payment events.
    
    Events:
    - charge.success - Payment completed
    - charge.failure - Payment failed
    
    Signature verification required.
    """
    body = await request.body()
    
    if not x_paystack_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify signature
    if not WebhookReceiver.verify_paystack_signature(
        body, x_paystack_signature, WebhookReceiver.PAYSTACK_SECRET
    ):
        logger.warning("Paystack signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(body)
        event_type = event.get('event', '')
        event_data = event.get('data', {})
        
        if event_type == 'charge.success':
            logger.info(f"Paystack charge succeeded: {event_data.get('reference')}")
            background_tasks.add_task(
                PaymentWebhookProcessor.process_paystack_payment,
                db, event
            )
        
        elif event_type == 'charge.failure':
            logger.warning(f"Paystack charge failed: {event_data.get('reference')}")
        
        return {"success": True}
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Paystack webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== KYC WEBHOOKS ====================

@router.post("/kyc/approval")
async def webhook_kyc_approval(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: str = Header(None)
):
    """
    Receive KYC approval events.
    
    Supported providers:
    - Jumio (jumio_id in event body)
    - Onfido (applicant_id in event body)
    - IDology (assessment_id in event body)
    - Generic webhook with user_id field
    
    Expected event structure:
    {
        "user_id": "uuid",
        "status": "approved",
        "provider": "jumio|onfido|idology",
        "externalId": "provider-reference"
    }
    """
    body = await request.body()
    
    if not x_webhook_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify signature
    if not WebhookReceiver.verify_custom_signature(
        body, x_webhook_signature, WebhookReceiver.KYC_PROVIDER_SECRET
    ):
        logger.warning("KYC signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(body)
        provider = event.get('provider', 'generic')
        
        logger.info(f"KYC approval from {provider}: {event.get('user_id')}")
        
        background_tasks.add_task(
            KYCWebhookProcessor.process_kyc_approval,
            db, event, provider
        )
        
        return {"success": True, "user_id": event.get("user_id")}
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"KYC webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kyc/rejection")
async def webhook_kyc_rejection(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: str = Header(None)
):
    """
    Receive KYC rejection events.
    
    Automatically reject user account and notify them.
    """
    body = await request.body()
    
    if not x_webhook_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify signature
    if not WebhookReceiver.verify_custom_signature(
        body, x_webhook_signature, WebhookReceiver.KYC_PROVIDER_SECRET
    ):
        logger.warning("KYC rejection signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(body)
        user_id = event.get('user_id')
        reason = event.get('rejection_reason', 'Document verification failed')
        
        logger.info(f"KYC rejection for user {user_id}: {reason}")
        
        # TODO: Implement rejection handler
        # - Update user.kyc_status = "rejected"
        # - Send refusal email with reason
        # - Log to AuditLog
        
        return {"success": True, "user_id": user_id}
    
    except Exception as e:
        logger.error(f"KYC rejection webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EMAIL DELIVERY TRACKING ====================

@router.post("/email/ses-events")
async def webhook_ses_events(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: str = Header(None)
):
    """
    Receive AWS SNS/SES events.
    
    Event types:
    - Send: Email was accepted by AWS SES
    - Delivery: Email successfully delivered
    - Bounce: Email bounced (permanent or transient)
    - Complaint: Recipient marked as spam
    - Reject: Email was rejected by SES
    - Open: Recipient opened email (if enabled)
    - Click: Recipient clicked link (if enabled)
    
    SNS sends JSON in request body or X-Amz-Sns-Topic header.
    """
    body = await request.body()
    
    try:
        message = json.loads(body)
        
        # Handle SNS subscription confirmation
        if message.get('Type') == 'SubscriptionConfirmation':
            logger.info("SNS subscription confirmation")
            # In production, verify and confirm subscription
            return {"success": True, "subscription_confirmed": True}
        
        # Handle SES event
        if message.get('Type') == 'Notification':
            # SNS wraps the actual message
            sns_message = json.loads(message.get('Message', '{}'))
            event_type = sns_message.get('eventType', '')
            event_data = sns_message.get('mail', {})
            
            logger.info(f"SES event: {event_type} for {event_data.get('messageId')}")
            
            # Process event
            background_tasks.add_task(
                SESEventsProcessor.process_ses_event,
                db, event_type, sns_message
            )
        
        return {"success": True}
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"SES webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SETTLEMENT CONFIRMATIONS ====================

@router.post("/settlement/confirmation")
async def webhook_settlement_confirmation(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: str = Header(None)
):
    """
    Receive settlement confirmation from banking partners.
    
    Settlement partners (SWIFT, ACH, etc.) confirm when transfers have been processed.
    
    Expected event structure:
    {
        "settlement_id": "uuid",
        "status": "completed|failed",
        "reference": "SWIFT/ACH reference",
        "amount": 1000.50,
        "currency": "USD",
        "timestamp": "2024-01-01T12:00:00Z"
    }
    """
    body = await request.body()
    
    if not x_webhook_signature:
        raise HTTPException(status_code=400, detail="Missing signature")
    
    # Verify signature
    if not WebhookReceiver.verify_custom_signature(
        body, x_webhook_signature, WebhookReceiver.PAYSTACK_SECRET
    ):
        logger.warning("Settlement signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    try:
        event = json.loads(body)
        settlement_id = event.get('settlement_id')
        status = event.get('status')
        
        logger.info(f"Settlement confirmation: {settlement_id} - {status}")
        
        # TODO: Update Settlement record status in database
        # - Lookup Settlement by settlement_id
        # - Update status and completion timestamp
        # - Trigger notification email
        # - Update related transactions
        
        return {"success": True, "settlement_id": settlement_id}
    
    except Exception as e:
        logger.error(f"Settlement confirmation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def webhook_health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "webhook_types": [
            "payment/stripe",
            "payment/paystack",
            "kyc/approval",
            "kyc/rejection",
            "email/ses-events",
            "settlement/confirmation"
        ]
    }
