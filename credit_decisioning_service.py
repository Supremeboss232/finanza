"""
Credit Decisioning Service - Automated lending decision engine
Integrates with credit bureaus and applies decisioning rules
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from models import User, Loan, CreditScore, LoanPayment, Delinquency, LoanHistory
import logging

log = logging.getLogger(__name__)


class CreditDecisionService:
    """Main credit decisioning engine"""
    
    # Score thresholds
    EXCELLENT_SCORE = 750
    GOOD_SCORE = 700
    FAIR_SCORE = 650
    POOR_SCORE = 600
    
    # Debt-to-Income ratio limits
    MAX_DTI_APPROVED = 0.43
    MAX_DTI_MANUAL_REVIEW = 0.50
    
    @staticmethod
    async def make_decision(
        db: Session,
        user_id: int,
        loan_amount: float,
        loan_type: str,
        term_months: int = 60
    ) -> Dict:
        """
        Make automated credit decision
        Returns: approve, deny, or manual_review
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Verify KYC completed
            if user.kyc_status != "approved":
                return {
                    "success": True,
                    "decision": "deny",
                    "reason": "KYC not approved"
                }
            
            # Pull credit score
            credit_score = await CreditBureauService.pull_credit_score(db, user_id)
            if not credit_score:
                return {
                    "success": True,
                    "decision": "deny",
                    "reason": "Unable to pull credit score"
                }
            
            # Calculate DTI
            dti = await CreditDecisionService.calculate_dti(db, user_id, loan_amount, term_months)
            
            # Calculate interest rate
            interest_rate = await CreditDecisionService.calculate_interest_rate(credit_score, loan_type)
            
            # Apply decision rules
            decision_result = await CreditDecisionService.apply_rules(
                db, user_id, credit_score, dti, loan_amount, loan_type
            )
            
            decision_result["credit_score"] = credit_score
            decision_result["dti"] = dti
            decision_result["interest_rate"] = interest_rate
            
            log.info(f"Credit decision for user {user_id}: {decision_result['decision']}")
            return {"success": True, **decision_result}
            
        except Exception as e:
            log.error(f"Error making credit decision: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def calculate_dti(
        db: Session,
        user_id: int,
        new_loan_amount: float,
        term_months: int
    ) -> float:
        """
        Calculate Debt-to-Income ratio
        DTI = (total monthly debt payments) / (gross monthly income)
        """
        try:
            # Get existing loans and monthly payments
            existing_loans = db.query(Loan).filter(
                Loan.user_id == user_id,
                Loan.status.in_(["approved", "active"])
            ).all()
            
            total_monthly_debt = 0
            for loan in existing_loans:
                total_monthly_debt += loan.monthly_payment or 0
            
            # Calculate new loan monthly payment
            monthly_rate = 0.05 / 12  # Example 5% annual
            num_payments = term_months
            new_monthly_payment = new_loan_amount * (
                monthly_rate * (1 + monthly_rate) ** num_payments
            ) / ((1 + monthly_rate) ** num_payments - 1)
            
            total_monthly_debt += new_monthly_payment
            
            # Assume gross monthly income (would come from income verification in real system)
            gross_monthly_income = 5000  # TODO: Pull from verified income
            
            if gross_monthly_income <= 0:
                return 0.50  # Max ratio if no income
            
            dti = total_monthly_debt / gross_monthly_income
            return round(dti, 3)
        except Exception as e:
            log.error(f"Error calculating DTI: {str(e)}")
            return 0.50
    
    @staticmethod
    async def calculate_interest_rate(credit_score: int, loan_type: str) -> float:
        """
        Calculate interest rate based on credit score
        Rate varies by loan type and credit profile
        """
        base_rates = {
            "personal": 0.10,  # 10% base
            "auto": 0.06,      # 6% base
            "mortgage": 0.04,  # 4% base
            "business": 0.12   # 12% base
        }
        
        base_rate = base_rates.get(loan_type, 0.10)
        
        # Adjust rate based on credit score
        if credit_score >= CreditDecisionService.EXCELLENT_SCORE:
            adjustment = -0.02  # -2%
        elif credit_score >= CreditDecisionService.GOOD_SCORE:
            adjustment = -0.01  # -1%
        elif credit_score >= CreditDecisionService.FAIR_SCORE:
            adjustment = 0.00   # 0%
        elif credit_score >= CreditDecisionService.POOR_SCORE:
            adjustment = 0.02   # +2%
        else:
            adjustment = 0.04   # +4%
        
        rate = max(base_rate + adjustment, 0.01)  # Minimum 1%
        return round(rate, 4)
    
    @staticmethod
    async def apply_rules(
        db: Session,
        user_id: int,
        credit_score: int,
        dti: float,
        loan_amount: float,
        loan_type: str
    ) -> Dict:
        """
        Apply automated decisioning rules
        Returns: decision (approve/deny/manual_review)
        """
        reasons = []
        
        # Rule 1: Minimum credit score
        if credit_score < CreditDecisionService.POOR_SCORE:
            return {
                "decision": "deny",
                "reason": f"Credit score {credit_score} below minimum {CreditDecisionService.POOR_SCORE}",
                "manual_review": False
            }
        
        # Rule 2: DTI limits
        if dti > CreditDecisionService.MAX_DTI_MANUAL_REVIEW:
            return {
                "decision": "deny",
                "reason": f"DTI {dti:.1%} exceeds maximum {CreditDecisionService.MAX_DTI_MANUAL_REVIEW:.1%}",
                "manual_review": False
            }
        elif dti > CreditDecisionService.MAX_DTI_APPROVED:
            return {
                "decision": "manual_review",
                "reason": f"DTI {dti:.1%} requires manual review (approved limit: {CreditDecisionService.MAX_DTI_APPROVED:.1%})",
                "manual_review": True
            }
        
        # Rule 3: Check for delinquencies
        delinquency = db.query(Delinquency).filter(
            Delinquency.loan_id.in_(
                db.query(Loan.id).filter(Loan.user_id == user_id)
            ),
            Delinquency.days_past_due > 0
        ).first()
        
        if delinquency and delinquency.days_past_due > 90:
            return {
                "decision": "deny",
                "reason": f"Existing delinquency: {delinquency.days_past_due} days past due",
                "manual_review": False
            }
        elif delinquency and delinquency.days_past_due > 30:
            return {
                "decision": "manual_review",
                "reason": f"Existing delinquency: {delinquency.days_past_due} days past due",
                "manual_review": True
            }
        
        # Rule 4: Loan amount limits by score
        max_loan_amount = CreditDecisionService.get_max_loan_amount(credit_score, loan_type)
        if loan_amount > max_loan_amount:
            return {
                "decision": "manual_review",
                "reason": f"Loan amount ${loan_amount:,.0f} exceeds auto-approval limit ${max_loan_amount:,.0f}",
                "manual_review": True
            }
        
        # All rules passed - approve
        return {
            "decision": "approve",
            "reason": "All automated rules satisfied",
            "manual_review": False
        }
    
    @staticmethod
    def get_max_loan_amount(credit_score: int, loan_type: str) -> float:
        """Get maximum loan amount by credit profile"""
        type_limits = {
            "personal": 50000,
            "auto": 75000,
            "mortgage": 500000,
            "business": 100000
        }
        
        base_limit = type_limits.get(loan_type, 50000)
        
        if credit_score >= CreditDecisionService.EXCELLENT_SCORE:
            return base_limit * 1.5  # +50%
        elif credit_score >= CreditDecisionService.GOOD_SCORE:
            return base_limit
        elif credit_score >= CreditDecisionService.FAIR_SCORE:
            return base_limit * 0.75  # -25%
        else:
            return base_limit * 0.5  # -50%


