from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from decimal import Decimal

from deps import CurrentUserDep, SessionDep
from models import User
from loan_origination_service import LoanOriginationService
from rbac import require_permission

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("/apply")
async def apply_for_loan(
    loan_type: str,
    amount: float,
    term_months: int,
    purpose: str,
    current_user: CurrentUserDep,
    db_session: SessionDep,
):
    """Submit a loan application."""
    result = await LoanOriginationService.submit_application(
        db=db_session,
        user_id=current_user.id,
        loan_type=loan_type,
        amount=Decimal(str(amount)),
        term_months=term_months,
        purpose=purpose,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/credit-decisioning/{loan_id}")
async def run_credit_decisioning(
    loan_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep,
    _perm=Depends(require_permission("loans:credit_decision")),
):
    """Run automated credit decisioning on a loan application."""
    result = await LoanOriginationService.perform_credit_decisioning(
        db=db_session,
        loan_id=loan_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/underwrite/{loan_id}")
async def underwrite_loan(
    loan_id: int,
    approved: bool,
    current_user: CurrentUserDep,
    db_session: SessionDep,
    _perm=Depends(require_permission("loans:underwrite")),
    notes: str = "",
):
    """Admin underwriting decision."""
    result = await LoanOriginationService.underwrite_loan(
        db=db_session,
        loan_id=loan_id,
        admin_id=current_user.id,
        approved=approved,
        notes=notes,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/disburse/{loan_id}")
async def disburse_loan(
    loan_id: int,
    to_account_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep,
    _perm=Depends(require_permission("loans:disburse")),
):
    """Disburse an approved loan."""
    result = await LoanOriginationService.disburse_funds(
        db=db_session,
        loan_id=loan_id,
        to_account_id=to_account_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/payment/{loan_id}")
async def make_loan_payment(
    loan_id: int,
    amount: float,
    current_user: CurrentUserDep,
    db_session: SessionDep,
):
    """Record a loan payment."""
    result = await LoanOriginationService.record_payment(
        db=db_session,
        loan_id=loan_id,
        amount=Decimal(str(amount)),
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/details/{loan_id}")
async def get_loan_details(
    loan_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep,
):
    """Get loan details."""
    result = await LoanOriginationService.get_loan_details(
        db=db_session,
        loan_id=loan_id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/my-loans")
async def get_my_loans(
    current_user: CurrentUserDep,
    db_session: SessionDep,
):
    """Get all of user's loans."""
    result = await LoanOriginationService.get_user_loans(
        db=db_session,
        user_id=current_user.id,
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


# Legacy route for backward compatibility
loans_router = router
