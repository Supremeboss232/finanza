"""
Payment Processing Router

Endpoints for internal payment processing:
- Initiate payments
- Settle payments
- Cancel payments
- Payment status
- Payment history
- Reconciliation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from deps import CurrentUserDep, SessionDep
from payment_processing_service import PaymentProcessingService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/initiate")
async def initiate_payment(
    recipient_user_id: int,
    amount: float,
    payment_type: str,
    description: str = "",
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Initiate a payment to another user."""
    result = await PaymentProcessingService.initiate_payment(
        db=db_session,
        user_id=current_user.id,
        recipient_user_id=recipient_user_id,
        amount=Decimal(str(amount)),
        payment_type=payment_type,
        description=description,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/settle/{transaction_id}")
async def settle_payment(
    transaction_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Settle a pending payment (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await PaymentProcessingService.settle_payment(
        db=db_session,
        transaction_id=transaction_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/cancel/{transaction_id}")
async def cancel_payment(
    transaction_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Cancel a pending payment."""
    result = await PaymentProcessingService.cancel_payment(
        db=db_session,
        transaction_id=transaction_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/status/{transaction_id}")
async def get_payment_status(
    transaction_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Get payment status."""
    result = await PaymentProcessingService.get_payment_status(
        db=db_session,
        transaction_id=transaction_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/history")
async def get_payment_history(
    limit: int = 50,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Get user's payment history."""
    result = await PaymentProcessingService.get_user_payment_history(
        db=db_session,
        user_id=current_user.id,
        limit=limit,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/reconcile")
async def reconcile_payments(
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Reconcile all payments (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await PaymentProcessingService.reconcile_payments(
        db=db_session,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
