# routers/lending_api.py
# Lending and loan servicing API endpoints - payments, modifications, collections

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from deps import get_db
from lending_servicing_service import (
    LoanServicingService,
    LoanModificationService,
    CollectionsService,
    PrepaymentService,
    ForbearanceService
)
from audit_service import AuditService

# Pydantic models
class PaymentRequest(BaseModel):
    payment_amount: float
    payment_date: Optional[datetime] = None

class ModificationRequest(BaseModel):
    modification_type: str  # rate_reduction, term_extension, forbearance, deferment
    reason: str
    requested_by: int

class ModificationApprovalRequest(BaseModel):
    approved_by: int

class CollectionEscalationRequest(BaseModel):
    reason: str

class CollectionContactRequest(BaseModel):
    contact_method: str  # phone, letter, email, in_person
    contact_result: str  # contacted, no_answer, wrong_number, ceased
    notes: Optional[str] = None

class PrepaymentRequest(BaseModel):
    prepayment_amount: float
    prepayment_type: str  # extra_payment, lump_sum, payoff
    applied_by: int

class ForbearanceRequest(BaseModel):
    forbearance_type: str  # forbearance, deferment, income_driven
    duration_months: int
    reason: str
    approved_by: int

router = APIRouter(
    prefix="/api/v1/loans",
    tags=["lending"],
    responses={404: {"description": "Not found"}}
)


# ==================== PAYMENTS ====================

