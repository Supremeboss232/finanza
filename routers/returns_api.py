# routers/returns_api.py
# Payment returns, NSF, disputes, and exception handling API endpoints

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from deps import get_db
from payment_returns_service import (
    ACHReturnService,
    NSFService,
    DisputeService,
    ExceptionHandlingService
)
from audit_service import AuditService

# Pydantic models
class ACHReturnRequest(BaseModel):
    transaction_id: int
    return_code: str  # R01-R99 NACHA codes
    return_reason: str
    original_amount: float
    return_date: Optional[datetime] = None

class ACHCorrectionRequest(BaseModel):
    return_id: int
    corrected_transaction_id: int
    submitted_by: int

class NSFRequest(BaseModel):
    account_id: int
    transaction_id: int
    transaction_amount: float

class NSFRecoveryRequest(BaseModel):
    nsf_id: int
    retry_account: Optional[int] = None

class DisputeRequest(BaseModel):
    transaction_id: int
    dispute_type: str  # unauthorized, duplicate, amount_mismatch, chargeback
    description: str
    amount: float
    filed_by: int

class DisputeEvidenceRequest(BaseModel):
    dispute_id: int
    evidence_type: str  # statement, receipt, email, documentation
    description: str
    reference_number: Optional[str] = None

class ExceptionRequest(BaseModel):
    transaction_id: int
    exception_type: str  # fraud_flag, velocity_check, limit_exceeded, manual_review
    severity: str  # low, medium, high, critical
    description: str

router = APIRouter(
    prefix="/api/v1/returns",
    tags=["returns"],
    responses={404: {"description": "Not found"}}
)


# ==================== ACH RETURNS ====================

