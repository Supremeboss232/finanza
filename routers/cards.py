from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from deps import CurrentUserDep, SessionDep
from card_processing_service import CardProcessingService

router = APIRouter(prefix="/cards", tags=["cards"])


@router.post("/request")
async def request_card(
    card_type: str,
    billing_address: str,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Request a new card."""
    result = await CardProcessingService.request_card(
        db=db_session,
        user_id=current_user.id,
        card_type=card_type,
        billing_address=billing_address,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/approve/{card_id}")
async def approve_card_request(
    card_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Admin approves and issues a card."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await CardProcessingService.approve_card_request(
        db=db_session,
        card_id=card_id,
        admin_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/activate/{card_id}")
async def activate_card(
    card_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """User activates their card."""
    result = await CardProcessingService.activate_card(
        db=db_session,
        card_id=card_id,
        user_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/authorize")
async def authorize_card_transaction(
    card_id: int,
    amount: float,
    merchant: str,
    description: str = "",
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Authorize a card transaction."""
    result = await CardProcessingService.authorize_transaction(
        db=db_session,
        card_id=card_id,
        amount=Decimal(str(amount)),
        merchant=merchant,
        description=description,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/settle")
async def settle_card_transaction(
    card_id: int,
    auth_code: str,
    amount: float,
    merchant: str,
    description: str = "",
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Settle an authorized card transaction."""
    result = await CardProcessingService.settle_transaction(
        db=db_session,
        card_id=card_id,
        auth_code=auth_code,
        amount=Decimal(str(amount)),
        merchant=merchant,
        description=description,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/pay-balance/{card_id}")
async def pay_credit_card_balance(
    card_id: int,
    amount: float,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Pay down credit card balance."""
    result = await CardProcessingService.pay_credit_card_balance(
        db=db_session,
        card_id=card_id,
        payment_amount=Decimal(str(amount)),
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/details/{card_id}")
async def get_card_details(
    card_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Get card details."""
    result = await CardProcessingService.get_card_details(
        db=db_session,
        card_id=card_id,
        user_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/my-cards")
async def get_my_cards(
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Get user's cards."""
    result = await CardProcessingService.get_user_cards(
        db=db_session,
        user_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# Legacy route for backward compatibility
cards_router = router