@router.post("/{loan_id}/payment")
async def apply_payment(
    loan_id: int,
    request: PaymentRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Apply payment to loan (interest allocated first, then principal)
    """
    try:
        result = await LoanServicingService.apply_payment(
            db=db,
            loan_id=loan_id,
            payment_amount=request.payment_amount,
            payment_date=request.payment_date
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="loan_payment",
                details={
                    "loan_id": loan_id,
                    "amount": request.payment_amount,
                    "principal": result.get("principal_portion"),
                    "interest": result.get("interest_portion")
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}/payment-schedule")
async def get_payment_schedule(
    loan_id: int,
    limit: int = Query(60, ge=1, le=360),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get loan payment schedule
    """
    try:
        from models import LoanPaymentSchedule
        
        schedule = db.query(LoanPaymentSchedule).filter(
            LoanPaymentSchedule.loan_id == loan_id
        ).order_by(LoanPaymentSchedule.scheduled_date).limit(limit).all()
        
        return {
            "success": True,
            "loan_id": loan_id,
            "payment_count": len(schedule),
            "payments": [
                {
                    "payment_number": p.payment_number,
                    "scheduled_date": p.scheduled_date.isoformat(),
                    "principal": p.principal_payment,
                    "interest": p.interest_payment,
                    "total": p.total_payment,
                    "remaining_balance": p.principal_balance,
                    "status": p.payment_status,
                    "paid_date": p.paid_date.isoformat() if p.paid_date else None,
                    "days_late": p.days_late
                }
                for p in schedule
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}/payment-history")
async def get_payment_history(
    loan_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get payment history for loan
    """
    try:
        from models import LoanPayment
        
        payments = db.query(LoanPayment).filter(
            LoanPayment.loan_id == loan_id,
            LoanPayment.payment_status == "paid"
        ).order_by(LoanPayment.payment_date.desc()).limit(limit).all()
        
        return {
            "success": True,
            "loan_id": loan_id,
            "payment_count": len(payments),
            "payments": [
                {
                    "payment_date": p.payment_date.isoformat(),
                    "principal": p.principal_payment,
                    "interest": p.interest_payment,
                    "total": p.total_payment,
                    "balance_after": p.balance_after
                }
                for p in payments
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INTEREST ====================

@router.get("/{loan_id}/interest")
async def calculate_interest(
    loan_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Calculate accrued interest on loan
    """
    try:
        result = await LoanServicingService.calculate_interest(db, loan_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DELINQUENCY ====================

@router.get("/{loan_id}/delinquency")
async def get_delinquency_status(
    loan_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Check delinquency status of loan
    """
    try:
        result = await LoanServicingService.check_delinquency(db, loan_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== MODIFICATIONS ====================

@router.post("/{loan_id}/modification")
async def request_modification(
    loan_id: int,
    request: ModificationRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Request loan modification (rate reduction, term extension, forbearance, deferment)
    """
    try:
        result = await LoanModificationService.request_modification(
            db=db,
            loan_id=loan_id,
            modification_type=request.modification_type,
            reason=request.reason,
            requested_by=request.requested_by
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="modification_requested",
                details={
                    "loan_id": loan_id,
                    "type": request.modification_type,
                    "reason": request.reason
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{loan_id}/modification/{modification_id}/approve")
async def approve_modification(
    loan_id: int,
    modification_id: int,
    request: ModificationApprovalRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Approve loan modification
    """
    try:
        result = await LoanModificationService.approve_modification(
            db=db,
            modification_id=modification_id,
            approved_by=request.approved_by
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="modification_approved",
                details={
                    "loan_id": loan_id,
                    "modification_id": modification_id,
                    "new_rate": result.get("new_rate"),
                    "new_term": result.get("new_term")
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}/modification/{modification_id}")
async def get_modification_status(
    loan_id: int,
    modification_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get modification status
    """
    try:
        from models import LoanModification
        
        modification = db.query(LoanModification).filter(
            LoanModification.id == modification_id
        ).first()
        
        if not modification:
            return {"success": False, "error": "Modification not found"}
        
        return {
            "success": True,
            "modification_id": modification_id,
            "loan_id": loan_id,
            "type": modification.modification_type,
            "reason": modification.reason,
            "effective_date": modification.effective_date.isoformat() if modification.effective_date else None,
            "approved_at": modification.approved_at.isoformat() if modification.approved_at else None,
            "status": "approved" if modification.approved_at else "pending"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== COLLECTIONS ====================

@router.post("/{loan_id}/collections/escalate")
async def escalate_to_collections(
    loan_id: int,
    request: CollectionEscalationRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Move loan to collections (admin only)
    """
    try:
        result = await CollectionsService.escalate_to_collections(
            db=db,
            loan_id=loan_id,
            reason=request.reason
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="escalated_to_collections",
                details={"loan_id": loan_id, "reason": request.reason}
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}/collections")
async def get_collections_status(
    loan_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get collections status for loan
    """
    try:
        from models import LoanCollection
        
        collection = db.query(LoanCollection).filter(
            LoanCollection.loan_id == loan_id
        ).first()
        
        if not collection:
            return {"success": True, "status": "not_in_collections"}
        
        return {
            "success": True,
            "loan_id": loan_id,
            "collection_status": collection.collection_status,
            "days_past_due": collection.days_past_due,
            "principal_past_due": collection.principal_past_due,
            "interest_past_due": collection.interest_past_due,
            "fees_past_due": collection.fees_past_due,
            "collection_attempts": collection.collection_attempts,
            "last_collection_attempt": collection.last_collection_attempt.isoformat() if collection.last_collection_attempt else None,
            "assigned_to_agency": collection.assigned_to_collection_agency,
            "agency_assignment_date": collection.agency_assignment_date.isoformat() if collection.agency_assignment_date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{loan_id}/collections/contact")
async def log_collection_contact(
    loan_id: int,
    request: CollectionContactRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Log collection contact attempt
    """
    try:
        from models import LoanCollection
        
        collection = db.query(LoanCollection).filter(
            LoanCollection.loan_id == loan_id
        ).first()
        
        if not collection:
            return {"success": False, "error": "Loan not in collections"}
        
        result = await CollectionsService.log_collection_attempt(
            db=db,
            collection_id=collection.id,
            contact_method=request.contact_method,
            contact_result=request.contact_result,
            notes=request.notes
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="collection_contact_logged",
                details={
                    "loan_id": loan_id,
                    "method": request.contact_method,
                    "result": request.contact_result
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PREPAYMENT ====================

@router.post("/{loan_id}/prepayment")
async def process_prepayment(
    loan_id: int,
    request: PrepaymentRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Process prepayment on loan
    """
    try:
        result = await PrepaymentService.accept_prepayment(
            db=db,
            loan_id=loan_id,
            prepayment_amount=request.prepayment_amount,
            prepayment_type=request.prepayment_type,
            applied_by=request.applied_by
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="prepayment_applied",
                details={
                    "loan_id": loan_id,
                    "amount": request.prepayment_amount,
                    "interest_saved": result.get("interest_saved")
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== FORBEARANCE ====================

@router.post("/{loan_id}/forbearance")
async def request_forbearance(
    loan_id: int,
    request: ForbearanceRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Request forbearance/deferment on loan
    """
    try:
        result = await ForbearanceService.request_forbearance(
            db=db,
            loan_id=loan_id,
            forbearance_type=request.forbearance_type,
            duration_months=request.duration_months,
            reason=request.reason,
            approved_by=request.approved_by
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="forbearance_approved",
                details={
                    "loan_id": loan_id,
                    "type": request.forbearance_type,
                    "duration_months": request.duration_months
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{loan_id}/forbearance")
async def get_forbearance_status(
    loan_id: int,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get forbearance status
    """
    try:
        from models import Forbearance
        
        forbearance = db.query(Forbearance).filter(
            Forbearance.loan_id == loan_id
        ).order_by(Forbearance.start_date.desc()).first()
        
        if not forbearance:
            return {"success": True, "status": "no_forbearance"}
        
        return {
            "success": True,
            "loan_id": loan_id,
            "forbearance_type": forbearance.forbearance_type,
            "start_date": forbearance.start_date.isoformat(),
            "end_date": forbearance.end_date.isoformat(),
            "payment_resume_date": forbearance.payment_resume_date.isoformat() if forbearance.payment_resume_date else None,
            "reason": forbearance.reason,
            "status": "active" if datetime.utcnow() < forbearance.end_date else "ended"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CHARGE-OFF ====================

@router.post("/{loan_id}/charge-off")
async def charge_off_loan(
    loan_id: int,
    principal_amount: float = Query(...),
    interest_amount: float = Query(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Charge off a loan (admin only)
    """
    try:
        result = await CollectionsService.charge_off_loan(
            db=db,
            loan_id=loan_id,
            principal_amount=principal_amount,
            interest_amount=interest_amount
        )
        
        if result["success"]:
            await AuditService.log_transaction_action(
                db=db,
                action="loan_charged_off",
                details={
                    "loan_id": loan_id,
                    "principal": principal_amount,
                    "interest": interest_amount
                }
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HEALTH ====================

@router.get("/health")
async def health() -> dict:
    """Health check for lending API"""
    return {"status": "healthy", "service": "lending_api"}
