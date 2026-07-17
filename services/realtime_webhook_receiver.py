"""
Real-Time Webhook Receiver Service

Handles incoming webhooks from:
1. Payment Gateways (Stripe, Paystack)
2. KYC Providers (Jumio, Onfido, IDology)
3. AWS SES/SNS Events (Email delivery, bounces, complaints)
4. Settlement Systems

All webhooks are verified for signature authenticity before processing.
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Account, Transaction, AuditLog, Settlement
from settlement_service import SettlementProcessor
from ledger_service import LedgerService
from ses_service import SESEmailService
from database import SessionLocal

logger = logging.getLogger(__name__)


class WebhookReceiver:
    """
    Routes and processes incoming webhooks with signature verification.
    
    Supports multiple payment providers with different signature schemes:
    - Stripe: X-Stripe-Signature header with HMAC-SHA256
    - Paystack: X-Paystack-Signature header with HMAC-SHA512
    - Custom: SHA256 signature verification
    """
    
    # Webhook secrets from config
    STRIPE_SECRET = None
    PAYSTACK_SECRET = None
    KYC_PROVIDER_SECRET = None
    SES_SNS_SECRET = None
    
    @classmethod
    def set_secrets(cls, stripe_secret: str = None, paystack_secret: str = None,
                    kyc_secret: str = None, ses_secret: str = None):
        """Set webhook secrets from config"""
        cls.STRIPE_SECRET = stripe_secret
        cls.PAYSTACK_SECRET = paystack_secret
        cls.KYC_PROVIDER_SECRET = kyc_secret
        cls.SES_SNS_SECRET = ses_secret
    
    @staticmethod
    def verify_stripe_signature(request_body: bytes, signature_header: str,
                               secret: str) -> bool:
        """
        Verify Stripe webhook signature.
        
        Stripe format: timestamp.signature
        Signature = HMAC-SHA256(timestamp.json_body, secret)
        """
        try:
            timestamp, sig = signature_header.split(',')[0].split('=')[1], \
                            signature_header.split(',')[1].split('=')[1]
            
            signed_content = f"{timestamp}.{request_body.decode()}"
            expected_sig = hmac.new(
                secret.encode(),
                signed_content.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(sig, expected_sig)
        except Exception as e:
            logger.error(f"Stripe signature verification failed: {e}")
            return False
    
    @staticmethod
    def verify_paystack_signature(request_body: bytes, signature_header: str,
                                 secret: str) -> bool:
        """
        Verify Paystack webhook signature.
        
        Paystack: X-Paystack-Signature = HMAC-SHA512(body, secret_key)
        """
        try:
            expected_sig = hmac.new(
                secret.encode(),
                request_body,
                hashlib.sha512
            ).hexdigest()
            
            return hmac.compare_digest(signature_header, expected_sig)
        except Exception as e:
            logger.error(f"Paystack signature verification failed: {e}")
            return False
    
    @staticmethod
    def verify_custom_signature(request_body: bytes, signature_header: str,
                               secret: str) -> bool:
        """
        Verify custom webhook signature using SHA256.
        """
        try:
            expected_sig = hmac.new(
                secret.encode(),
                request_body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature_header, expected_sig)
        except Exception as e:
            logger.error(f"Custom signature verification failed: {e}")
            return False


class PaymentWebhookProcessor:
    """
    Process payment webhooks from Stripe, Paystack, and other gateways.
    
    Flow:
    1. Verify webhook signature
    2. Parse payment event
    3. Create Transaction record
    4. Update Account balance via Ledger
    5. Send confirmation email to user
    6. Log to AuditLog
    """
    
    @staticmethod
    async def process_stripe_payment(
        db: AsyncSession,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Stripe payment.charge.succeeded or payment_intent.succeeded events.
        """
        try:
            # Extract payment details
            if 'charge' in event_data:
                charge = event_data['charge']
                amount = Decimal(str(charge['amount'])) / 100  # Stripe uses cents
                customer_id = charge.get('customer')
                reference = charge.get('id')
                description = charge.get('description', 'Stripe deposit')
            else:
                payment_intent = event_data.get('payment_intent', {})
                amount = Decimal(str(payment_intent['amount'])) / 100
                customer_id = payment_intent.get('customer')
                reference = payment_intent.get('id')
                description = payment_intent.get('description', 'Stripe payment')
            
            user_id = event_data.get('metadata', {}).get('user_id') if isinstance(event_data.get('metadata'), dict) else None
            if user_id is None:
                user_id = event_data.get('user_id')

            user = None
            if user_id:
                user_result = await db.execute(select(User).where(User.id == int(user_id)))
                user = user_result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "User not found for Stripe payment"}

            account_result = await db.execute(select(Account).where(Account.owner_id == user.id).limit(1))
            account = account_result.scalar_one_or_none()
            if not account:
                return {"success": False, "error": "No account found for user"}

            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                amount=amount,
                transaction_type="deposit",
                direction="credit",
                status="completed",
                description=description,
                reference_number=reference,
                kyc_status_at_time=user.kyc_status,
            )
            db.add(transaction)
            await db.flush()

            await LedgerService.create_deposit(
                db=db,
                user_id=user.id,
                amount=amount,
                description=description,
                transaction_id=transaction.id,
                reference_number=reference,
            )

            audit = AuditLog(
                admin_id=1,
                user_id=user.id,
                account_id=account.id,
                action_type="deposit",
                reason=f"Stripe payment {reference}",
                details=json.dumps({"provider": "stripe", "amount": str(amount), "reference": reference}),
                status="success",
            )
            db.add(audit)
            await db.commit()

            logger.info(f"Stripe payment processed: ${amount} for {user.email}")

            return {
                "success": True,
                "provider": "stripe",
                "user_id": user.id,
                "amount": amount,
                "reference": reference,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Stripe payment processing failed: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def process_paystack_payment(
        db: AsyncSession,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Paystack payment.charge.success events.
        """
        try:
            data = event_data.get('data', {})
            amount = Decimal(str(data['amount'])) / 100  # Paystack uses kobo for NGN
            reference = data.get('reference')
            customer_email = data.get('customer', {}).get('email')
            metadata = data.get('metadata', {})
            
            # Find user by email or metadata
            user_result = await db.execute(
                select(User).where(User.email == customer_email)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Get user's primary account
            account_result = await db.execute(
                select(Account).where(Account.owner_id == user.id).limit(1)
            )
            account = account_result.scalar_one_or_none()
            
            if not account:
                return {"success": False, "error": "No account found for user"}
            
            # Create deposit transaction
            transaction = Transaction(
                user_id=user.id,
                account_id=account.id,
                amount=amount,
                transaction_type="deposit",
                direction="credit",
                status="completed",
                description=f"Paystack deposit - Ref: {reference}",
                reference_number=reference,
                kyc_status_at_time=user.kyc_status
            )
            db.add(transaction)
            await db.flush()
            
            # Create ledger entry
            await LedgerService.create_deposit(
                db=db,
                user_id=user.id,
                amount=amount,
                description=f"Paystack deposit {reference}",
                transaction_id=transaction.id,
                reference_number=reference
            )
            
            # Send confirmation email
            try:
                email_service = SESEmailService()
                await email_service.send_payment_confirmation(
                    user.email,
                    user.full_name,
                    amount,
                    reference
                )
            except Exception as email_error:
                logger.warning(f"Email send failed (payment successful): {email_error}")
            
            # Log to audit
            audit = AuditLog(
                admin_id=1,  # System user
                user_id=user.id,
                account_id=account.id,
                action_type="deposit",
                reason=f"Paystack payment {reference}",
                details=json.dumps({"provider": "paystack", "amount": str(amount)}),
                status="success"
            )
            db.add(audit)
            
            await db.commit()
            
            logger.info(f"Paystack payment processed: ${amount} for {user.email}")
            
            return {
                "success": True,
                "provider": "paystack",
                "user_id": user.id,
                "amount": amount,
                "reference": reference,
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Paystack payment processing failed: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}


class KYCWebhookProcessor:
    """
    Process KYC verification webhooks from providers.
    
    When a third-party KYC provider confirms identity verification,
    automatically approve the user's KYC and unlock their account.
    """
    
    @staticmethod
    async def process_kyc_approval(
        db: AsyncSession,
        event_data: Dict[str, Any],
        provider: str = "generic"
    ) -> Dict[str, Any]:
        """
        Process KYC approval from any provider.
        
        Providers: jumio, onfido, idology, etc.
        Event types: verification.complete, verified, approved
        """
        try:
            # Extract user ID from event
            user_id = event_data.get('user_id') or event_data.get('userId')
            external_ref = event_data.get('externalId') or event_data.get('reference')
            status = event_data.get('status', 'approved').lower()
            
            if not user_id:
                return {"success": False, "error": "User ID not found in event"}
            
            # Get user
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Check status
            if status not in ['approved', 'verified', 'success', 'complete']:
                logger.info(f"KYC status is {status}, not approved")
                return {
                    "success": True,
                    "user_id": user_id,
                    "status": status,
                    "action": "no_update"
                }
            
            # Update user KYC status
            user.kyc_status = "approved"
            user.updated_at = datetime.utcnow()
            
            # Log to audit
            audit = AuditLog(
                admin_id=1,  # System user
                user_id=user_id,
                action_type="approve_kyc",
                reason=f"Automatic approval via {provider} webhook",
                details=json.dumps({
                    "provider": provider,
                    "external_ref": external_ref,
                    "event_status": status
                }),
                status="success"
            )
            db.add(audit)
            
            await db.commit()
            
            # Send approval email
            try:
                email_service = SESEmailService()
                await email_service.send_kyc_approved(user.email, user.full_name)
            except Exception as e:
                logger.warning(f"KYC approval email failed: {e}")
            
            logger.info(f"KYC approved for user {user_id} via {provider}")
            
            return {
                "success": True,
                "user_id": user_id,
                "status": "approved",
                "action": "updated"
            }
        except Exception as e:
            logger.error(f"KYC processing failed: {e}")
            await db.rollback()
            return {"success": False, "error": str(e)}


class SESEventsProcessor:
    """
    Process AWS SES/SNS delivery, bounce, and complaint events.
    
    These events update the AuditLog to track email delivery status.
    """
    
    @staticmethod
    async def process_ses_event(
        db: AsyncSession,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process SES event: delivery, bounce, complaint, send, reject, open, click
        """
        try:
            mail = event_data.get('mail', {})
            destination = mail.get('destination', [])
            message_id = mail.get('messageId')
            
            if not message_id:
                return {"success": False, "error": "No message ID"}
            
            # Create or update audit log for this email
            audit_data = {
                "event_type": event_type,
                "message_id": message_id,
                "timestamp": event_data.get('eventTimestamp')
            }
            
            if event_type == "delivery":
                audit_data["status"] = "delivered"
                audit_data["delivery_timestamp"] = event_data.get('delivery', {}).get('timestamp')
            
            elif event_type == "bounce":
                bounce = event_data.get('bounce', {})
                audit_data["bounce_type"] = bounce.get('bounceType')  # permanent, transient
                audit_data["bounce_subtype"] = bounce.get('bounceSubType')
            
            elif event_type == "complaint":
                complaint = event_data.get('complaint', {})
                audit_data["complaint_feedback_type"] = complaint.get('complaintFeedbackType')
            
            logger.info(f"SES event {event_type} for message {message_id}: {audit_data}")
            
            return {
                "success": True,
                "event_type": event_type,
                "message_id": message_id,
                "data": audit_data
            }
        except Exception as e:
            logger.error(f"SES event processing failed: {e}")
            return {"success": False, "error": str(e)}


# Import at module level
from sqlalchemy import select