class CreditBureauService:
    """Credit bureau integration (Equifax, Experian, TransUnion)"""
    
    # Mock bureau APIs - in production these would call real APIs
    BUREAU_REFRESH_DAYS = 30
    
    @staticmethod
    async def pull_credit_score(db: Session, user_id: int) -> Optional[int]:
        """
        Pull credit score from bureaus
        Returns most recent score or None if unable to retrieve
        """
        try:
            # Check if recent score exists
            recent_score = db.query(CreditScore).filter(
                CreditScore.user_id == user_id,
                CreditScore.expires_date > datetime.utcnow().date()
            ).order_by(CreditScore.pulled_date.desc()).first()
            
            if recent_score:
                return recent_score.score
            
            # Pull new score from bureau
            # TODO: Call actual bureau APIs (Equifax, Experian, TransUnion)
            # For now, return mock score
            mock_score = await CreditBureauService.get_mock_score(db, user_id)
            
            # Store score
            credit_score = CreditScore(
                user_id=user_id,
                bureau="equifax",  # TODO: Pull from all 3
                score=mock_score,
                pulled_date=datetime.utcnow().date(),
                expires_date=datetime.utcnow().date() + timedelta(days=CreditBureauService.BUREAU_REFRESH_DAYS)
            )
            db.add(credit_score)
            db.commit()
            
            log.info(f"Credit score pulled for user {user_id}: {mock_score}")
            return mock_score
        except Exception as e:
            log.error(f"Error pulling credit score: {str(e)}")
            return None
    
    @staticmethod
    async def get_mock_score(db: Session, user_id: int) -> int:
        """
        Generate mock credit score based on transaction history
        In production, would call actual bureau APIs
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return 650  # Default score
            
            # Score based on account age, payment history
            base_score = 650
            
            # Adjust for existing loans
            existing_loans = db.query(Loan).filter(Loan.user_id == user_id).all()
            if existing_loans:
                base_score += len(existing_loans) * 10  # +10 per loan
            
            # Adjust for delinquencies
            delinquencies = db.query(Delinquency).filter(
                Delinquency.loan_id.in_(
                    db.query(Loan.id).filter(Loan.user_id == user_id)
                )
            ).all()
            
            for del_record in delinquencies:
                if del_record.days_past_due > 0:
                    base_score -= (del_record.days_past_due // 30) * 50
            
            # Cap at reasonable range (300-850)
            return max(300, min(850, base_score))
        except Exception as e:
            log.error(f"Error generating mock score: {str(e)}")
            return 650


class AmortizationService:
    """Loan amortization schedule generation"""
    
    @staticmethod
    async def generate_schedule(
        db: Session,
        loan_id: int,
        principal: float,
        annual_rate: float,
        term_months: int
    ) -> Dict:
        """Generate amortization schedule"""
        try:
            monthly_rate = annual_rate / 12
            num_payments = term_months
            
            # Calculate monthly payment using standard formula
            if monthly_rate == 0:
                monthly_payment = principal / num_payments
            else:
                monthly_payment = principal * (
                    monthly_rate * (1 + monthly_rate) ** num_payments
                ) / ((1 + monthly_rate) ** num_payments - 1)
            
            # Generate schedule
            remaining_balance = principal
            payment_schedule = []
            start_date = datetime.utcnow().date()
            
            for payment_num in range(1, term_months + 1):
                interest_payment = remaining_balance * monthly_rate
                principal_payment = monthly_payment - interest_payment
                remaining_balance -= principal_payment
                
                payment_date = start_date + timedelta(days=30 * payment_num)
                due_date = payment_date + timedelta(days=15)
                
                loan_payment = LoanPayment(
                    loan_id=loan_id,
                    payment_number=payment_num,
                    scheduled_date=payment_date,
                    due_date=due_date,
                    amount=monthly_payment,
                    principal_amount=principal_payment,
                    interest_amount=interest_payment,
                    status="scheduled"
                )
                db.add(loan_payment)
                payment_schedule.append({
                    "payment_number": payment_num,
                    "payment_date": payment_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "payment_amount": round(monthly_payment, 2),
                    "principal": round(principal_payment, 2),
                    "interest": round(interest_payment, 2),
                    "remaining_balance": round(max(0, remaining_balance), 2)
                })
            
            db.commit()
            log.info(f"Amortization schedule generated for loan {loan_id}: {term_months} payments")
            return {
                "success": True,
                "monthly_payment": round(monthly_payment, 2),
                "schedule": payment_schedule
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error generating amortization schedule: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def record_payment(
        db: Session,
        loan_id: int,
        payment_amount: float,
        payment_date: datetime
    ) -> Dict:
        """Record loan payment and update schedule"""
        try:
            # Get next scheduled payment
            payment = db.query(LoanPayment).filter(
                LoanPayment.loan_id == loan_id,
                LoanPayment.status == "scheduled"
            ).order_by(LoanPayment.payment_number).first()
            
            if not payment:
                return {"success": False, "error": "No scheduled payments found"}
            
            # Update payment record
            payment.status = "paid"
            payment.paid_date = payment_date.date()
            payment.received_amount = payment_amount
            
            # Update loan balance
            loan = db.query(Loan).filter(Loan.id == loan_id).first()
            if loan:
                loan.remaining_balance = max(0, loan.remaining_balance - payment.principal_amount)
                loan.paid_amount = (loan.paid_amount or 0) + payment.principal_amount
            
            # Record in loan history
            history = LoanHistory(
                loan_id=loan_id,
                action="payment_made",
                old_balance=loan.remaining_balance + payment.principal_amount,
                new_balance=loan.remaining_balance,
                changed_by="system"
            )
            db.add(history)
            db.commit()
            
            log.info(f"Payment recorded for loan {loan_id}: ${payment_amount:,.2f}")
            return {"success": True, "payment_id": payment.id}
        except Exception as e:
            db.rollback()
            log.error(f"Error recording loan payment: {str(e)}")
            return {"success": False, "error": str(e)}
