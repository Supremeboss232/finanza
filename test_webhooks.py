#!/usr/bin/env python3
"""
Real-Time Webhook Testing Suite

Run this script to test all webhook endpoints locally with valid signatures.
"""

import requests
import hmac
import hashlib
import json
import uuid
from typing import Dict, Any
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
WEBHOOK_SECRETS = {
    "stripe": "test-stripe-secret",
    "paystack": "test-paystack-secret",
    "kyc": "your-kyc-webhook-secret-change-in-env",
    "ses": "test-ses-secret"
}

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_section(title: str):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title:^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg: str):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg: str):
    print(f"{YELLOW}→ {msg}{RESET}")

def create_stripe_signature(payload: str, secret: str, timestamp: str = None) -> str:
    """Create Stripe signature in format: t=timestamp,v1=signature"""
    import time
    timestamp = timestamp or str(int(time.time()))
    signed_content = f"{timestamp}.{payload}"
    signature = hmac.new(
        secret.encode(),
        signed_content.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"

def create_paystack_signature(payload: str, secret: str) -> str:
    """Create Paystack signature: HMAC-SHA512"""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha512
    ).hexdigest()

def create_custom_signature(payload: str, secret: str) -> str:
    """Create custom signature: HMAC-SHA256"""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

def test_health_check():
    """Test webhook health endpoint"""
    print_section("Health Check Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/webhooks/health", timeout=5)
        
        if response.status_code == 200:
            print_success("Health check endpoint is responding")
            data = response.json()
            print(f"  Status: {data.get('status')}")
            print(f"  Webhooks available: {len(data.get('webhook_types', []))}")
            for webhook_type in data.get('webhook_types', []):
                print(f"    • {webhook_type}")
        else:
            print_error(f"Health check failed with status {response.status_code}")
    except Exception as e:
        print_error(f"Health check error: {e}")

