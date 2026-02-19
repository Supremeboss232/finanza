# bill_pay_service.py
# Bill pay and payee management service

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging

log = logging.getLogger(__name__)


class BillPayService:
    """Service for managing payees and bill payments"""
    
    @staticmethod
    async def add_payee(
        db: Session,
        account_id: int,
        payee_name: str,
        payee_type: str,  # utility, credit_card, insurance, other
        account_number: str,
        routing_number: Optional[str] = None,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Add a payee for bill payments
        
        Args:
            payee_type: utility, credit_card, insurance, other
            account_number: Payee account number
            routing_number: For bank transfers
        
        Returns:
            {"success": bool, "payee_id": int}
        """
        try:
            from models import Payee
            
            payee = Payee(
                account_id=account_id,
                payee_name=payee_name,
                payee_type=payee_type,
                account_number=account_number,
                routing_number=routing_number,
                address=address,
                phone=phone,
                status="active",
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(payee)
            db.commit()
            db.refresh(payee)
            
            log.info(f"Payee added: {payee.id} - {payee_name}")
            
            return {
                "success": True,
                "payee_id": payee.id,
                "payee_name": payee_name,
                "status": "active"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error adding payee: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_payees(
        db: Session,
        account_id: int
    ) -> dict:
        """
        Get all payees for account
        
        Returns:
            {"success": bool, "payees": [...]}
        """
        try:
            from models import Payee
            
            payees = db.query(Payee).filter(
                Payee.account_id == account_id,
                Payee.status == "active"
            ).all()
            
            return {
                "success": True,
                "payee_count": len(payees),
                "payees": [
                    {
                        "payee_id": p.id,
                        "payee_name": p.payee_name,
                        "payee_type": p.payee_type,
                        "last_payment_date": p.last_payment_date.isoformat() if p.last_payment_date else None,
                        "created_at": p.created_at.isoformat()
                    }
                    for p in payees
                ]
            }
        except Exception as e:
            log.error(f"Error fetching payees: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def remove_payee(
        db: Session,
        payee_id: int
    ) -> dict:
        """
        Remove a payee
        
        Returns:
            {"success": bool, "payee_id": int}
        """
        try:
            from models import Payee
            
            payee = db.query(Payee).filter(Payee.id == payee_id).first()
            
            if not payee:
                return {"success": False, "error": "Payee not found"}
            
            payee.status = "inactive"
            payee.deleted_at = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Payee removed: {payee_id}")
            
            return {"success": True, "payee_id": payee_id}
        except Exception as e:
            db.rollback()
            log.error(f"Error removing payee: {e}")
            return {"success": False, "error": str(e)}


class BillPaymentService:
    """Service for scheduling and processing bill payments"""
    
    @staticmethod
    async def schedule_payment(
        db: Session,
        account_id: int,
        payee_id: int,
        amount: float,
        payment_date: datetime,
        memo: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Schedule a bill payment
        
        Returns:
            {"success": bool, "payment_id": int}
        """
        try:
            from models import BillPayment, Payee, Account
            
            # Verify payee exists
            payee = db.query(Payee).filter(Payee.id == payee_id).first()
            if not payee:
                return {"success": False, "error": "Payee not found"}
            
            # Verify account exists and has funds
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            if account.available_balance < amount:
                return {"success": False, "error": "Insufficient available balance"}
            
            # Create payment
            payment = BillPayment(
                account_id=account_id,
                payee_id=payee_id,
                amount=amount,
                payment_date=payment_date,
                status="scheduled",
                memo=memo,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(payment)
            db.commit()
            db.refresh(payment)
            
            log.info(f"Bill payment scheduled: {payment.id} to {payee_id}")
            
            return {
                "success": True,
                "payment_id": payment.id,
                "payee_id": payee_id,
                "amount": amount,
                "payment_date": payment_date.isoformat(),
                "status": "scheduled"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error scheduling payment: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_payment_history(
        db: Session,
        account_id: int,
        limit: int = 50
    ) -> dict:
        """
        Get payment history for account
        
        Returns:
            {"success": bool, "payments": [...]}
        """
        try:
            from models import BillPayment
            
            payments = db.query(BillPayment).filter(
                BillPayment.account_id == account_id
            ).order_by(BillPayment.payment_date.desc()).limit(limit).all()
            
            return {
                "success": True,
                "payment_count": len(payments),
                "payments": [
                    {
                        "payment_id": p.id,
                        "payee_id": p.payee_id,
                        "amount": p.amount,
                        "payment_date": p.payment_date.isoformat(),
                        "status": p.status,
                        "memo": p.memo
                    }
                    for p in payments
                ]
            }
        except Exception as e:
            log.error(f"Error fetching payment history: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def cancel_payment(
        db: Session,
        payment_id: int
    ) -> dict:
        """
        Cancel a scheduled payment
        
        Returns:
            {"success": bool, "payment_id": int}
        """
        try:
            from models import BillPayment
            
            payment = db.query(BillPayment).filter(
                BillPayment.id == payment_id
            ).first()
            
            if not payment:
                return {"success": False, "error": "Payment not found"}
            
            if payment.status not in ["scheduled", "pending"]:
                return {"success": False, "error": f"Cannot cancel {payment.status} payment"}
            
            payment.status = "cancelled"
            payment.cancelled_at = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Bill payment cancelled: {payment_id}")
            
            return {"success": True, "payment_id": payment_id}
        except Exception as e:
            db.rollback()
            log.error(f"Error cancelling payment: {e}")
            return {"success": False, "error": str(e)}


class BillerService:
    """Service for managing billers (supported payment recipients)"""
    
    @staticmethod
    async def get_supported_billers(
        db: Session,
        biller_type: Optional[str] = None
    ) -> dict:
        """
        Get list of supported billers
        
        Returns:
            {"success": bool, "billers": [...]}
        """
        try:
            from models import Biller
            
            query = db.query(Biller).filter(Biller.active == True)
            
            if biller_type:
                query = query.filter(Biller.biller_type == biller_type)
            
            billers = query.all()
            
            return {
                "success": True,
                "biller_count": len(billers),
                "billers": [
                    {
                        "biller_id": b.id,
                        "biller_name": b.biller_name,
                        "biller_type": b.biller_type,
                        "processing_time_days": b.processing_time_days
                    }
                    for b in billers
                ]
            }
        except Exception as e:
            log.error(f"Error fetching billers: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def estimate_delivery_date(
        db: Session,
        biller_id: int,
        payment_date: datetime
    ) -> dict:
        """
        Estimate delivery date for payment
        
        Returns:
            {"success": bool, "estimated_delivery": str}
        """
        try:
            from models import Biller
            
            biller = db.query(Biller).filter(Biller.id == biller_id).first()
            
            if not biller:
                return {"success": False, "error": "Biller not found"}
            
            # Standard processing: same day or next business day
            processing_days = biller.processing_time_days or 1
            estimated_delivery = payment_date + timedelta(days=processing_days)
            
            return {
                "success": True,
                "payment_date": payment_date.isoformat(),
                "estimated_delivery": estimated_delivery.isoformat(),
                "processing_days": processing_days
            }
        except Exception as e:
            log.error(f"Error estimating delivery: {e}")
            return {"success": False, "error": str(e)}


class PaymentProcessingService:
    """Service for processing bill payments"""
    
    @staticmethod
    async def process_bill_payment(
        db: Session,
        payment_id: int
    ) -> dict:
        """
        Process a bill payment (scheduled job)
        
        Returns:
            {"success": bool, "transaction_id": int}
        """
        try:
            from models import BillPayment, Account, Transaction, PaymentReceipt
            
            payment = db.query(BillPayment).filter(
                BillPayment.id == payment_id
            ).first()
            
            if not payment:
                return {"success": False, "error": "Payment not found"}
            
            if payment.status not in ["scheduled", "pending"]:
                return {"success": False, "error": f"Cannot process {payment.status} payment"}
            
            # Verify account and funds
            account = db.query(Account).filter(
                Account.id == payment.account_id
            ).first()
            
            if account.available_balance < payment.amount:
                payment.status = "failed"
                payment.failure_reason = "Insufficient funds"
                db.commit()
                return {"success": False, "error": "Insufficient funds"}
            
            # Debit account
            account.available_balance -= payment.amount
            account.balance -= payment.amount
            
            # Record transaction
            transaction = Transaction(
                account_id=payment.account_id,
                amount=payment.amount,
                transaction_type="bill_payment",
                status="completed",
                description=f"Bill payment to payee {payment.payee_id}",
                created_at=datetime.utcnow()
            )
            
            db.add(transaction)
            
            # Update payment
            payment.status = "processed"
            payment.processed_at = datetime.utcnow()
            payment.transaction_id = transaction.id
            
            # Create receipt
            receipt = PaymentReceipt(
                payment_id=payment.id,
                transaction_id=transaction.id,
                receipt_date=datetime.utcnow(),
                status="generated"
            )
            
            db.add(receipt)
            db.commit()
            
            log.info(f"Bill payment processed: {payment_id}")
            
            return {
                "success": True,
                "payment_id": payment_id,
                "transaction_id": transaction.id,
                "status": "processed",
                "processed_at": payment.processed_at.isoformat()
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error processing bill payment: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def handle_payment_failure(
        db: Session,
        payment_id: int,
        failure_reason: str
    ) -> dict:
        """
        Handle failed payment with retry logic
        
        Returns:
            {"success": bool, "retry_scheduled": bool}
        """
        try:
            from models import BillPayment, PaymentFailureLog
            
            payment = db.query(BillPayment).filter(
                BillPayment.id == payment_id
            ).first()
            
            if not payment:
                return {"success": False, "error": "Payment not found"}
            
            # Log failure
            failure_log = PaymentFailureLog(
                payment_id=payment_id,
                failure_reason=failure_reason,
                failure_date=datetime.utcnow(),
                retry_count=payment.retry_count + 1
            )
            
            db.add(failure_log)
            
            # Determine if should retry
            max_retries = 3
            should_retry = payment.retry_count < max_retries
            
            if should_retry:
                # Schedule retry for next day
                retry_date = datetime.utcnow() + timedelta(days=1)
                payment.next_retry_date = retry_date
                payment.status = "retry_scheduled"
                payment.retry_count += 1
            else:
                payment.status = "failed"
                payment.failure_reason = failure_reason
            
            db.commit()
            
            log.info(f"Payment failure handled: {payment_id} - {failure_reason}")
            
            return {
                "success": True,
                "payment_id": payment_id,
                "retry_scheduled": should_retry,
                "retry_count": payment.retry_count
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error handling payment failure: {e}")
            return {"success": False, "error": str(e)}
