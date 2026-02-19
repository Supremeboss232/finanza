# routers/accounts_api.py
# Account management API endpoints - account CRUD, holds, statements, transactions, sweeps

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
from deps import get_db
from account_management_service import (
    AccountManagementService,
    StatementGenerationService,
    InterestAccrualService,
    SweepService,
    TransactionHistoryService
)
from audit_service import AuditService

# Pydantic models
class AccountCreateRequest(BaseModel):
    owner_id: int
    account_type_name: str
    initial_deposit: float = 0.0

class HoldRequest(BaseModel):
    hold_type: str  # legal, regulatory, fraud, kyc, administrative
    amount: Optional[float] = None
    reason: str
    applied_by: int
    expires_in_days: Optional[int] = None

class SweepRequest(BaseModel):
    target_account_id: int
    frequency: str  # daily, weekly, monthly
    minimum_threshold: float
    maximum_amount: Optional[float] = None

class CloseAccountRequest(BaseModel):
    closure_reason: str
    initiated_by: int

router = APIRouter(
    prefix="/api/v1/accounts",
    tags=["accounts"],
    responses={404: {"description": "Not found"}}
)


# ==================== ACCOUNT OPERATIONS ====================

@router.post("/")
async def create_account(
    request: AccountCreateRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Open a new account
    
    - **owner_id**: User ID of account owner
    - **account_type_name**: Type of account (Checking, Savings, etc.)
    - **initial_deposit**: Initial deposit amount
    """
    try:
        result = await AccountManagementService.open_account(
            db=db,
            owner_id=request.owner_id,
            account_type_name=request.account_type_name,
            initial_deposit=request.initial_deposit
        )
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=result["account_id"],
                action="account_opened",
                details={"account_type": request.account_type_name}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}")
async def get_account(
    account_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get account details including balance and status
    """
    try:
        balance_result = await AccountManagementService.get_account_balance(db, account_id)
        available_result = await AccountManagementService.get_available_balance(db, account_id)
        
        if balance_result["success"]:
            return {
                "success": True,
                "account_id": account_id,
                **balance_result,
                "available_balance": available_result.get("available_balance", 0.0)
            }
        return balance_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/balance")
async def get_balance(
    account_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get real-time account balance
    """
    try:
        result = await AccountManagementService.get_account_balance(db, account_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/available-balance")
async def get_available_balance(
    account_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get available balance (excluding holds)
    """
    try:
        result = await AccountManagementService.get_available_balance(db, account_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/close")
async def close_account(
    account_id: int,
    request: CloseAccountRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Close an account
    """
    try:
        result = await AccountManagementService.close_account(
            db=db,
            account_id=account_id,
            closure_reason=request.closure_reason,
            initiated_by=request.initiated_by
        )
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="account_closed",
                details={"reason": request.closure_reason}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ACCOUNT HOLDS ====================

@router.post("/{account_id}/holds")
async def place_hold(
    account_id: int,
    request: HoldRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Place a hold on account (legal, regulatory, fraud, kyc, administrative)
    """
    try:
        result = await AccountManagementService.place_hold(
            db=db,
            account_id=account_id,
            hold_type=request.hold_type,
            amount=request.amount,
            reason=request.reason,
            applied_by=request.applied_by,
            expires_in_days=request.expires_in_days
        )
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="hold_placed",
                details={"hold_type": request.hold_type, "amount": request.amount}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/holds")
async def list_holds(
    account_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    List all holds on account
    """
    try:
        from models import AccountHold
        holds = db.query(AccountHold).filter(
            AccountHold.account_id == account_id,
            AccountHold.released_at == None
        ).all()
        
        return {
            "success": True,
            "account_id": account_id,
            "hold_count": len(holds),
            "holds": [
                {
                    "hold_id": h.id,
                    "hold_type": h.hold_type,
                    "amount": h.amount,
                    "reason": h.reason,
                    "expires_at": h.expires_at.isoformat() if h.expires_at else None
                }
                for h in holds
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{account_id}/holds/{hold_id}")
async def release_hold(
    account_id: int,
    hold_id: int,
    release_reason: str = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Release an account hold
    """
    try:
        result = await AccountManagementService.release_hold(
            db=db,
            hold_id=hold_id,
            release_reason=release_reason
        )
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="hold_released",
                details={"hold_id": hold_id, "reason": release_reason}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== STATEMENTS ====================

@router.post("/{account_id}/statements")
async def generate_statement(
    account_id: int,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
) -> dict:
    """
    Generate account statement for specified period
    """
    try:
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)
        
        result = await StatementGenerationService.generate_statement(
            db=db,
            account_id=account_id,
            period_start=period_start,
            period_end=period_end
        )
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="statement_generated",
                details={"period_days": days}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/statements/{statement_id}")
async def get_statement(
    account_id: int,
    statement_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Retrieve statement details
    """
    try:
        result = await StatementGenerationService.get_statement(db, statement_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TRANSACTIONS ====================

@router.get("/{account_id}/transactions")
async def get_transactions(
    account_id: int,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get transaction history for account
    """
    try:
        result = await TransactionHistoryService.get_transaction_history(
            db=db,
            account_id=account_id,
            days=days,
            limit=limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{account_id}/transactions/export")
async def export_transactions(
    account_id: int,
    format_type: str = Query("csv", pattern="^(csv|json)$"),
    days: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
) -> dict:
    """
    Export transaction history (CSV or JSON)
    """
    try:
        result = await TransactionHistoryService.export_transactions(
            db=db,
            account_id=account_id,
            format_type=format_type,
            days=days
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INTEREST ====================

@router.post("/{account_id}/interest/accrue")
async def accrue_interest(
    account_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Calculate and accrue daily interest (admin only)
    """
    try:
        result = await InterestAccrualService.accrue_daily_interest(db, account_id)
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="interest_accrued",
                details={"amount": result.get("accrued_amount")}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/interest/post")
async def post_interest(
    account_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Post monthly accrued interest (admin only)
    """
    try:
        result = await InterestAccrualService.post_monthly_interest(db, account_id)
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="interest_posted",
                details={"amount": result.get("posted_amount")}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SWEEPS ====================

@router.post("/{account_id}/sweep")
async def setup_sweep(
    account_id: int,
    request: SweepRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Configure automatic sweep rule
    """
    try:
        result = await SweepService.setup_sweep(
            db=db,
            account_id=account_id,
            target_account_id=request.target_account_id,
            frequency=request.frequency,
            minimum_threshold=request.minimum_threshold,
            maximum_amount=request.maximum_amount
        )
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="sweep_configured",
                details={
                    "target": request.target_account_id,
                    "frequency": request.frequency
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{account_id}/sweep/{sweep_id}/execute")
async def execute_sweep(
    account_id: int,
    sweep_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Execute a single sweep (admin only)
    """
    try:
        result = await SweepService.execute_sweep(db, sweep_id)
        
        if result["success"]:
            await AuditService.log_account_action(
                db=db,
                account_id=account_id,
                action="sweep_executed",
                details={"sweep_id": sweep_id, "amount": result.get("sweep_amount")}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH ====================

@router.get("/health")
async def health() -> dict:
    """Health check for accounts API"""
    return {"status": "healthy", "service": "accounts_api"}
