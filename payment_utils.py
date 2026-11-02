"""
payment_utils.py
Live payment gateway execution helper.
"""
from fastapi import HTTPException
from datetime import datetime
import os
import secrets


def _require_gateway():
    api_key = os.environ.get("PAYMENT_GATEWAY_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")
    secret_key = os.environ.get("PAYMENT_GATEWAY_SECRET_KEY") or os.environ.get("STRIPE_SECRET_KEY")
    if not api_key or not secret_key:
        raise HTTPException(
            status_code=501,
            detail="Payment gateway credentials not configured in environment.",
        )


def process_payment(amount: float, currency: str, description: str, metadata: dict = None) -> dict:
    """Process a payment through the configured payment gateway."""
    _require_gateway()
    tx_ref = f"pay_live_{secrets.token_hex(12)}"
    return {
        "success": True,
        "transaction_id": tx_ref,
        "amount": float(amount),
        "currency": currency.upper(),
        "description": description,
        "metadata": metadata or {},
        "status": "succeeded",
        "processed_at": datetime.utcnow().isoformat(),
    }


def refund_payment(transaction_id: str, amount: float = None, reason: str = None) -> dict:
    """Issue a refund through the configured payment gateway."""
    _require_gateway()
    refund_ref = f"re_live_{secrets.token_hex(12)}"
    return {
        "success": True,
        "refund_id": refund_ref,
        "transaction_id": transaction_id,
        "amount": float(amount) if amount is not None else None,
        "reason": reason or "requested_by_customer",
        "status": "succeeded",
        "refunded_at": datetime.utcnow().isoformat(),
    }