def test_stripe_webhook():
    """Test Stripe payment webhook"""
    print_section("Stripe Payment Webhook")
    
    payload_dict = {
        "type": "charge.succeeded",
        "id": f"evt_{uuid.uuid4().hex[:24]}",
        "data": {
            "object": {
                "id": f"ch_{uuid.uuid4().hex[:24]}",
                "amount": 5000,
                "currency": "usd",
                "customer": f"cus_{uuid.uuid4().hex[:24]}",
                "description": "Test charge from webhook test",
                "status": "succeeded",
                "paid": True
            }
        }
    }
    
    payload = json.dumps(payload_dict)
    signature = create_stripe_signature(payload, WEBHOOK_SECRETS["stripe"])
    
    print_info(f"Event: charge.succeeded")
    print_info(f"Amount: $50.00")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/payment/stripe",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Stripe-Signature": signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("Stripe webhook processed successfully")
            print(f"  Response: {response.json()}")
        else:
            print_error(f"Stripe webhook failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print_error(f"Stripe webhook error: {e}")

def test_paystack_webhook():
    """Test Paystack payment webhook"""
    print_section("Paystack Payment Webhook")
    
    payload_dict = {
        "event": "charge.success",
        "data": {
            "id": 123456,
            "reference": f"ref_{uuid.uuid4().hex[:16]}",
            "amount": 50000,  # In kobo (50000 kobo = ₦500)
            "currency": "NGN",
            "status": "success",
            "customer": {
                "id": 123,
                "customer_code": f"CUS_{uuid.uuid4().hex[:16]}",
                "email": f"user{uuid.uuid4().hex[:8]}@example.com"
            }
        }
    }
    
    payload = json.dumps(payload_dict)
    signature = create_paystack_signature(payload, WEBHOOK_SECRETS["paystack"])
    
    print_info(f"Event: charge.success")
    print_info(f"Amount: ₦500.00")
    print_info(f"Reference: {payload_dict['data']['reference']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/payment/paystack",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Paystack-Signature": signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("Paystack webhook processed successfully")
            print(f"  Response: {response.json()}")
        else:
            print_error(f"Paystack webhook failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print_error(f"Paystack webhook error: {e}")

def test_kyc_approval_webhook():
    """Test KYC approval webhook"""
    print_section("KYC Approval Webhook")
    
    user_id = str(uuid.uuid4())
    payload_dict = {
        "user_id": user_id,
        "status": "approved",
        "provider": "jumio",
        "externalId": f"jumio_{uuid.uuid4().hex[:16]}",
        "verification_level": "id_verification",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    payload = json.dumps(payload_dict)
    signature = create_custom_signature(payload, WEBHOOK_SECRETS["kyc"])
    
    print_info(f"Event: KYC Verification Complete")
    print_info(f"User ID: {user_id}")
    print_info(f"Status: approved")
    print_info(f"Provider: jumio")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/kyc/approval",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("KYC approval webhook processed successfully")
            print(f"  Response: {response.json()}")
        else:
            print_error(f"KYC approval webhook failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print_error(f"KYC approval webhook error: {e}")

def test_kyc_rejection_webhook():
    """Test KYC rejection webhook"""
    print_section("KYC Rejection Webhook")
    
    user_id = str(uuid.uuid4())
    payload_dict = {
        "user_id": user_id,
        "status": "rejected",
        "provider": "onfido",
        "rejection_reason": "Document verification failed - image quality too low",
        "externalId": f"onfido_{uuid.uuid4().hex[:16]}",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    payload = json.dumps(payload_dict)
    signature = create_custom_signature(payload, WEBHOOK_SECRETS["kyc"])
    
    print_info(f"Event: KYC Verification Rejected")
    print_info(f"User ID: {user_id}")
    print_info(f"Reason: {payload_dict['rejection_reason']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/kyc/rejection",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("KYC rejection webhook processed successfully")
            print(f"  Response: {response.json()}")
        else:
            print_error(f"KYC rejection webhook failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print_error(f"KYC rejection webhook error: {e}")

def test_ses_events_webhook():
    """Test SES email delivery events webhook"""
    print_section("SES Email Events Webhook")
    
    message_id = f"msg_{uuid.uuid4().hex[:24]}"
    payload_dict = {
        "Type": "Notification",
        "Message": json.dumps({
            "eventType": "Delivery",
            "mail": {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "noreply@finanzabank.com",
                "sourceArn": f"arn:aws:ses:eu-north-1:123456789012:identity/finanzabank.com",
                "sendingAccountId": "123456789012",
                "messageId": message_id,
                "destination": ["user@example.com"],
                "headersTruncated": False,
                "headers": [
                    {"name": "From", "value": "Finanza Bank <noreply@finanzabank.com>"},
                    {"name": "Subject", "value": "Payment Confirmation"}
                ],
                "commonHeaders": {
                    "from": ["noreply@finanzabank.com"],
                    "to": ["user@example.com"],
                    "messageId": message_id
                }
            },
            "delivery": {
                "timestamp": datetime.utcnow().isoformat(),
                "processingTimeMillis": 2478,
                "recipients": ["user@example.com"],
                "smtpResponse": "250 2.0.0 OK",
                "remoteMtaIp": "203.0.113.1",
                "bounceType": "Undetermined",
                "bounceSubType": "Undetermined"
            }
        })
    }
    
    payload = json.dumps(payload_dict)
    
    print_info(f"Event: Email Delivered")
    print_info(f"Message ID: {message_id}")
    print_info(f"Recipient: user@example.com")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/email/ses-events",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": create_custom_signature(payload, WEBHOOK_SECRETS["ses"])
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("SES events webhook processed successfully")
            print(f"  Response: {response.json()}")
        else:
            print_error(f"SES events webhook failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print_error(f"SES events webhook error: {e}")

def test_settlement_webhook():
    """Test settlement confirmation webhook"""
    print_section("Settlement Confirmation Webhook")
    
    settlement_id = str(uuid.uuid4())
    payload_dict = {
        "settlement_id": settlement_id,
        "status": "completed",
        "reference": f"SWIFT-{uuid.uuid4().hex[:12].upper()}",
        "amount": 150000.50,
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat(),
        "transaction_count": 42
    }
    
    payload = json.dumps(payload_dict)
    signature = create_custom_signature(payload, WEBHOOK_SECRETS["paystack"])
    
    print_info(f"Event: Settlement Completed")
    print_info(f"Settlement ID: {settlement_id}")
    print_info(f"Amount: $150,000.50")
    print_info(f"Reference: {payload_dict['reference']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/settlement/confirmation",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print_success("Settlement webhook processed successfully")
            print(f"  Response: {response.json()}")
        else:
            print_error(f"Settlement webhook failed with status {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print_error(f"Settlement webhook error: {e}")

def main():
    print(f"\n{BLUE}{'#'*60}{RESET}")
    print(f"{BLUE}Real-Time Webhook Testing Suite{RESET}")
    print(f"{BLUE}{'#'*60}{RESET}")
    
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Test Mode: Local Development")
    
    # Run all tests
    test_health_check()
    test_stripe_webhook()
    test_paystack_webhook()
    test_kyc_approval_webhook()
    test_kyc_rejection_webhook()
    test_ses_events_webhook()
    test_settlement_webhook()
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'Testing Complete':^60}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

if __name__ == "__main__":
    main()
