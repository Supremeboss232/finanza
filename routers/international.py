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


@international_router.get("/transfers")
async def list_international_transfers(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """List international transfers for the current user, optionally filtered by status."""
    from models import Transaction
    from sqlalchemy import select

    stmt = select(Transaction).where(
        (Transaction.user_id == current_user.id)
        & (Transaction.transaction_type.in_(["international_transfer", "wire_transfer", "international", "swift"]))
    )
    if status:
        if status == "pending":
            stmt = stmt.where(Transaction.status.in_(["pending", "pending_approval", "processing"]))
        else:
            stmt = stmt.where(Transaction.status == status)
    stmt = stmt.order_by(Transaction.created_at.desc()).limit(50)
    result = await db_session.execute(stmt)
    txns = result.scalars().all()
    items = []
    for t in txns:
        desc = t.description or "International Transfer"
        recipient_name = desc
        recipient_country = "INTL"
        if "International transfer to " in desc:
            body = desc.split("International transfer to ", 1)[1]
            if " (" in body and ")" in body:
                recipient_name = body.split(" (", 1)[0].strip()
                recipient_country = body.split(" (", 1)[1].split(")", 1)[0].strip()
            elif " - " in body:
                parts = body.split(" - ", 1)
                recipient_country = parts[0].strip()
                recipient_name = parts[1].strip()
        elif "International Transfer to " in desc:
            body = desc.split("International Transfer to ", 1)[1]
            if " (" in body and ")" in body:
                recipient_name = body.split(" (", 1)[0].strip()
                recipient_country = body.split(" (", 1)[1].split(")", 1)[0].strip()

        items.append({
            "id": t.id,
            "amount": abs(float(t.amount or 0)),
            "currency": getattr(t, "currency", "USD") or "USD",
            "status": t.status,
            "recipient_name": recipient_name,
            "recipient_country": recipient_country,
            "description": desc,
            "reference": getattr(t, "reference_number", None) or f"INTL-{t.id}",
            "reference_number": getattr(t, "reference_number", None) or f"INTL-{t.id}",
            "step_1_completed": True,
            "step_2_completed": t.status in ("processing", "pending_approval", "completed"),
            "step_3_completed": t.status in ("in_transit", "completed"),
            "estimated_delivery": "1-3 business days",
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return items


@international_router.get("/stats")
async def get_international_transfer_stats(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """Get summary statistics of international transfers for the current user."""
    from models import Transaction, UserSettings
    from sqlalchemy import select
    import json

    stmt = select(Transaction).where(
        (Transaction.user_id == current_user.id)
        & (Transaction.transaction_type.in_(["international_transfer", "wire_transfer", "international", "swift"]))
    )
    result = await db_session.execute(stmt)
    txns = result.scalars().all()
    pending = [t for t in txns if t.status in ("pending", "pending_approval", "processing")]
    completed = [t for t in txns if t.status == "completed"]
    total_used = round(sum(abs(float(t.amount or 0)) for t in txns if t.status != "failed"), 2)

    saved_count = 0
    try:
        us_res = await db_session.execute(select(UserSettings).where(UserSettings.user_id == current_user.id))
        us = us_res.scalar_one_or_none()
        if us and us.preferences:
            prefs = json.loads(us.preferences)
            saved_count = len(prefs.get("saved_recipients", []))
    except Exception:
        pass

    return {
        "monthly_limit": 100000.0,
        "limit_used": total_used,
        "pending_count": len(pending),
        "completed_count": len(completed),
        "this_month_transfers": len(txns),
        "this_month_amount": total_used,
        "total_sent": round(sum(abs(float(t.amount or 0)) for t in completed), 2),
        "countries_count": 140,
        "recipient_count": saved_count,
    }
