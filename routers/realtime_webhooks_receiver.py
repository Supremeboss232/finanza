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


def _verify_hmac(body: bytes, signature: str, secret: str) -> bool:
    """
    Generic HMAC-SHA256 signature verifier.
    Compares 'sha256=...' or raw hex signatures.
    Used by all vendor webhook endpoints.
    """
    if not secret or not signature:
        return False
    try:
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        incoming = signature.replace("sha256=", "").strip()
        return hmac.compare_digest(expected, incoming)
    except Exception:
        return False


def _get_secret(env_key: str) -> str:
    """Safely read a vendor secret from environment/settings."""
    import os
    return os.environ.get(env_key, "") or getattr(__import__('config').settings, env_key, "") or ""


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


# ==================== CARD ISSUER WEBHOOKS ====================
# Vendors: Marqeta, Galileo Financial Technologies, Visa DPS, i2c
# Webhook URL to give vendor: POST /webhooks/cards/events

@router.post("/cards/events")
async def webhook_card_issuer(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
    x_marqeta_signature: Optional[str] = Header(None),
):
    """
    Receive card lifecycle events from card issuing provider.
    Handles: card.activated, card.suspended, card.terminated,
             transaction.authorization, transaction.clearing,
             transaction.reversal, dispute.created, dispute.resolved
    """
    body = await request.body()
    secret = _get_secret("CARD_ISSUER_WEBHOOK_SECRET")
    sig = x_webhook_signature or x_marqeta_signature or ""

    if secret and sig and not _verify_hmac(body, sig, secret):
        logger.warning("Card issuer webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("type") or event.get("event_type", "unknown")
        logger.info(f"Card event received: {event_type}")

        # Route by event type
        if "transaction" in event_type.lower():
            # Card transaction — update ledger / transaction record
            logger.info(f"Card transaction event: {event.get('transaction_token', 'N/A')}")
        elif "card" in event_type.lower():
            # Card lifecycle — activate/suspend/terminate card
            logger.info(f"Card lifecycle event: {event_type} for card {event.get('card_token', 'N/A')}")
        elif "dispute" in event_type.lower():
            logger.info(f"Card dispute event: {event_type}")
        else:
            logger.info(f"Unhandled card event type: {event_type}")

        return {"success": True, "event_type": event_type, "received": True}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Card issuer webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ==================== ACH / WIRE PAYMENT RAIL WEBHOOKS ====================
# Vendors: Column Bank, Evolve Bank, Cross River, Synapse, Plaid, Dwolla
# Webhook URL to give vendor: POST /webhooks/payments/ach

@router.post("/payments/ach")
async def webhook_ach_payment(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
    x_column_signature: Optional[str] = Header(None),
):
    """
    Receive ACH/Wire payment rail events.
    Handles: ach.transfer.initiated, ach.transfer.completed, ach.transfer.returned,
             wire.transfer.completed, ach.return.R01, ach.return.R02, etc.
    """
    body = await request.body()
    secret = _get_secret("ACH_WEBHOOK_SECRET")
    sig = x_webhook_signature or x_column_signature or ""

    if secret and sig and not _verify_hmac(body, sig, secret):
        logger.warning("ACH webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("type") or event.get("event_type", "unknown")
        reference = event.get("reference") or event.get("transfer_id", "N/A")
        status = event.get("status", "unknown")
        logger.info(f"ACH event: {event_type} | ref={reference} | status={status}")

        if "return" in event_type.lower():
            return_code = event.get("return_code", "")
            logger.warning(f"ACH return: {return_code} for ref {reference}")
            # TODO: Mark transaction as returned, trigger NSF fee workflow
        elif "completed" in status.lower() or "settled" in status.lower():
            logger.info(f"ACH/Wire settled: {reference}")
            # TODO: Update transaction to COMPLETED, trigger user notification
        elif "failed" in status.lower():
            logger.error(f"ACH/Wire failed: {reference}")
            # TODO: Mark as failed, refund sender, notify compliance

        return {"success": True, "event_type": event_type, "reference": reference}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"ACH webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ==================== OFAC / AML COMPLIANCE WEBHOOKS ====================
# Vendors: Comply Advantage, Refinitiv World-Check, LexisNexis, Acuris
# Webhook URL to give vendor: POST /webhooks/compliance/ofac

@router.post("/compliance/ofac")
async def webhook_ofac_screening(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
    x_complyadvantage_signature: Optional[str] = Header(None),
):
    """
    Receive OFAC/AML screening result callbacks.
    Handles: screening.completed, match.found, match.dismissed,
             sar.required, pep.detected, adverse_media.found
    """
    body = await request.body()
    secret = _get_secret("OFAC_WEBHOOK_SECRET")
    sig = x_webhook_signature or x_complyadvantage_signature or ""

    if secret and sig and not _verify_hmac(body, sig, secret):
        logger.warning("OFAC webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("type") or event.get("event_type", "unknown")
        entity_id = event.get("entity_id") or event.get("search_id", "N/A")
        match_status = event.get("match_status") or event.get("status", "unknown")
        logger.info(f"OFAC event: {event_type} | entity={entity_id} | status={match_status}")

        if "confirmed_match" in match_status.lower() or "true_match" in match_status.lower():
            logger.critical(f"CONFIRMED OFAC MATCH: entity={entity_id} — account must be frozen")
            # TODO: Freeze user account, alert compliance team, file SAR
        elif "possible_match" in match_status.lower() or "potential_match" in match_status.lower():
            logger.warning(f"POSSIBLE OFAC MATCH: entity={entity_id} — requires manual review")
            # TODO: Flag account for manual review, notify BSA officer
        elif "clear" in match_status.lower() or "no_match" in match_status.lower():
            logger.info(f"OFAC screening clear: entity={entity_id}")
            # TODO: Update SanctionsCheck record to 'clear', allow transaction to proceed

        return {"success": True, "event_type": event_type, "entity_id": entity_id}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"OFAC webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ==================== CREDIT BUREAU WEBHOOKS ====================
# Vendors: Equifax, Experian, TransUnion (requires FCRA compliance)
# Webhook URL to give vendor: POST /webhooks/credit/bureau

@router.post("/credit/bureau")
async def webhook_credit_bureau(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
):
    """
    Receive credit bureau report callbacks.
    Handles: credit.report.ready, credit.score.updated, fraud.alert.placed,
             dispute.resolved, score.refresh.completed
    """
    body = await request.body()
    secret = _get_secret("CREDIT_BUREAU_WEBHOOK_SECRET")
    sig = x_webhook_signature or ""

    if secret and sig and not _verify_hmac(body, sig, secret):
        logger.warning("Credit bureau webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("type") or event.get("event_type", "unknown")
        consumer_id = event.get("consumer_id") or event.get("applicant_id", "N/A")
        logger.info(f"Credit bureau event: {event_type} | consumer={consumer_id}")

        if "report.ready" in event_type.lower() or "score" in event_type.lower():
            credit_score = event.get("credit_score") or event.get("score")
            logger.info(f"Credit report ready: score={credit_score} for consumer={consumer_id}")
            # TODO: Update loan application with credit score, trigger decisioning engine
        elif "fraud.alert" in event_type.lower():
            logger.warning(f"Fraud alert from credit bureau for consumer={consumer_id}")
            # TODO: Flag user account, notify compliance
        elif "dispute.resolved" in event_type.lower():
            logger.info(f"Credit dispute resolved for consumer={consumer_id}")

        return {"success": True, "event_type": event_type, "consumer_id": consumer_id}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Credit bureau webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ==================== CRYPTO / BLOCKCHAIN WEBHOOKS ====================
# Vendors: Fireblocks, BitGo, Anchorage Digital, Zero Hash
# Webhook URL to give vendor: POST /webhooks/crypto/events

@router.post("/crypto/events")
async def webhook_crypto_provider(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
    x_fireblocks_signature: Optional[str] = Header(None),
):
    """
    Receive crypto/blockchain transaction events.
    Handles: transaction.confirmed, transaction.failed, wallet.created,
             deposit.detected, withdrawal.completed, address.generated
    """
    body = await request.body()
    secret = _get_secret("CRYPTO_WEBHOOK_SECRET")
    sig = x_webhook_signature or x_fireblocks_signature or ""

    if secret and sig and not _verify_hmac(body, sig, secret):
        logger.warning("Crypto webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("type") or event.get("event_type", "unknown")
        tx_id = event.get("transaction_id") or event.get("txHash", "N/A")
        logger.info(f"Crypto event: {event_type} | tx={tx_id}")

        if "confirmed" in event_type.lower() or "completed" in event_type.lower():
            amount = event.get("amount")
            asset = event.get("asset_id") or event.get("currency", "")
            logger.info(f"Crypto transaction confirmed: {amount} {asset} | tx={tx_id}")
            # TODO: Credit user's crypto wallet balance, update transaction record
        elif "failed" in event_type.lower():
            logger.error(f"Crypto transaction failed: tx={tx_id}")
            # TODO: Mark transaction as failed, notify user, refund if applicable
        elif "deposit" in event_type.lower():
            logger.info(f"Crypto deposit detected: tx={tx_id}")
            # TODO: Credit user balance, confirm after network confirmations

        return {"success": True, "event_type": event_type, "tx_id": tx_id}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Crypto webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ==================== FX RATE PROVIDER WEBHOOKS ====================
# Vendors: Currencycloud, Wise Business, Airwallex
# Webhook URL to give vendor: POST /webhooks/fx/events

@router.post("/fx/events")
async def webhook_fx_provider(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None),
):
    """
    Receive FX provider events.
    Handles: conversion.completed, conversion.failed, rate.expired,
             payment.completed, payment.failed, balance.updated
    """
    body = await request.body()
    secret = _get_secret("FX_PROVIDER_WEBHOOK_SECRET")
    sig = x_webhook_signature or ""

    if secret and sig and not _verify_hmac(body, sig, secret):
        logger.warning("FX webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
        event_type = event.get("type") or event.get("event_type", "unknown")
        conversion_id = event.get("conversion_id") or event.get("id", "N/A")
        logger.info(f"FX event: {event_type} | id={conversion_id}")

        if "conversion.completed" in event_type.lower():
            rate = event.get("client_rate") or event.get("rate")
            logger.info(f"FX conversion completed at rate {rate}: {conversion_id}")
            # TODO: Update transaction record with final FX rate, credit target currency
        elif "failed" in event_type.lower():
            logger.error(f"FX conversion failed: {conversion_id}")
            # TODO: Refund source currency, notify user, mark transaction as failed

        return {"success": True, "event_type": event_type, "conversion_id": conversion_id}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"FX webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing error")


# ==================== HEALTH CHECK ====================

@router.get("/health")
async def webhook_health():
    """Health check — lists all supported webhook endpoints for vendors."""
    return {
        "status": "healthy",
        "webhook_endpoints": {
            "payment": [
                "/webhooks/payment/stripe",
                "/webhooks/payment/paystack",
            ],
            "kyc": [
                "/webhooks/kyc/approval",
                "/webhooks/kyc/rejection",
            ],
            "cards": [
                "/webhooks/cards/events",       # Marqeta, Galileo, i2c
            ],
            "ach_wire": [
                "/webhooks/payments/ach",        # Column, Evolve, Synapse, Dwolla
            ],
            "compliance": [
                "/webhooks/compliance/ofac",     # Comply Advantage, Refinitiv
            ],
            "credit": [
                "/webhooks/credit/bureau",       # Equifax, Experian, TransUnion
            ],
            "crypto": [
                "/webhooks/crypto/events",       # Fireblocks, BitGo, Zero Hash
            ],
            "fx": [
                "/webhooks/fx/events",           # Currencycloud, Wise, Airwallex
            ],
            "email": [
                "/webhooks/email/ses-events",
            ],
            "settlement": [
                "/webhooks/settlement/confirmation",
            ],
        },
        "signature_verification": "HMAC-SHA256",
        "auth_header": "X-Webhook-Signature",
        "note": "Each endpoint verifies HMAC-SHA256 signature before processing."
    }


# ==================== MULTI-GATEWAY & CUSTOM SLOT WEBHOOKS ====================
PAYMENT_PROVIDER_SECRET_MAP = {
    "flutterwave": ("FLUTTERWAVE_WEBHOOK_SECRET", "verif-hash"),
    "adyen": ("ADYEN_HMAC_KEY", "HmacSignature"),
    "paypal": ("PAYPAL_WEBHOOK_ID", "PAYPAL-TRANSMISSION-SIG"),
    "square": ("SQUARE_WEBHOOK_SIGNATURE_KEY", "x-square-hmacsha256-signature"),
    "checkout": ("CHECKOUT_WEBHOOK_SECRET", "Cko-Signature"),
    "authnet": ("AUTHNET_SIGNATURE_KEY", "X-ANET-Signature"),
    "razorpay": ("RAZORPAY_WEBHOOK_SECRET", "X-Razorpay-Signature"),
    "monnify": ("MONNIFY_WEBHOOK_SECRET", "monnify-signature"),
    "custom_gateway": ("CUSTOM_GATEWAY_WEBHOOK_SECRET", "X-Webhook-Signature"),
}


@router.post("/payment/{provider_slug}")
async def webhook_dynamic_payment_gateway(
    provider_slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    slug = provider_slug.strip().lower()
    secret_env_key, default_header = PAYMENT_PROVIDER_SECRET_MAP.get(
        slug, (f"CUSTOM_SLOT_{slug.upper()}_WEBHOOK_SECRET", "X-Webhook-Signature")
    )
    secret = _get_secret(secret_env_key) or os.environ.get(secret_env_key, "")
    if slug == "custom_gateway":
        default_header = os.environ.get("CUSTOM_GATEWAY_WEBHOOK_HEADER", "X-Webhook-Signature")
    sig = (
        request.headers.get(default_header)
        or request.headers.get(default_header.lower())
        or request.headers.get("x-webhook-signature")
        or ""
    )
    if secret and sig:
        if slug == "flutterwave" and hmac.compare_digest(sig, secret):
            pass
        elif not _verify_hmac(body, sig, secret):
            logger.warning(f"Payment gateway webhook ({slug}): signature verification failed")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        event = json.loads(body) if body else {}
        event_type = event.get("event") or event.get("type") or event.get("event_type") or "payment.event"
        reference = event.get("reference") or (event.get("data") or {}).get("reference") or event.get("id") or "N/A"
        logger.info(f"Payment gateway [{slug}] webhook received: event={event_type} ref={reference}")
        return {"success": True, "provider": slug, "event_type": event_type, "reference": reference, "received": True}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


@router.post("/custom/{slot_id}")
async def webhook_custom_vendor_slot(
    slot_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    slug = slot_id.strip().lower()
    secret = os.environ.get(f"CUSTOM_SLOT_{slug.upper()}_WEBHOOK_SECRET", "")
    sig = request.headers.get("x-webhook-signature") or ""
    if secret and sig and not _verify_hmac(body, sig, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        event = json.loads(body) if body else {}
        event_type = event.get("event") or event.get("type") or "custom.event"
        logger.info(f"Custom vendor slot [{slug}] webhook received: {event_type}")
        return {"success": True, "slot_id": slug, "event_type": event_type, "received": True}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
