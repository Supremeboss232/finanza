"""
Loan Origination Service

Handles the complete loan lifecycle:
1. Application submission
2. Credit decisioning (automated scoring)
3. Underwriting review
4. Approval/Denial
5. Funding disbursement
6. Repayment scheduling
"""

from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
import json
import logging

from models import User, Loan, Transaction, Ledger, Account, AuditLog

logger = logging.getLogger(__name__)


class LoanOriginationService:
    """Service for managing loan origination workflow."""

    @staticmethod
    async def submit_application(
        db: AsyncSession,
        user_id: int,
        loan_type: str,
        amount: Decimal,
        term_months: int,
        purpose: str,
    ) -> Dict:
        """
        Submit a loan application.
        
        Loan Types: personal, auto, home, student, business
        """
        try:
            user = await db.get(User, user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            if user.kyc_status != "approved":
                return {"success": False, "error": "KYC approval required"}

            # Validate amount and term
            if amount <= 0 or amount > Decimal("1000000"):
                return {"success": False, "error": "Invalid loan amount"}

            if term_months < 6 or term_months > 360:
                return {"success": False, "error": "Term must be between 6-360 months"}

            # Create loan record in "application" status
            loan = Loan(
                user_id=user_id,
                loan_type=loan_type,
                amount=amount,
                remaining_balance=amount,
                interest_rate=Decimal("0"),  # Set after credit decisioning
                term_months=term_months,
                purpose=purpose,
                status="application",
            )
            db.add(loan)
            await db.flush()

            logger.info(f"Loan application {loan.id} submitted by user {user_id}: ${amount} {loan_type}")

            return {
                "success": True,
                "loan_id": loan.id,
                "status": "application",
                "amount": float(amount),
                "term_months": term_months,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Loan application failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def perform_credit_decisioning(
        db: AsyncSession,
        loan_id: int,
    ) -> Dict:
        """
        Automated credit decisioning.
        
        Simplified model: score based on KYC status, account history, requested amount.
        In production: integrate with credit bureau APIs.
        """
        try:
            loan = await db.get(Loan, loan_id)
            if not loan:
                return {"success": False, "error": "Loan not found"}

            if loan.status != "application":
                return {"success": False, "error": f"Cannot score loan in status {loan.status}"}

            user = await db.get(User, loan.user_id)
            if not user:
                return {"success": False, "error": "User not found"}

            # Simple credit scoring (0-850)
            score = 650  # Base score

            # KYC bonus
            if user.kyc_status == "approved":
                score += 100

            # Adjust for loan type
            type_adjustment = {
                "personal": 0,
                "auto": 20,
                "home": 50,
                "student": 30,
                "business": -20,
            }
            score += type_adjustment.get(loan.loan_type, 0)

            # Adjust for amount (smaller = safer)
            if loan.amount < Decimal("5000"):
                score += 50
            elif loan.amount < Decimal("50000"):
                score += 25
            elif loan.amount > Decimal("200000"):
                score -= 50

            score = min(850, max(300, score))  # Clamp 300-850

            # Determine interest rate based on score
            if score >= 750:
                interest_rate = Decimal("4.5")
            elif score >= 700:
                interest_rate = Decimal("6.5")
            elif score >= 650:
                interest_rate = Decimal("8.5")
            elif score >= 600:
                interest_rate = Decimal("10.5")
            else:
                interest_rate = Decimal("12.5")

            # Move to underwriting
            loan.status = "underwriting"
            loan.interest_rate = interest_rate
            db.add(loan)
            await db.commit()

            logger.info(f"Loan {loan_id} scored: {score} (rate: {interest_rate}%)")

            return {
                "success": True,
                "loan_id": loan_id,
                "credit_score": score,
                "interest_rate": float(interest_rate),
                "status": "underwriting",
                "recommendation": "approve" if score >= 600 else "deny",
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Credit decisioning failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def underwrite_loan(
        db: AsyncSession,
        loan_id: int,
        admin_id: int,
        approved: bool,
        notes: str = "",
    ) -> Dict:
        """Admin underwriting decision: approve or deny."""
        try:
            loan = await db.get(Loan, loan_id)
            if not loan:
                return {"success": False, "error": "Loan not found"}

            if loan.status != "underwriting":
                return {"success": False, "error": f"Cannot underwrite loan in status {loan.status}"}

            admin = await db.get(User, admin_id)
            if not admin or not admin.is_admin:
                return {"success": False, "error": "Admin verification failed"}

            if approved:
                loan.status = "approved"
            else:
                loan.status = "denied"

            # Create audit log
            audit = AuditLog(
                admin_id=admin_id,
                user_id=loan.user_id,
                action_type="loan_underwriting",
                reason=f"Loan underwriting decision: {'approved' if approved else 'denied'}",
                details=json.dumps({
                    "loan_id": loan_id,
                    "amount": float(loan.amount),
                    "term_months": loan.term_months,
                    "interest_rate": float(loan.interest_rate),
                    "notes": notes,
                }),
                status="success",
            )
            db.add(audit)
            db.add(loan)
            await db.commit()

            logger.info(f"Loan {loan_id} underwriting: {'APPROVED' if approved else 'DENIED'}")

            return {
                "success": True,
                "loan_id": loan_id,
                "status": loan.status,
                "amount": float(loan.amount),
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Loan underwriting failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def disburse_funds(
        db: AsyncSession,
        loan_id: int,
        to_account_id: int,
    ) -> Dict:
        """
        Disburse approved loan funds.
        
        Creates ledger entry from system account to user account.
        """
        try:
            loan = await db.get(Loan, loan_id)
            if not loan:
                return {"success": False, "error": "Loan not found"}

            if loan.status != "approved":
                return {"success": False, "error": f"Cannot disburse loan in status {loan.status}"}

            account = await db.get(Account, to_account_id)
            if not account or account.owner_id != loan.user_id:
                return {"success": False, "error": "Invalid disbursement account"}

            # Create transaction
            transaction = Transaction(
                user_id=loan.user_id,
                account_id=to_account_id,
                transaction_type="loan_disbursement",
                amount=loan.amount,
                direction="credit",
                status="completed",
                description=f"Loan disbursement: {loan.loan_type} for {loan.purpose}",
                reference_number=f"LOAN-{loan_id}",
            )
            db.add(transaction)
            await db.flush()

            # Create double-entry ledger (system → user)
            now = datetime.utcnow()

            # System debit
            debit = Ledger(
                user_id=1,  # System account
                entry_type="debit",
                amount=loan.amount,
                transaction_id=transaction.id,
                source_user_id=1,
                destination_user_id=loan.user_id,
                description=f"Debit: Loan {loan.loan_type} disbursement",
                reference_number=f"LOAN-{loan_id}",
                status="posted",
                posted_at=now,
            )
            db.add(debit)
            await db.flush()

            # User credit
            credit = Ledger(
                user_id=loan.user_id,
                entry_type="credit",
                amount=loan.amount,
                transaction_id=transaction.id,
                related_entry_id=debit.id,
                source_user_id=1,
                destination_user_id=loan.user_id,
                description=f"Credit: Loan {loan.loan_type} disbursement",
                reference_number=f"LOAN-{loan_id}",
                status="posted",
                posted_at=now,
            )
            db.add(credit)
            await db.flush()

            # Link entries
            debit.related_entry_id = credit.id
            db.add(debit)

            # Update account balance
            account.balance = (account.balance or 0) + loan.amount
            db.add(account)

            # Update loan status and calculate monthly payment
            loan.status = "active"
            loan.approved_at = datetime.utcnow()

            # Calculate monthly payment: P * [r(1+r)^n] / [(1+r)^n - 1]
            monthly_rate = loan.interest_rate / 100 / 12
            num_payments = loan.term_months
            if monthly_rate > 0:
                payment_factor = (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
                loan.monthly_payment = loan.amount * payment_factor
            else:
                loan.monthly_payment = loan.amount / num_payments

            db.add(loan)
            await db.commit()

            logger.info(f"Loan {loan_id} disbursed: ${loan.amount} to account {to_account_id}")

            return {
                "success": True,
                "loan_id": loan_id,
                "status": "active",
                "amount": float(loan.amount),
                "monthly_payment": float(loan.monthly_payment),
                "transaction_id": transaction.id,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Loan disbursement failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def record_payment(
        db: AsyncSession,
        loan_id: int,
        amount: Decimal,
    ) -> Dict:
        """Record a loan payment."""
        try:
            loan = await db.get(Loan, loan_id)
            if not loan:
                return {"success": False, "error": "Loan not found"}

            if loan.status != "active":
                return {"success": False, "error": f"Cannot pay loan in status {loan.status}"}

            # Create transaction for payment
            result = await db.execute(
                select(Account).where(Account.owner_id == loan.user_id).limit(1)
            )
            account = result.scalar_one_or_none()

            if not account:
                return {"success": False, "error": "User account not found"}

            transaction = Transaction(
                user_id=loan.user_id,
                account_id=account.id,
                transaction_type="loan_payment",
                amount=amount,
                direction="debit",
                status="completed",
                description=f"Loan payment for {loan.loan_type}",
                reference_number=f"LOAN-PAY-{loan_id}",
            )
            db.add(transaction)
            await db.flush()

            # Create ledger entries (user debit, system credit)
            now = datetime.utcnow()

            debit = Ledger(
                user_id=loan.user_id,
                entry_type="debit",
                amount=amount,
                transaction_id=transaction.id,
                source_user_id=loan.user_id,
                destination_user_id=1,
                description="Debit: Loan payment",
                reference_number=f"LOAN-PAY-{loan_id}",
                status="posted",
                posted_at=now,
            )
            db.add(debit)
            await db.flush()

            credit = Ledger(
                user_id=1,
                entry_type="credit",
                amount=amount,
                transaction_id=transaction.id,
                related_entry_id=debit.id,
                source_user_id=loan.user_id,
                destination_user_id=1,
                description="Credit: Loan payment received",
                reference_number=f"LOAN-PAY-{loan_id}",
                status="posted",
                posted_at=now,
            )
            db.add(credit)
            await db.flush()

            debit.related_entry_id = credit.id
            db.add(debit)

            # Update loan
            loan.remaining_balance = max(Decimal("0"), loan.remaining_balance - amount)
            loan.paid_amount = (loan.paid_amount or 0) + amount

            if loan.remaining_balance == 0:
                loan.status = "paid_off"

            db.add(loan)

            # Update account balance
            account.balance = (account.balance or 0) - amount
            db.add(account)

            await db.commit()

            logger.info(f"Loan {loan_id} payment recorded: ${amount}")

            return {
                "success": True,
                "loan_id": loan_id,
                "amount_paid": float(amount),
                "remaining_balance": float(loan.remaining_balance),
                "status": loan.status,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Loan payment failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_loan_details(db: AsyncSession, loan_id: int) -> Dict:
        """Get full loan details."""
        try:
            loan = await db.get(Loan, loan_id)
            if not loan:
                return {"success": False, "error": "Loan not found"}

            return {
                "success": True,
                "loan_id": loan.id,
                "user_id": loan.user_id,
                "loan_type": loan.loan_type,
                "amount": float(loan.amount),
                "remaining_balance": float(loan.remaining_balance),
                "paid_amount": float(loan.paid_amount),
                "monthly_payment": float(loan.monthly_payment),
                "interest_rate": float(loan.interest_rate),
                "term_months": loan.term_months,
                "status": loan.status,
                "purpose": loan.purpose,
                "approved_at": loan.approved_at.isoformat() if loan.approved_at else None,
                "created_at": loan.created_at.isoformat() if loan.created_at else None,
            }

        except Exception as e:
            logger.error(f"Failed to get loan details: {str(e)}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def get_user_loans(db: AsyncSession, user_id: int) -> Dict:
        """Get all loans for a user."""
        try:
            result = await db.execute(
                select(Loan).where(Loan.user_id == user_id).order_by(Loan.created_at.desc())
            )
            loans = result.scalars().all()

            return {
                "success": True,
                "count": len(loans),
                "loans": [
                    {
                        "loan_id": loan.id,
                        "loan_type": loan.loan_type,
                        "amount": float(loan.amount),
                        "remaining_balance": float(loan.remaining_balance),
                        "monthly_payment": float(loan.monthly_payment),
                        "interest_rate": float(loan.interest_rate),
                        "status": loan.status,
                        "created_at": loan.created_at.isoformat() if loan.created_at else None,
                    }
                    for loan in loans
                ],
            }

        except Exception as e:
            logger.error(f"Failed to get user loans: {str(e)}")
            return {"success": False, "error": str(e)}
