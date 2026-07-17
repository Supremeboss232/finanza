"""Mobile deposit endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from deps import get_current_user, get_current_admin_user, SessionDep
from models import User
from mobile_deposits_service import MobileDepositsService
import logging

logger = logging.getLogger(__name__)

deposits_router = APIRouter(
    prefix="/api/deposits",
    tags=["mobile_deposits"],
)


@deposits_router.post("/mobile", status_code=status.HTTP_201_CREATED)
async def create_mobile_deposit(
    amount: float,
    check_number: str,
    issuer_name: str,
    bank_routing: str,
    bank_account: str,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """Create a new mobile deposit submission."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    result = await MobileDepositsService.create_deposit(
        db=db_session,
        user_id=current_user.id,
        amount=Decimal(str(amount)),
        check_number=check_number,
        issuer_name=issuer_name,
        bank_routing=bank_routing,
        bank_account=bank_account,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@deposits_router.post("/mobile/{deposit_id}/upload-image")
async def add_deposit_image(
    deposit_id: int,
    image_side: str,  # "front" or "back"
    image_url: str,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """Upload front or back image of check."""
    result = await MobileDepositsService.add_deposit_image(
        db=db_session,
        deposit_id=deposit_id,
        image_side=image_side,
        image_url=image_url,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@deposits_router.get("/mobile/pending")
async def get_pending_deposits(
    current_user: User = Depends(get_current_admin_user),
    db_session: SessionDep = None,
):
    """Get all pending deposits awaiting admin review."""
    result = await MobileDepositsService.get_pending_deposits(db_session)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@deposits_router.post("/mobile/{deposit_id}/approve")
async def approve_deposit(
    deposit_id: int,
    reviewer_notes: str = "",
    current_user: User = Depends(get_current_admin_user),
    db_session: SessionDep = None,
):
    """Admin approves a mobile deposit and settles funds."""
    result = await MobileDepositsService.approve_deposit(
        db=db_session,
        deposit_id=deposit_id,
        admin_id=current_user.id,
        reviewer_notes=reviewer_notes,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@deposits_router.post("/mobile/{deposit_id}/reject")
async def reject_deposit(
    deposit_id: int,
    rejection_reason: str,
    current_user: User = Depends(get_current_admin_user),
    db_session: SessionDep = None,
):
    """Admin rejects a mobile deposit."""
    result = await MobileDepositsService.reject_deposit(
        db=db_session,
        deposit_id=deposit_id,
        admin_id=current_user.id,
        rejection_reason=rejection_reason,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@deposits_router.get("/mobile/stats")
async def get_mobile_deposit_stats(
    current_user: User = Depends(get_current_admin_user),
    db_session: SessionDep = None,
):
    """Get mobile deposit statistics."""
    result = await MobileDepositsService.get_deposit_stats(db_session)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result
