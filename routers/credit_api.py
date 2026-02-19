"""
Credit Decisioning API Endpoints - /api/v1/credit/*
Loan decisioning, credit scoring, amortization
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from deps import SessionDep, get_current_user
from models import User, Loan, CreditScore, LoanPayment
from credit_decisioning_service import (
    CreditDecisionService, AmortizationService
)
from audit_service import AuditService

router = APIRouter(prefix="/credit", tags=["credit"])


# ==================== PYDANTIC MODELS ====================

class LoanApplicationRequest(BaseModel):
    loan_type: str  # personal, auto, mortgage, business
    amount: float
    term_months: int = 60
    purpose: Optional[str] = None


class CreditDecisionResponse(BaseModel):
    decision: str  # approve, deny, manual_review
    credit_score: Optional[int] = None
    dti: float
    interest_rate: float
    reason: str
    manual_review: bool = False


class AmortizationScheduleResponse(BaseModel):
    monthly_payment: float
    total_payments: int
    total_interest: float
    schedule: list


# ==================== CREDIT DECISION ENDPOINTS ====================

@router.post("/apply-loan", response_model=CreditDecisionResponse)
async def apply_for_loan(
    request: LoanApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Apply for loan - triggers automated credit decision"""
    try:
        # Verify KYC completed
        if current_user.kyc_status != "approved":
            raise HTTPException(status_code=400, detail="KYC not approved")
        
        # Make credit decision
        decision = await CreditDecisionService.make_decision(
            db,
            current_user.id,
            request.amount,
            request.loan_type,
            request.term_months
        )
        
        if not decision["success"]:
            raise HTTPException(status_code=500, detail=decision["error"])
        
        # If approved, create loan record
        if decision["decision"] == "approve":
            loan = Loan(
                user_id=current_user.id,
                loan_type=request.loan_type,
                amount=request.amount,
                remaining_balance=request.amount,
                interest_rate=decision["interest_rate"],
                term_months=request.term_months,
                purpose=request.purpose,
                status="approved",
                monthly_payment=(
                    request.amount * (decision["interest_rate"] / 12) / 
                    (1 - (1 + decision["interest_rate"] / 12) ** (-request.term_months))
                )
            )
            db.add(loan)
            db.flush()
            
            # Generate amortization schedule
            await AmortizationService.generate_schedule(
                db,
                loan.id,
                request.amount,
                decision["interest_rate"],
                request.term_months
            )
            
            # Log audit
            await AuditService.log_loan_action(
                db, "create", loan.id,
                new_status="approved",
                amount=request.amount,
                user_id=current_user.id,
                reason="Auto-approved by credit decision engine"
            )
            
            db.commit()
        elif decision["decision"] == "manual_review":
            # Create pending loan for manual review
            loan = Loan(
                user_id=current_user.id,
                loan_type=request.loan_type,
                amount=request.amount,
                remaining_balance=request.amount,
                interest_rate=decision.get("interest_rate", 0.08),
                term_months=request.term_months,
                purpose=request.purpose,
                status="pending"
            )
            db.add(loan)
            db.flush()
            
            await AuditService.log_loan_action(
                db, "create", loan.id,
                new_status="pending",
                amount=request.amount,
                user_id=current_user.id,
                reason=f"Manual review required: {decision['reason']}"
            )
            
            db.commit()
        else:
            # Denied
            await AuditService.log_loan_action(
                db, "deny", 0,
                new_status="denied",
                amount=request.amount,
                user_id=current_user.id,
                reason=decision["reason"]
            )
        
        return {
            "decision": decision["decision"],
            "credit_score": decision.get("credit_score"),
            "dti": decision.get("dti", 0),
            "interest_rate": decision.get("interest_rate", 0.08),
            "reason": decision["reason"],
            "manual_review": decision.get("manual_review", False)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decision/{loan_id}")
async def get_credit_decision(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get credit decision details for loan"""
    try:
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.user_id == current_user.id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        return {
            "loan_id": loan_id,
            "status": loan.status,
            "loan_type": loan.loan_type,
            "amount": loan.amount,
            "interest_rate": loan.interest_rate,
            "term_months": loan.term_months,
            "monthly_payment": loan.monthly_payment
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CREDIT SCORE ENDPOINTS ====================

@router.get("/scores")
async def get_credit_scores(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get user's credit scores from all bureaus"""
    try:
        scores = db.query(CreditScore).filter(
            CreditScore.user_id == current_user.id
        ).order_by(CreditScore.pulled_date.desc()).all()
        
        if not scores:
            # Pull new scores
            result = await CreditDecisionService.CreditBureauService.pull_credit_score(
                db, current_user.id
            )
            scores = db.query(CreditScore).filter(
                CreditScore.user_id == current_user.id
            ).all()
        
        return [
            {
                "bureau": s.bureau,
                "score": s.score,
                "pulled_date": s.pulled_date.isoformat(),
                "expires_date": s.expires_date.isoformat()
            }
            for s in scores
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AMORTIZATION SCHEDULE ====================

@router.get("/loans/{loan_id}/amortization-schedule")
async def get_amortization_schedule(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get amortization schedule for loan"""
    try:
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.user_id == current_user.id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        payments = db.query(LoanPayment).filter(
            LoanPayment.loan_id == loan_id
        ).order_by(LoanPayment.payment_number).all()
        
        schedule = [
            {
                "payment_number": p.payment_number,
                "scheduled_date": p.scheduled_date.isoformat(),
                "due_date": p.due_date.isoformat(),
                "payment_amount": p.amount,
                "principal": p.principal_amount,
                "interest": p.interest_amount,
                "status": p.status,
                "paid_date": p.paid_date.isoformat() if p.paid_date else None
            }
            for p in payments
        ]
        
        return {
            "loan_id": loan_id,
            "monthly_payment": loan.monthly_payment,
            "total_payments": loan.term_months,
            "schedule": schedule
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/loans/{loan_id}/payment-history")
async def get_payment_history(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Get payment history for loan"""
    try:
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.user_id == current_user.id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        payments = db.query(LoanPayment).filter(
            LoanPayment.loan_id == loan_id,
            LoanPayment.status == "paid"
        ).order_by(LoanPayment.payment_number.desc()).all()
        
        return {
            "loan_id": loan_id,
            "total_paid": sum(p.amount for p in payments),
            "payments": [
                {
                    "payment_number": p.payment_number,
                    "paid_date": p.paid_date.isoformat() if p.paid_date else None,
                    "amount": p.amount,
                    "principal": p.principal_amount,
                    "interest": p.interest_amount
                }
                for p in payments
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/loans/{loan_id}/make-payment")
async def make_loan_payment(
    loan_id: int,
    amount: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Record loan payment"""
    try:
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.user_id == current_user.id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        from datetime import datetime as dt
        result = await AmortizationService.record_payment(
            db, loan_id, amount, dt.utcnow()
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        await AuditService.log_loan_action(
            db, "payment", loan_id,
            amount=amount,
            user_id=current_user.id,
            reason="Loan payment made"
        )
        
        return {"success": True, "payment_recorded": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/loans/{loan_id}/delinquency-status")
async def get_delinquency_status(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionDep)
):
    """Check delinquency status"""
    try:
        from models import Delinquency
        
        loan = db.query(Loan).filter(
            Loan.id == loan_id,
            Loan.user_id == current_user.id
        ).first()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")
        
        delinquency = db.query(Delinquency).filter(
            Delinquency.loan_id == loan_id
        ).first()
        
        if not delinquency:
            return {
                "loan_id": loan_id,
                "status": "current",
                "days_past_due": 0
            }
        
        return {
            "loan_id": loan_id,
            "status": delinquency.delinquency_status,
            "days_past_due": delinquency.days_past_due,
            "principal_at_risk": delinquency.principal_at_risk,
            "last_payment_date": delinquency.last_payment_date.isoformat() if delinquency.last_payment_date else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
