"""International transfer and compliance endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, SessionDep
from models import User
from international_transfer_service import InternationalTransferService
import logging

logger = logging.getLogger(__name__)

international_router = APIRouter(
    prefix="/api/international",
    tags=["international_transfers"],
)


@international_router.get("/country-risk/{country_code}")
async def get_country_risk(
    country_code: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get risk assessment for a specific country.

    Returns risk tier, level, and KYC requirements.
    """
    result = await InternationalTransferService.assess_country_risk(country_code)
    return result


@international_router.post("/sanctions-check")
async def check_sanctions(
    full_name: str,
    country_code: str,
    current_user: User = Depends(get_current_user),
):
    """
    Screen a person against sanctions lists.

    Returns whether person is sanctioned and risk level.
    """
    result = await InternationalTransferService.screen_sanctions(full_name, country_code)
    return result


@international_router.post("/transfer-rules")
async def get_transfer_rules(
    country_code: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get transfer rules, limits, and requirements for a country.

    Returns daily limit, KYC requirements, fees, and processing time.
    """
    result = await InternationalTransferService.get_international_transfer_rules(country_code)
    return result


@international_router.post("/transfer", status_code=status.HTTP_201_CREATED)
async def create_international_transfer(
    recipient_country: str,
    recipient_name: str,
    recipient_account: str,
    amount: float,
    purpose: str,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """
    Create an international transfer with compliance checks.

    The transfer will be created in pending_approval status pending admin review.
    Compliance data (sanctions screening, country risk) is attached to the audit log.
    """
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    result = await InternationalTransferService.create_international_transfer(
        db=db_session,
        sender_id=current_user.id,
        recipient_country=recipient_country,
        recipient_name=recipient_name,
        recipient_account=recipient_account,
        amount=Decimal(str(amount)),
        purpose=purpose,
        admin_notes=None,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@international_router.get("/compliance-data/{transaction_id}")
async def get_transfer_compliance_data(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """
    Get compliance documentation for an international transfer.

    Shows country risk, sanctions screening, and audit trail.
    """
    from models import Transaction, AuditLog
    from sqlalchemy import select

    # Verify user owns this transaction
    tx = await db_session.get(Transaction, transaction_id)
    if not tx or tx.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Get associated audit log
    result = await db_session.execute(
        select(AuditLog)
        .where(
            (AuditLog.user_id == current_user.id)
            & (AuditLog.action_type == "international_transfer")
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    audit_log = result.scalar_one_or_none()

    if not audit_log:
        raise HTTPException(status_code=404, detail="Compliance data not found")

    import json
    details = json.loads(audit_log.details) if audit_log.details else {}

    return {
        "transaction_id": transaction_id,
        "transaction_status": tx.status,
        "compliance_data": details.get("compliance_data", {}),
        "recipient_country": details.get("recipient_country"),
        "recipient_name": details.get("recipient_name"),
        "amount": details.get("amount"),
        "audit_log_id": audit_log.id,
        "created_at": audit_log.created_at.isoformat() if audit_log.created_at else None,
    }
