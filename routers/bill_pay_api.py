# routers/bill_pay_api.py
# API endpoints for bill pay services

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging

from database import get_db
from models import Account, Payee, Biller, BillPayment
from bill_pay_service import (
    BillPayService,
    BillerService,
    BillPaymentService,
    PaymentProcessingService
)
from audit_service import AuditService

router = APIRouter(prefix="/api/v1/bill-pay", tags=["Bill Pay"])
log = logging.getLogger(__name__)


# ==================== PAYEE MANAGEMENT ENDPOINTS ====================

@router.post("/payees")
async def add_payee(
    account_id: int = Query(..., gt=0),
    payee_name: str = Query(...),
    payee_type: str = Query(...),  # utility, credit_card, insurance, other
    account_number: str = Query(...),
    routing_number: Optional[str] = None,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Add a new payee for bill payments
    
    - **payee_type**: utility, credit_card, insurance, government, telecom, healthcare, other
    """
    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        result = await BillPayService.add_payee(
            db=db,
            account_id=account_id,
            payee_name=payee_name,
            payee_type=payee_type,
            account_number=account_number,
            routing_number=routing_number,
            address=address,
            phone=phone,
            created_by=current_user_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="PAYEE_ADDED",
                entity_type="Payee",
                entity_id=result["payee_id"],
                actor_id=current_user_id,
                details=f"Added payee: {payee_name}"
            )
            return {
                "success": True,
                "payee_id": result["payee_id"],
                "payee_name": payee_name,
                "status": "active"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error adding payee: {e}")
        raise HTTPException(status_code=500, detail="Failed to add payee")


@router.get("/payees")
async def list_payees(
    account_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get all payees for an account"""
    try:
        result = await BillPayService.get_payees(
            db=db,
            account_id=account_id
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error listing payees: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve payees")


@router.delete("/payees/{payee_id}")
async def remove_payee(
    payee_id: int = Query(..., gt=0),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Remove a payee"""
    try:
        result = await BillPayService.remove_payee(
            db=db,
            payee_id=payee_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="PAYEE_REMOVED",
                entity_type="Payee",
                entity_id=payee_id,
                actor_id=current_user_id,
                details="Removed payee"
            )
            return {"success": True, "payee_id": payee_id}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error removing payee: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove payee")


# ==================== BILLER ENDPOINTS ====================

@router.get("/billers")
async def get_supported_billers(
    biller_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get list of supported billers"""
    try:
        result = await BillerService.get_supported_billers(
            db=db,
            biller_type=biller_type
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error fetching billers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve billers")


@router.get("/billers/{biller_id}/delivery-estimate")
async def estimate_delivery_date(
    biller_id: int = Query(..., gt=0),
    payment_date: datetime = Query(...),
    db: Session = Depends(get_db)
):
    """Estimate delivery date for a payment to a biller"""
    try:
        result = await BillerService.estimate_delivery_date(
            db=db,
            biller_id=biller_id,
            payment_date=payment_date
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error estimating delivery: {e}")
        raise HTTPException(status_code=500, detail="Failed to estimate delivery")


# ==================== PAYMENT ENDPOINTS ====================

@router.post("/payments")
async def schedule_payment(
    account_id: int = Query(..., gt=0),
    payee_id: int = Query(..., gt=0),
    amount: float = Query(..., gt=0),
    payment_date: datetime = Query(...),
    memo: Optional[str] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Schedule a bill payment to a payee
    
    Payment will be processed on the specified date
    """
    try:
        # Verify account exists
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        result = await BillPaymentService.schedule_payment(
            db=db,
            account_id=account_id,
            payee_id=payee_id,
            amount=amount,
            payment_date=payment_date,
            memo=memo,
            created_by=current_user_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="PAYMENT_SCHEDULED",
                entity_type="BillPayment",
                entity_id=result["payment_id"],
                actor_id=current_user_id,
                details=f"Scheduled ${amount} payment"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error scheduling payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule payment")


@router.get("/payments")
async def get_payment_history(
    account_id: int = Query(..., gt=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get payment history for an account"""
    try:
        result = await BillPaymentService.get_payment_history(
            db=db,
            account_id=account_id,
            limit=limit
        )
        
        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except Exception as e:
        log.error(f"Error retrieving payment history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve history")


@router.get("/payments/{payment_id}")
async def get_payment_details(
    payment_id: int = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    """Get details of a specific payment"""
    try:
        payment = db.query(BillPayment).filter(
            BillPayment.id == payment_id
        ).first()
        
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        return {
            "success": True,
            "payment": {
                "payment_id": payment.id,
                "amount": payment.amount,
                "status": payment.status,
                "payment_date": payment.payment_date.isoformat(),
                "memo": payment.memo,
                "created_at": payment.created_at.isoformat(),
                "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
                "failure_reason": payment.failure_reason
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve payment")


@router.delete("/payments/{payment_id}")
async def cancel_payment(
    payment_id: int = Query(..., gt=0),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Cancel a scheduled payment"""
    try:
        result = await BillPaymentService.cancel_payment(
            db=db,
            payment_id=payment_id
        )
        
        if result["success"]:
            # Log to audit
            await AuditService.log_action(
                db=db,
                action="PAYMENT_CANCELLED",
                entity_type="BillPayment",
                entity_id=payment_id,
                actor_id=current_user_id,
                details="Cancelled payment"
            )
            return result
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error cancelling payment: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel payment")


# ==================== RECURRING PAYMENT ENDPOINTS ====================

@router.post("/schedules")
async def create_payment_schedule(
    account_id: int = Query(..., gt=0),
    payee_id: int = Query(..., gt=0),
    amount: float = Query(..., gt=0),
    frequency: str = Query(...),  # weekly, biweekly, monthly, quarterly, annual
    start_date: datetime = Query(...),
    end_date: Optional[datetime] = None,
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Create a recurring bill payment schedule
    
    - **frequency**: weekly, biweekly, monthly, quarterly, annual
    """
    try:
        from models import PaymentSchedule
        
        # Verify account and payee
        account = db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        payee = db.query(Payee).filter(Payee.id == payee_id).first()
        if not payee:
            raise HTTPException(status_code=404, detail="Payee not found")
        
        schedule = PaymentSchedule(
            account_id=account_id,
            payee_id=payee_id,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            status="active"
        )
        
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        
        # Log to audit
        await AuditService.log_action(
            db=db,
            action="PAYMENT_SCHEDULE_CREATED",
            entity_type="PaymentSchedule",
            entity_id=schedule.id,
            actor_id=current_user_id,
            details=f"Created {frequency} recurring payment schedule"
        )
        
        return {
            "success": True,
            "schedule_id": schedule.id,
            "frequency": frequency,
            "status": "active"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error(f"Error creating payment schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to create schedule")


@router.get("/schedules")
async def list_payment_schedules(
    account_id: int = Query(..., gt=0),
    status: Optional[str] = Query("active"),
    db: Session = Depends(get_db)
):
    """Get all payment schedules for an account"""
    try:
        from models import PaymentSchedule
        
        query = db.query(PaymentSchedule).filter(
            PaymentSchedule.account_id == account_id
        )
        
        if status:
            query = query.filter(PaymentSchedule.status == status)
        
        schedules = query.all()
        
        return {
            "success": True,
            "count": len(schedules),
            "schedules": [
                {
                    "schedule_id": s.id,
                    "payee_id": s.payee_id,
                    "amount": s.amount,
                    "frequency": s.frequency,
                    "status": s.status,
                    "start_date": s.start_date.isoformat(),
                    "end_date": s.end_date.isoformat() if s.end_date else None
                }
                for s in schedules
            ]
        }
    except Exception as e:
        log.error(f"Error listing schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve schedules")


@router.delete("/schedules/{schedule_id}")
async def cancel_payment_schedule(
    schedule_id: int = Query(..., gt=0),
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Cancel a recurring payment schedule"""
    try:
        from models import PaymentSchedule
        
        schedule = db.query(PaymentSchedule).filter(
            PaymentSchedule.id == schedule_id
        ).first()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        schedule.status = "cancelled"
        db.commit()
        
        # Log to audit
        await AuditService.log_action(
            db=db,
            action="PAYMENT_SCHEDULE_CANCELLED",
            entity_type="PaymentSchedule",
            entity_id=schedule_id,
            actor_id=current_user_id,
            details="Cancelled payment schedule"
        )
        
        return {"success": True, "schedule_id": schedule_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        log.error(f"Error cancelling schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel schedule")


# ==================== BATCH PROCESSING ENDPOINT ====================

@router.post("/process-payments")
async def process_payments_batch(
    current_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Process all due bill payments (scheduled job endpoint)
    Should be called periodically by job scheduler
    """
    try:
        # Get all payments due today
        today = datetime.utcnow()
        due_payments = db.query(BillPayment).filter(
            BillPayment.status.in_(["scheduled", "pending"]),
            BillPayment.payment_date <= today
        ).all()
        
        processed_count = 0
        failed_count = 0
        
        for payment in due_payments:
            result = await PaymentProcessingService.process_bill_payment(
                db=db,
                payment_id=payment.id
            )
            
            if result["success"]:
                processed_count += 1
            else:
                failed_count += 1
        
        # Log to audit
        await AuditService.log_action(
            db=db,
            action="BATCH_PAYMENT_PROCESSING",
            entity_type="BillPayment",
            entity_id=None,
            actor_id=current_user_id,
            details=f"Processed {processed_count} payments, {failed_count} failed"
        )
        
        return {
            "success": True,
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total": processed_count + failed_count
        }
    except Exception as e:
        log.error(f"Error processing batch payments: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch")
