"""
Payment API Endpoints - /api/v1/payments/*
ACH, Wire, RTP, FedNow transfer APIs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from deps import SessionDep, get_current_user
from models import User, Transaction, Settlement
from payment_rail_service import (
    PaymentRailService, ACHService, WireService, RTPService,
    FedNowService, PaymentRail
)
from audit_service import AuditService

router = APIRouter(prefix="/payments", tags=["payments"])


# ==================== PYDANTIC MODELS ====================

class ACHTransferRequest(BaseModel):
    receiving_account: str
    receiving_routing: str
    amount: float
    description: Optional[str] = None


class WireTransferRequest(BaseModel):
    receiving_bank: str
    receiving_routing: str
    receiving_account: str
    amount: float
    swift_code: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    transaction_id: int
    rail_type: str
    status: str
    settlement_date: Optional[str] = None
    settlement_time: Optional[str] = None


class PaymentResponseModel(BaseModel):
    success: bool
    transaction_id: int


# ==================== ACH ENDPOINTS ====================

@router.post("/ach", response_model=PaymentResponseModel)
async def submit_ach_transfer(
    request: ACHTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Submit ACH transfer request"""
    try:
        # Validate user has account
        if not current_user.accounts or len(current_user.accounts) == 0:
            raise HTTPException(status_code=400, detail="User has no accounts")
        
        sender_account = current_user.accounts[0]
        
        # Validate sufficient funds
        if sender_account.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        # Create transaction
        transaction = Transaction(
            sender_id=current_user.id,
            sender_account_id=sender_account.id,
            amount=request.amount,
            description=request.description or "ACH Transfer",
            status="pending",
            direction="outgoing"
        )
        db.add(transaction)
        db.flush()
        
        # Route to ACH
        result = await PaymentRailService.route_transaction(
            db, transaction.id, PaymentRail.ACH,
            receiving_account=request.receiving_account,
            receiving_routing=request.receiving_routing
        )
        
        # Log audit
        await AuditService.log_transaction_action(
            db, "create", transaction.id,
            new_status="pending", amount=request.amount,
            user_id=current_user.id,
            reason="ACH transfer submitted"
        )
        
        db.commit()
        return {"success": result["success"], "transaction_id": transaction.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ach/{transaction_id}")
async def get_ach_status(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get ACH transfer status"""
    try:
        settlement = db.query(Settlement).filter(
            Settlement.transaction_id == transaction_id,
            Settlement.rail_type == "ACH"
        ).first()
        
        if not settlement:
            raise HTTPException(status_code=404, detail="ACH transfer not found")
        
        return {
            "transaction_id": transaction_id,
            "rail_type": "ACH",
            "status": settlement.status,
            "settlement_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ach/batch")
async def create_ach_batch(
    effective_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Create ACH batch for submission (admin endpoint)"""
    try:
        from datetime import datetime as dt
        
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        effective = dt.fromisoformat(effective_date).date()
        result = await ACHService.batch_transactions(db, effective)
        
        await AuditService.log_action(
            db, "batch_ach", "ach_file", 0,
            user_id=current_user.id,
            new_value=result
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WIRE ENDPOINTS ====================

@router.post("/wire", response_model=PaymentResponseModel)
async def submit_wire_transfer(
    request: WireTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Submit wire transfer request"""
    try:
        if not current_user.accounts or len(current_user.accounts) == 0:
            raise HTTPException(status_code=400, detail="User has no accounts")
        
        sender_account = current_user.accounts[0]
        
        # Wire fee
        wire_fee = 15.0
        total_amount = request.amount + wire_fee
        
        if sender_account.balance < total_amount:
            raise HTTPException(status_code=400, detail="Insufficient funds for wire + fee")
        
        # Create transaction
        transaction = Transaction(
            sender_id=current_user.id,
            sender_account_id=sender_account.id,
            amount=request.amount,
            description=f"Wire to {request.receiving_bank}",
            status="pending",
            direction="outgoing"
        )
        db.add(transaction)
        db.flush()
        
        # Route to Wire
        result = await PaymentRailService.route_transaction(
            db, transaction.id, PaymentRail.WIRE,
            receiving_bank=request.receiving_bank,
            receiving_routing=request.receiving_routing,
            receiving_account=request.receiving_account
        )
        
        await AuditService.log_transaction_action(
            db, "create", transaction.id,
            new_status="pending", amount=request.amount,
            user_id=current_user.id,
            reason=f"Wire transfer to {request.receiving_bank}"
        )
        
        db.commit()
        return {"success": result["success"], "transaction_id": transaction.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wire/{transaction_id}")
async def get_wire_status(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get wire transfer status"""
    try:
        settlement = db.query(Settlement).filter(
            Settlement.transaction_id == transaction_id,
            Settlement.rail_type == "Wire"
        ).first()
        
        if not settlement:
            raise HTTPException(status_code=404, detail="Wire transfer not found")
        
        return {
            "transaction_id": transaction_id,
            "rail_type": "Wire",
            "status": settlement.status,
            "settlement_time": settlement.settlement_time.isoformat() if settlement.settlement_time else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RTP ENDPOINTS ====================

@router.post("/rtp", response_model=PaymentResponseModel)
async def submit_rtp_transfer(
    request: ACHTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Submit Real-Time Payment (RTP) transfer"""
    try:
        if not current_user.accounts or len(current_user.accounts) == 0:
            raise HTTPException(status_code=400, detail="User has no accounts")
        
        sender_account = current_user.accounts[0]
        
        if sender_account.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        transaction = Transaction(
            sender_id=current_user.id,
            sender_account_id=sender_account.id,
            amount=request.amount,
            description=request.description or "RTP Transfer",
            status="pending",
            direction="outgoing"
        )
        db.add(transaction)
        db.flush()
        
        result = await PaymentRailService.route_transaction(
            db, transaction.id, PaymentRail.RTP
        )
        
        await AuditService.log_transaction_action(
            db, "create", transaction.id,
            new_status="pending", amount=request.amount,
            user_id=current_user.id,
            reason="RTP transfer submitted"
        )
        
        db.commit()
        return {"success": result["success"], "transaction_id": transaction.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FEDNOW ENDPOINTS ====================

@router.post("/fednow", response_model=PaymentResponseModel)
async def submit_fednow_transfer(
    request: ACHTransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Submit FedNow instant payment"""
    try:
        if not current_user.accounts or len(current_user.accounts) == 0:
            raise HTTPException(status_code=400, detail="User has no accounts")
        
        sender_account = current_user.accounts[0]
        
        if sender_account.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        transaction = Transaction(
            sender_id=current_user.id,
            sender_account_id=sender_account.id,
            amount=request.amount,
            description=request.description or "FedNow Transfer",
            status="pending",
            direction="outgoing"
        )
        db.add(transaction)
        db.flush()
        
        result = await PaymentRailService.route_transaction(
            db, transaction.id, PaymentRail.FEDNOW
        )
        
        await AuditService.log_transaction_action(
            db, "create", transaction.id,
            new_status="pending", amount=request.amount,
            user_id=current_user.id,
            reason="FedNow transfer submitted"
        )
        
        db.commit()
        return {"success": result["success"], "transaction_id": transaction.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SETTLEMENT STATUS ====================

@router.get("/settlement/{transaction_id}")
async def get_settlement_status(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get settlement status for transaction"""
    try:
        settlement = db.query(Settlement).filter(
            Settlement.transaction_id == transaction_id
        ).first()
        
        if not settlement:
            raise HTTPException(status_code=404, detail="Settlement not found")
        
        return {
            "transaction_id": transaction_id,
            "rail_type": settlement.rail_type,
            "status": settlement.status,
            "settlement_date": settlement.settlement_date.isoformat() if settlement.settlement_date else None,
            "settlement_time": settlement.settlement_time.isoformat() if settlement.settlement_time else None,
            "retry_count": settlement.retry_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/{batch_id}")
async def get_batch_details(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get ACH batch details (admin)"""
    try:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Admin only")
        
        from models import ACHFile
        
        batch = db.query(ACHFile).filter(ACHFile.file_id == batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        return {
            "file_id": batch.file_id,
            "batch_number": batch.batch_number,
            "status": batch.status,
            "total_entries": batch.total_entries,
            "total_amount": batch.total_amount,
            "transmission_date": batch.transmission_date.isoformat(),
            "effective_date": batch.effective_date.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
