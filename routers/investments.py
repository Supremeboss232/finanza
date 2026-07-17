from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from deps import CurrentUserDep, SessionDep
from investment_management_service import InvestmentManagementService

router = APIRouter(prefix="/investments", tags=["investments"])


@router.post("/create")
async def create_investment(
    investment_type: str,
    amount: float,
    annual_return_rate: Optional[float] = None,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Create a new investment."""
    result = await InvestmentManagementService.create_investment(
        db=db_session,
        user_id=current_user.id,
        investment_type=investment_type,
        amount=Decimal(str(amount)),
        annual_return_rate=Decimal(str(annual_return_rate)) if annual_return_rate else None,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/accrue-returns/{investment_id}")
async def accrue_investment_returns(
    investment_id: int,
    days_elapsed: int = 1,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Accrue returns on an investment (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await InvestmentManagementService.accrue_returns(
        db=db_session,
        investment_id=investment_id,
        days_elapsed=days_elapsed,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/rebalance")
async def rebalance_portfolio(
    target_profile: str = "moderate",
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Rebalance user's investment portfolio."""
    result = await InvestmentManagementService.rebalance_portfolio(
        db=db_session,
        user_id=current_user.id,
        target_profile=target_profile,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/liquidate/{investment_id}")
async def liquidate_investment(
    investment_id: int,
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Liquidate an investment."""
    result = await InvestmentManagementService.liquidate_investment(
        db=db_session,
        investment_id=investment_id,
        user_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/portfolio-summary")
async def get_portfolio_summary(
    current_user: CurrentUserDep = None,
    db_session: SessionDep = None,
):
    """Get user's complete portfolio summary."""
    result = await InvestmentManagementService.get_portfolio_summary(
        db=db_session,
        user_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# Legacy route for backward compatibility
investments_router = router