@router.post("/ach/return")
async def process_ach_return(
    request: ACHReturnRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Process ACH return (R01-R99 NACHA codes)
    Supported codes: R01 (Insufficient Funds), R02 (Account Closed), R03 (No Account),
    R04 (Invalid Account), R05 (Reserved), R06 (Routing Number Check Digit Error),
    R07 (Wrong Account Number), R08 (Account Type Mismatch), R09 (Predates Account Opening),
    R10 (Account Holder Deceased), R11 (Not Authorized), R12 (Consumer Dispute),
    R13-R99 (Various other return reasons)
    """
    try:
        result = await ACHReturnService.process_return(
            db=db,
            transaction_id=request.transaction_id,
            return_code=request.return_code,
            return_reason=request.return_reason,
            original_amount=request.original_amount,
            return_date=request.return_date
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="ach_return_processed",
                details={
                    "transaction_id": request.transaction_id,
                    "return_code": request.return_code,
                    "correctable": result.get("is_correctable"),
                    "amount": request.original_amount
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ach/return/{return_id}")
async def get_return_status(
    return_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get ACH return status and details
    """
    try:
        result = await ACHReturnService.get_return_status(db, return_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ach/correction")
async def submit_ach_correction(
    request: ACHCorrectionRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Submit correcting ACH entry for returnable transaction
    """
    try:
        result = await ACHReturnService.submit_correction(
            db=db,
            return_id=request.return_id,
            corrected_transaction_id=request.corrected_transaction_id,
            submitted_by=request.submitted_by
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="ach_correction_submitted",
                details={
                    "return_id": request.return_id,
                    "corrected_transaction_id": request.corrected_transaction_id
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ach/returns-list")
async def list_ach_returns(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
) -> dict:
    """
    List ACH returns for last N days
    """
    try:
        from models import ACHReturn
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        returns = db.query(ACHReturn).filter(
            ACHReturn.created_at >= cutoff_date
        ).order_by(ACHReturn.created_at.desc()).limit(limit).all()
        
        return {
            "success": True,
            "return_count": len(returns),
            "returns": [
                {
                    "return_id": r.id,
                    "transaction_id": r.transaction_id,
                    "return_code": r.return_code,
                    "return_reason": r.return_reason,
                    "amount": r.original_amount,
                    "return_date": r.return_date.isoformat() if r.return_date else None,
                    "correctable": r.is_correctable,
                    "status": r.return_status,
                    "created_at": r.created_at.isoformat()
                }
                for r in returns
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== NSF ====================

@router.post("/nsf/apply-fee")
async def apply_nsf_fee(
    request: NSFRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Check balance and apply NSF fee if insufficient funds
    Standard NSF fee: $35, 2-day recovery grace period
    """
    try:
        # Check available balance first
        balance_result = await NSFService.check_available_balance(
            db=db,
            account_id=request.account_id,
            required_amount=request.transaction_amount
        )
        
        if not balance_result["has_sufficient_balance"]:
            # Apply NSF fee
            result = await NSFService.apply_nsf_fee(
                db=db,
                account_id=request.account_id,
                transaction_id=request.transaction_id,
                transaction_amount=request.transaction_amount,
                nsf_fee=35.00
            )
            
            if result["success"]:
                await AuditService.log_transaction_action(
                    db=db,
                    action="nsf_fee_applied",
                    details={
                        "account_id": request.account_id,
                        "transaction_id": request.transaction_id,
                        "amount": request.transaction_amount,
                        "fee": 35.00
                    }
                )
            
            return result
        
        return {
            "success": True,
            "has_nsf": False,
            "available_balance": balance_result["available_balance"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nsf/recovery-attempt")
async def attempt_nsf_recovery(
    request: NSFRecoveryRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Attempt to recover NSF transaction (2-day grace period)
    """
    try:
        retry_account = request.retry_account  # Can retry from different account
        result = await NSFService.attempt_recovery(
            db=db,
            nsf_id=request.nsf_id,
            retry_account_id=retry_account
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="nsf_recovery_attempted",
                details={
                    "nsf_id": request.nsf_id,
                    "recovery_result": result.get("recovery_status")
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nsf/{nsf_id}")
async def get_nsf_status(
    nsf_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get NSF event status and details
    """
    try:
        from models import NSFManagement
        
        nsf = db.query(NSFManagement).filter(
            NSFManagement.id == nsf_id
        ).first()
        
        if not nsf:
            return {"success": False, "error": "NSF event not found"}
        
        return {
            "success": True,
            "nsf_id": nsf_id,
            "account_id": nsf.account_id,
            "transaction_id": nsf.transaction_id,
            "transaction_amount": nsf.transaction_amount,
            "nsf_fee": nsf.nsf_fee,
            "total_charged": nsf.nsf_fee + nsf.transaction_amount,
            "fee_applied_date": nsf.fee_applied_date.isoformat(),
            "recovery_status": nsf.recovery_status,
            "recovery_due_date": nsf.recovery_due_date.isoformat() if nsf.recovery_due_date else None,
            "fee_waived": nsf.fee_waived,
            "waived_at": nsf.waived_at.isoformat() if nsf.waived_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nsf/{nsf_id}/reverse-fee")
async def reverse_nsf_fee(
    nsf_id: int,
    reason: str = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Reverse/waive NSF fee (customer service exception)
    """
    try:
        result = await NSFService.reverse_nsf_fee(
            db=db,
            nsf_id=nsf_id,
            waive_reason=reason
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="nsf_fee_reversed",
                details={
                    "nsf_id": nsf_id,
                    "reason": reason,
                    "fee_amount": result.get("fee_reversed")
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nsf/account/{account_id}")
async def get_nsf_history(
    account_id: int,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get NSF event history for account
    """
    try:
        from models import NSFManagement
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        events = db.query(NSFManagement).filter(
            NSFManagement.account_id == account_id,
            NSFManagement.fee_applied_date >= cutoff_date
        ).order_by(NSFManagement.fee_applied_date.desc()).limit(limit).all()
        
        total_fees = sum(e.nsf_fee for e in events if not e.fee_waived)
        
        return {
            "success": True,
            "account_id": account_id,
            "nsf_count": len(events),
            "total_fees_charged": total_fees,
            "nsf_events": [
                {
                    "nsf_id": e.id,
                    "fee_applied_date": e.fee_applied_date.isoformat(),
                    "transaction_amount": e.transaction_amount,
                    "fee": e.nsf_fee,
                    "recovery_status": e.recovery_status,
                    "waived": e.fee_waived
                }
                for e in events
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DISPUTES ====================

@router.post("/dispute/file")
async def file_dispute(
    request: DisputeRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    File a transaction dispute (unauthorized, duplicate, amount mismatch, chargeback)
    """
    try:
        result = await DisputeService.file_dispute(
            db=db,
            transaction_id=request.transaction_id,
            dispute_type=request.dispute_type,
            description=request.description,
            amount=request.amount,
            filed_by=request.filed_by
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="dispute_filed",
                details={
                    "transaction_id": request.transaction_id,
                    "dispute_type": request.dispute_type,
                    "amount": request.amount
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dispute/{dispute_id}")
async def get_dispute_status(
    dispute_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get dispute status and details
    """
    try:
        from models import TransactionDispute
        
        dispute = db.query(TransactionDispute).filter(
            TransactionDispute.id == dispute_id
        ).first()
        
        if not dispute:
            return {"success": False, "error": "Dispute not found"}
        
        return {
            "success": True,
            "dispute_id": dispute_id,
            "transaction_id": dispute.transaction_id,
            "dispute_type": dispute.dispute_type,
            "amount": dispute.dispute_amount,
            "filed_date": dispute.filed_date.isoformat(),
            "status": dispute.dispute_status,
            "resolution": dispute.resolution,
            "resolved_date": dispute.resolved_date.isoformat() if dispute.resolved_date else None,
            "customer_refunded": dispute.customer_refunded
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dispute/{dispute_id}/submit-evidence")
async def submit_dispute_evidence(
    dispute_id: int,
    request: DisputeEvidenceRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Submit evidence for dispute resolution
    """
    try:
        result = await DisputeService.submit_evidence(
            db=db,
            dispute_id=dispute_id,
            evidence_type=request.evidence_type,
            description=request.description,
            reference_number=request.reference_number
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="dispute_evidence_submitted",
                details={
                    "dispute_id": dispute_id,
                    "evidence_type": request.evidence_type
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dispute/{dispute_id}/resolve")
async def resolve_dispute(
    dispute_id: int,
    resolution: str = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Resolve dispute (approve, deny, chargeback_accepted, chargeback_denied)
    """
    try:
        result = await DisputeService.resolve_dispute(
            db=db,
            dispute_id=dispute_id,
            resolution=resolution
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="dispute_resolved",
                details={
                    "dispute_id": dispute_id,
                    "resolution": resolution,
                    "refund_amount": result.get("refund_amount")
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EXCEPTIONS ====================

@router.post("/exception/detect")
async def detect_exception(
    request: ExceptionRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Detect and log transaction exception (fraud flag, velocity check, limit exceeded, manual review)
    """
    try:
        result = await ExceptionHandlingService.detect_exception(
            db=db,
            transaction_id=request.transaction_id,
            exception_type=request.exception_type,
            severity=request.severity,
            description=request.description
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="exception_detected",
                details={
                    "transaction_id": request.transaction_id,
                    "type": request.exception_type,
                    "severity": request.severity
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exception/{exception_id}")
async def get_exception_status(
    exception_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get exception status and resolution
    """
    try:
        from models import PaymentException
        
        exception = db.query(PaymentException).filter(
            PaymentException.id == exception_id
        ).first()
        
        if not exception:
            return {"success": False, "error": "Exception not found"}
        
        return {
            "success": True,
            "exception_id": exception_id,
            "transaction_id": exception.transaction_id,
            "exception_type": exception.exception_type,
            "severity": exception.severity,
            "detected_at": exception.detected_at.isoformat(),
            "status": exception.status,
            "resolution": exception.resolution,
            "resolved_at": exception.resolved_at.isoformat() if exception.resolved_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exception/{exception_id}/escalate")
async def escalate_exception(
    exception_id: int,
    reason: str = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Escalate exception for manual review
    """
    try:
        result = await ExceptionHandlingService.escalate_exception(
            db=db,
            exception_id=exception_id,
            escalation_reason=reason
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="exception_escalated",
                details={
                    "exception_id": exception_id,
                    "reason": reason
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH ====================

@router.get("/health")
async def health() -> dict:
    """Health check for returns API"""
    return {"status": "healthy", "service": "returns_api"}
