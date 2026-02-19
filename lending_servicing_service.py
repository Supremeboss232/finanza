# lending_servicing_service.py
# Loan servicing, collections, modifications, prepayments, forbearance

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
from models import (
    Loan, LoanPayment, LoanModification, LoanCollection, Forbearance,
    ChargeOff, LoanPaymentSchedule, Prepayment, CollectionContact,
    Delinquency, Transaction, Account, User
)


class LoanServicingService:
    """Core loan servicing operations"""
    
    @staticmethod
    async def apply_payment(
        db: Session,
        loan_id: int,
        payment_amount: float,
        payment_date: Optional[datetime] = None
    ) -> Dict:
        """Apply payment to loan"""
        try:
            if payment_date is None:
                payment_date = datetime.utcnow()
            
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Calculate interest owed
            daily_rate = loan.interest_rate / 365 / 100
            days_since_payment = (payment_date - loan.last_payment_date).days if loan.last_payment_date else 0
            interest_owed = loan.principal_balance * daily_rate * days_since_payment
            
            # Apply payment: interest first, then principal
            interest_portion = min(interest_owed, payment_amount)
            principal_portion = payment_amount - interest_portion
            
            loan.principal_balance -= principal_portion
            loan.last_payment_date = payment_date
            
            # Record payment in schedule
            payment_record = LoanPayment(
                loan_id=loan_id,
                payment_date=payment_date,
                principal_payment=principal_portion,
                interest_payment=interest_portion,
                total_payment=payment_amount,
                balance_after=loan.principal_balance,
                payment_status="paid"
            )
            
            # Update delinquency status
            delinquency = db.query(Delinquency).filter(
                Delinquency.loan_id == loan_id
            ).first()
            
            if delinquency:
                delinquency.days_past_due = 0
                delinquency.delinquency_status = "current"
                delinquency.last_payment_date = payment_date
            
            db.add(payment_record)
            db.commit()
            
            return {
                "success": True,
                "loan_id": loan_id,
                "payment_amount": payment_amount,
                "principal_portion": principal_portion,
                "interest_portion": interest_owed,
                "remaining_balance": loan.principal_balance,
                "payment_date": payment_date.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def calculate_interest(
        db: Session,
        loan_id: int,
        as_of_date: Optional[datetime] = None
    ) -> Dict:
        """Calculate accrued interest"""
        try:
            if as_of_date is None:
                as_of_date = datetime.utcnow()
            
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Daily interest calculation
            daily_rate = loan.interest_rate / 365 / 100
            days_since_payment = (as_of_date - loan.last_payment_date).days if loan.last_payment_date else 0
            accrued_interest = loan.principal_balance * daily_rate * days_since_payment
            
            return {
                "success": True,
                "loan_id": loan_id,
                "principal_balance": loan.principal_balance,
                "interest_rate": loan.interest_rate,
                "days_since_payment": days_since_payment,
                "accrued_interest": accrued_interest,
                "as_of_date": as_of_date.isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def check_delinquency(db: Session, loan_id: int) -> Dict:
        """Check and update delinquency status"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            delinquency = db.query(Delinquency).filter(
                Delinquency.loan_id == loan_id
            ).first()
            
            if not delinquency:
                return {"success": True, "delinquency_status": "current"}
            
            # Get next scheduled payment date
            next_payment = db.query(LoanPaymentSchedule).filter(
                and_(
                    LoanPaymentSchedule.loan_id == loan_id,
                    LoanPaymentSchedule.payment_status == "pending"
                )
            ).order_by(LoanPaymentSchedule.scheduled_date).first()
            
            if not next_payment:
                return {"success": True, "delinquency_status": "current"}
            
            days_past_due = (datetime.utcnow() - next_payment.scheduled_date).days
            
            if days_past_due <= 0:
                status = "current"
            elif days_past_due <= 30:
                status = "30_days"
            elif days_past_due <= 60:
                status = "60_days"
            elif days_past_due <= 90:
                status = "90_days"
            else:
                status = "charged_off"
            
            delinquency.days_past_due = max(0, days_past_due)
            delinquency.delinquency_status = status
            
            db.commit()
            
            return {
                "success": True,
                "loan_id": loan_id,
                "delinquency_status": status,
                "days_past_due": max(0, days_past_due),
                "next_payment_date": next_payment.scheduled_date.isoformat() if next_payment else None
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class LoanModificationService:
    """Loan modification and restructuring"""
    
    @staticmethod
    async def request_modification(
        db: Session,
        loan_id: int,
        modification_type: str,
        reason: str,
        requested_by: int
    ) -> Dict:
        """Request loan modification"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            modification = LoanModification(
                loan_id=loan_id,
                modification_type=modification_type,
                reason=reason,
                requested_by=requested_by,
                old_terms=json.dumps({
                    "principal": loan.principal_balance,
                    "rate": loan.interest_rate,
                    "term_months": loan.loan_term_months
                })
            )
            
            db.add(modification)
            db.commit()
            
            return {
                "success": True,
                "modification_id": modification.id,
                "modification_type": modification_type,
                "status": "pending"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def approve_modification(
        db: Session,
        modification_id: int,
        approved_by: int
    ) -> Dict:
        """Approve and apply modification"""
        try:
            modification = db.query(LoanModification).filter(
                LoanModification.id == modification_id
            ).first()
            
            if not modification:
                return {"success": False, "error": "Modification not found"}
            
            loan = db.query(Loan).filter(Loan.id == modification.loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            modification.approved_by = approved_by
            modification.approved_at = datetime.utcnow()
            modification.effective_date = datetime.utcnow()
            
            # Apply modification based on type
            if modification.modification_type == "rate_reduction":
                # Reduce rate by 1-2%
                old_rate = loan.interest_rate
                loan.interest_rate = max(0, loan.interest_rate - 1.5)
                modification.new_terms = json.dumps({
                    "principal": loan.principal_balance,
                    "rate": loan.interest_rate,
                    "term_months": loan.loan_term_months,
                    "old_rate": old_rate
                })
            elif modification.modification_type == "term_extension":
                # Extend term by 12 months
                old_term = loan.loan_term_months
                loan.loan_term_months += 12
                modification.new_terms = json.dumps({
                    "principal": loan.principal_balance,
                    "rate": loan.interest_rate,
                    "term_months": loan.loan_term_months,
                    "old_term": old_term
                })
            
            db.commit()
            
            return {
                "success": True,
                "modification_id": modification_id,
                "status": "approved",
                "new_rate": loan.interest_rate,
                "new_term": loan.loan_term_months
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class CollectionsService:
    """Collections and delinquency management"""
    
    @staticmethod
    async def escalate_to_collections(
        db: Session,
        loan_id: int,
        reason: str
    ) -> Dict:
        """Move loan to collections"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            collection = LoanCollection(
                loan_id=loan_id,
                collection_status="120_day",
                principal_past_due=loan.principal_balance,
                interest_past_due=0.0,
                collection_attempts=0
            )
            
            db.add(collection)
            db.commit()
            
            return {
                "success": True,
                "collection_id": collection.id,
                "status": "escalated"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def log_collection_attempt(
        db: Session,
        collection_id: int,
        contact_method: str,
        contact_result: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Log collection contact attempt"""
        try:
            collection = db.query(LoanCollection).filter(
                LoanCollection.id == collection_id
            ).first()
            
            if not collection:
                return {"success": False, "error": "Collection not found"}
            
            contact = CollectionContact(
                collection_id=collection_id,
                contact_method=contact_method,
                contact_result=contact_result,
                notes=notes
            )
            
            collection.collection_attempts += 1
            collection.last_collection_attempt = datetime.utcnow()
            
            db.add(contact)
            db.commit()
            
            return {
                "success": True,
                "contact_id": contact.id,
                "attempts_count": collection.collection_attempts
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def charge_off_loan(
        db: Session,
        loan_id: int,
        principal_amount: float,
        interest_amount: float
    ) -> Dict:
        """Charge off a loan"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            charge_off = ChargeOff(
                loan_id=loan_id,
                principal_charged_off=principal_amount,
                accrued_interest_charged_off=interest_amount,
                recovery_status="open"
            )
            
            loan.status = "charged_off"
            
            db.add(charge_off)
            db.commit()
            
            return {
                "success": True,
                "charge_off_id": charge_off.id,
                "charge_off_date": charge_off.charge_off_date.isoformat(),
                "principal_charged_off": principal_amount,
                "interest_charged_off": interest_amount
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class PrepaymentService:
    """Prepayment handling"""
    
    @staticmethod
    async def accept_prepayment(
        db: Session,
        loan_id: int,
        prepayment_amount: float,
        prepayment_type: str,
        applied_by: int
    ) -> Dict:
        """Accept and apply prepayment"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            # Calculate interest savings
            daily_rate = loan.interest_rate / 365 / 100
            remaining_days = loan.loan_term_months * 30
            interest_saved = prepayment_amount * daily_rate * remaining_days
            
            # Apply prepayment to principal
            loan.principal_balance -= prepayment_amount
            
            # Calculate new maturity date
            old_maturity = loan.maturity_date
            months_saved = int((prepayment_amount / (loan.principal_balance + prepayment_amount)) * loan.loan_term_months)
            new_maturity = old_maturity - timedelta(days=months_saved * 30)
            
            prepayment = Prepayment(
                loan_id=loan_id,
                prepayment_amount=prepayment_amount,
                prepayment_type=prepayment_type,
                principal_reduction=prepayment_amount,
                interest_saved=interest_saved,
                new_maturity_date=new_maturity,
                applied_by=applied_by
            )
            
            db.add(prepayment)
            db.commit()
            
            return {
                "success": True,
                "prepayment_id": prepayment.id,
                "prepayment_amount": prepayment_amount,
                "interest_saved": interest_saved,
                "new_principal_balance": loan.principal_balance,
                "new_maturity_date": new_maturity.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class ForbearanceService:
    """Forbearance and deferment management"""
    
    @staticmethod
    async def request_forbearance(
        db: Session,
        loan_id: int,
        forbearance_type: str,
        duration_months: int,
        reason: str,
        approved_by: int
    ) -> Dict:
        """Request and approve forbearance"""
        try:
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            
            if not loan:
                return {"success": False, "error": "Loan not found"}
            
            start_date = datetime.utcnow()
            end_date = start_date + timedelta(days=duration_months * 30)
            payment_resume_date = end_date + timedelta(days=1)
            
            forbearance = Forbearance(
                loan_id=loan_id,
                forbearance_type=forbearance_type,
                start_date=start_date,
                end_date=end_date,
                payment_resume_date=payment_resume_date,
                accrued_interest_capitalization=True,
                reason=reason,
                approved_by=approved_by
            )
            
            db.add(forbearance)
            db.commit()
            
            return {
                "success": True,
                "forbearance_id": forbearance.id,
                "forbearance_type": forbearance_type,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "payment_resume_date": payment_resume_date.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
