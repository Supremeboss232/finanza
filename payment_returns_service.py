# payment_returns_service.py
# ACH returns, NSF handling, disputes, exceptions

from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Dict, Optional
from models import (
    ACHReturn, NSFManagement, PaymentException, TransactionDispute,
    ReturnProcessing, Transaction, Account, User
)


class ACHReturnService:
    """ACH return processing"""
    
    # NACHA return codes
    RETURN_CODES = {
        "R01": "Insufficient Funds",
        "R02": "Account Closed",
        "R03": "No Account/Unable to Locate Account",
        "R04": "Invalid Account Number Structure",
        "R05": "Unauthorized User-Initiated Entry",
        "R07": "Authorization Revoked",
        "R08": "Payment Stopped",
        "R09": "Uncollected Funds",
        "R10": "Customer Advises Unauthorized, Improper, Ineligible",
        "R11": "Check Digit Error",
        "R13": "Invalid ACH Routing Number",
        "R14": "Representative Payee Deceased or Unable to Continue",
        "R15": "Beneficiary or Account Holder Deceased",
        "R16": "Account Frozen",
        "R17": "Credit Frozen",
        "R20": "Non-Transaction Account",
        "R23": "Credit Entry Refused by Receiver",
        "R29": "Corporate Customer Advises Not Authorized"
    }
    
    @staticmethod
    async def process_return(
        db: Session,
        original_transaction_id: int,
        return_code: str,
        return_date: Optional[datetime] = None
    ) -> Dict:
        """Process ACH return"""
        try:
            if return_date is None:
                return_date = datetime.utcnow()
            
            transaction = db.query(Transaction).filter(
                Transaction.id == original_transaction_id
            ).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            # Determine if correctable
            correctable_codes = ["R01", "R09", "R11", "R13", "R16"]
            is_correctable = return_code in correctable_codes
            
            # Create return record
            ach_return = ACHReturn(
                original_transaction_id=original_transaction_id,
                return_code=return_code,
                return_reason=ACHReturnService.RETURN_CODES.get(return_code, "Unknown"),
                return_date=return_date,
                is_correctable=is_correctable
            )
            
            # Update transaction status
            transaction.status = "returned"
            
            # Reverse transaction if needed (for debits)
            if transaction.direction == "debit":
                # Add funds back to account
                account = db.query(Account).filter(
                    Account.id == transaction.account_id
                ).first()
                
                if account:
                    account.balance += transaction.amount
            
            db.add(ach_return)
            db.commit()
            
            return {
                "success": True,
                "return_id": ach_return.id,
                "return_code": return_code,
                "reason": ach_return.return_reason,
                "is_correctable": is_correctable,
                "return_date": return_date.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def submit_correction(
        db: Session,
        return_id: int,
        corrected_transaction_id: Optional[int] = None
    ) -> Dict:
        """Submit correcting ACH entry"""
        try:
            ach_return = db.query(ACHReturn).filter(
                ACHReturn.id == return_id
            ).first()
            
            if not ach_return or not ach_return.is_correctable:
                return {"success": False, "error": "Return not correctable"}
            
            ach_return.correction_submitted = True
            ach_return.correction_date = datetime.utcnow()
            
            db.commit()
            
            return {
                "success": True,
                "return_id": return_id,
                "correction_submitted_date": ach_return.correction_date.isoformat(),
                "status": "correction_pending"
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_return_status(db: Session, return_id: int) -> Dict:
        """Get return status"""
        try:
            ach_return = db.query(ACHReturn).filter(
                ACHReturn.id == return_id
            ).first()
            
            if not ach_return:
                return {"success": False, "error": "Return not found"}
            
            return {
                "success": True,
                "return_id": return_id,
                "return_code": ach_return.return_code,
                "reason": ach_return.return_reason,
                "return_date": ach_return.return_date.isoformat(),
                "is_correctable": ach_return.is_correctable,
                "correction_submitted": ach_return.correction_submitted,
                "correction_date": ach_return.correction_date.isoformat() if ach_return.correction_date else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class NSFService:
    """Non-Sufficient Funds management"""
    
    # NSF fee configuration
    NSF_FEE = 35.0
    NSF_RETRY_DAYS = 2
    
    @staticmethod
    async def check_available_balance(
        db: Session,
        account_id: int,
        transaction_amount: float
    ) -> Dict:
        """Pre-transaction NSF check"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            if account.balance < transaction_amount:
                shortage = transaction_amount - account.balance
                return {
                    "success": False,
                    "nsf_risk": True,
                    "current_balance": account.balance,
                    "transaction_amount": transaction_amount,
                    "shortage_amount": shortage
                }
            
            return {
                "success": True,
                "nsf_risk": False,
                "current_balance": account.balance,
                "available_balance": account.balance - transaction_amount
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def apply_nsf_fee(
        db: Session,
        transaction_id: int,
        account_id: int
    ) -> Dict:
        """Apply NSF fee to account"""
        try:
            transaction = db.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()
            
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not transaction or not account:
                return {"success": False, "error": "Transaction or account not found"}
            
            # Calculate shortage
            shortage = transaction.amount - account.balance if transaction.amount > account.balance else 0
            
            # Create NSF record
            nsf = NSFManagement(
                transaction_id=transaction_id,
                account_id=account_id,
                transaction_amount=transaction.amount,
                account_balance=account.balance,
                shortage_amount=shortage,
                nsf_fee=NSFService.NSF_FEE
            )
            
            # Apply NSF fee
            account.balance -= NSFService.NSF_FEE
            
            # Mark transaction as NSF
            transaction.status = "nsf"
            
            db.add(nsf)
            db.commit()
            
            return {
                "success": True,
                "nsf_id": nsf.id,
                "nsf_fee": NSFService.NSF_FEE,
                "new_balance": account.balance,
                "shortage_amount": shortage
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def attempt_recovery(
        db: Session,
        nsf_id: int
    ) -> Dict:
        """Attempt to re-debit after funds available"""
        try:
            nsf = db.query(NSFManagement).filter(NSFManagement.id == nsf_id).first()
            
            if not nsf or nsf.is_recovered:
                return {"success": False, "error": "NSF not found or already recovered"}
            
            account = db.query(Account).filter(Account.id == nsf.account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Check if sufficient funds now
            if account.balance < nsf.shortage_amount:
                return {
                    "success": False,
                    "recovery_status": "insufficient_funds",
                    "current_balance": account.balance,
                    "needed_amount": nsf.shortage_amount
                }
            
            # Debit original amount
            account.balance -= nsf.shortage_amount
            
            nsf.is_recovered = True
            nsf.recovered_date = datetime.utcnow()
            
            # Create recovery transaction
            recovery_txn = Transaction(
                user_id=account.owner_id,
                account_id=account.id,
                amount=nsf.shortage_amount,
                transaction_type="nsf_recovery",
                direction="debit",
                status="completed",
                description="NSF recovery debit"
            )
            
            db.add(recovery_txn)
            db.commit()
            
            return {
                "success": True,
                "nsf_id": nsf_id,
                "recovery_status": "recovered",
                "amount_recovered": nsf.shortage_amount,
                "new_balance": account.balance
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def reverse_nsf_fee(
        db: Session,
        nsf_id: int,
        reason: str
    ) -> Dict:
        """Reverse NSF fee"""
        try:
            nsf = db.query(NSFManagement).filter(NSFManagement.id == nsf_id).first()
            
            if not nsf:
                return {"success": False, "error": "NSF not found"}
            
            account = db.query(Account).filter(Account.id == nsf.account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Refund NSF fee
            account.balance += nsf.nsf_fee
            nsf.reversal_reason = reason
            
            db.commit()
            
            return {
                "success": True,
                "nsf_id": nsf_id,
                "fee_reversed": nsf.nsf_fee,
                "new_balance": account.balance
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class DisputeService:
    """Chargeback and dispute management"""
    
    @staticmethod
    async def file_dispute(
        db: Session,
        transaction_id: int,
        account_id: int,
        dispute_amount: float,
        dispute_reason: str
    ) -> Dict:
        """File a dispute/chargeback"""
        try:
            transaction = db.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            dispute = TransactionDispute(
                transaction_id=transaction_id,
                account_id=account_id,
                dispute_amount=dispute_amount,
                dispute_reason=dispute_reason,
                dispute_status="filed"
            )
            
            db.add(dispute)
            db.commit()
            
            return {
                "success": True,
                "dispute_id": dispute.id,
                "dispute_status": "filed",
                "dispute_date": dispute.dispute_date.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def submit_evidence(
        db: Session,
        dispute_id: int,
        evidence_description: str
    ) -> Dict:
        """Submit evidence for dispute"""
        try:
            dispute = db.query(TransactionDispute).filter(
                TransactionDispute.id == dispute_id
            ).first()
            
            if not dispute:
                return {"success": False, "error": "Dispute not found"}
            
            dispute.evidence_provided = True
            dispute.dispute_status = "under_investigation"
            
            db.commit()
            
            return {
                "success": True,
                "dispute_id": dispute_id,
                "status": "under_investigation",
                "evidence_submitted": True
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def resolve_dispute(
        db: Session,
        dispute_id: int,
        winning_party: str,
        resolution_notes: str
    ) -> Dict:
        """Resolve dispute"""
        try:
            dispute = db.query(TransactionDispute).filter(
                TransactionDispute.id == dispute_id
            ).first()
            
            if not dispute:
                return {"success": False, "error": "Dispute not found"}
            
            dispute.dispute_status = "resolved"
            dispute.winning_party = winning_party
            dispute.resolution_date = datetime.utcnow()
            dispute.resolution_notes = resolution_notes
            
            # If customer won, credit account
            if winning_party == "customer":
                account = db.query(Account).filter(
                    Account.id == dispute.account_id
                ).first()
                
                if account:
                    account.balance += dispute.dispute_amount
                    
                    # Create credit transaction
                    credit_txn = Transaction(
                        user_id=account.owner_id,
                        account_id=account.id,
                        amount=dispute.dispute_amount,
                        transaction_type="dispute_credit",
                        direction="credit",
                        status="completed",
                        description="Chargeback credit - dispute won"
                    )
                    
                    db.add(credit_txn)
            
            db.commit()
            
            return {
                "success": True,
                "dispute_id": dispute_id,
                "status": "resolved",
                "winning_party": winning_party,
                "resolution_date": dispute.resolution_date.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class ExceptionHandlingService:
    """Payment exception detection and handling"""
    
    @staticmethod
    async def detect_exception(
        db: Session,
        transaction_id: int
    ) -> Dict:
        """Detect payment exceptions"""
        try:
            transaction = db.query(Transaction).filter(
                Transaction.id == transaction_id
            ).first()
            
            if not transaction:
                return {"success": False, "error": "Transaction not found"}
            
            exceptions_detected = []
            
            # Check for NSF
            account = db.query(Account).filter(Account.id == transaction.account_id).first()
            
            if account and transaction.amount > account.balance:
                exceptions_detected.append("nsf")
            
            # Check for duplicates
            duplicate = db.query(Transaction).filter(
                and_(
                    Transaction.account_id == transaction.account_id,
                    Transaction.amount == transaction.amount,
                    Transaction.created_at >= datetime.utcnow() - timedelta(minutes=5),
                    Transaction.id != transaction_id
                )
            ).first()
            
            if duplicate:
                exceptions_detected.append("duplicate")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "exceptions_detected": exceptions_detected,
                "exception_count": len(exceptions_detected)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def escalate_exception(
        db: Session,
        transaction_id: int,
        exception_type: str,
        severity: str
    ) -> Dict:
        """Create and escalate exception"""
        try:
            exception = PaymentException(
                transaction_id=transaction_id,
                exception_type=exception_type,
                severity=severity,
                status="open",
                description=f"{exception_type} detected on transaction"
            )
            
            db.add(exception)
            db.commit()
            
            return {
                "success": True,
                "exception_id": exception.id,
                "status": "escalated",
                "severity": severity
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def resolve_exception(
        db: Session,
        exception_id: int,
        resolution_notes: str
    ) -> Dict:
        """Resolve exception"""
        try:
            exception = db.query(PaymentException).filter(
                PaymentException.id == exception_id
            ).first()
            
            if not exception:
                return {"success": False, "error": "Exception not found"}
            
            exception.status = "resolved"
            exception.resolved_at = datetime.utcnow()
            exception.resolution_notes = resolution_notes
            
            db.commit()
            
            return {
                "success": True,
                "exception_id": exception_id,
                "status": "resolved",
                "resolved_at": exception.resolved_at.isoformat()
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
