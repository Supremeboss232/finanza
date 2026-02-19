"""
Audit Logging Service - Immutable audit trail for regulatory compliance
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import User, Account, Transaction, Loan
import json
import logging

log = logging.getLogger(__name__)


class AuditService:
    """Immutable audit logging service"""
    
    @staticmethod
    async def log_action(
        db: Session,
        action: str,
        entity_type: str,
        entity_id: int,
        user_id: Optional[int] = None,
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        status_code: Optional[int] = None
    ) -> bool:
        """
        Log audit event (immutable append-only)
        
        Actions: create, read, update, delete, approve, reject, settle, block
        Entity types: user, account, transaction, loan, deposit, card, kyc
        """
        try:
            # Note: In a real system, you'd use a dedicated AuditLog model
            # For now we're logging, but we need to add proper immutable storage
            
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
                "old_value": old_value,
                "new_value": new_value,
                "reason": reason,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "api_endpoint": api_endpoint,
                "status_code": status_code
            }
            
            # Log to application logs
            log.info(f"AUDIT: {json.dumps(audit_entry)}")
            
            # In production: Write to immutable audit table
            # Could also write to: S3, WORM (Write-Once-Read-Many) storage, blockchain, etc.
            
            return True
        except Exception as e:
            log.error(f"Error logging audit: {str(e)}")
            return False
    
    @staticmethod
    async def log_user_action(
        db: Session,
        action: str,
        target_user_id: int,
        current_user_id: Optional[int] = None,
        change_details: Optional[Dict] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Log user-related actions"""
        return await AuditService.log_action(
            db,
            action=action,
            entity_type="user",
            entity_id=target_user_id,
            user_id=current_user_id,
            new_value=change_details,
            reason=reason
        )
    
    @staticmethod
    async def log_account_action(
        db: Session,
        action: str,
        account_id: int,
        old_balance: Optional[float] = None,
        new_balance: Optional[float] = None,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Log account-related actions"""
        return await AuditService.log_action(
            db,
            action=action,
            entity_type="account",
            entity_id=account_id,
            user_id=user_id,
            old_value={"balance": old_balance},
            new_value={"balance": new_balance},
            reason=reason
        )
    
    @staticmethod
    async def log_transaction_action(
        db: Session,
        action: str,
        transaction_id: int,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        amount: Optional[float] = None,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Log transaction-related actions"""
        return await AuditService.log_action(
            db,
            action=action,
            entity_type="transaction",
            entity_id=transaction_id,
            user_id=user_id,
            old_value={"status": old_status},
            new_value={"status": new_status, "amount": amount},
            reason=reason
        )
    
    @staticmethod
    async def log_loan_action(
        db: Session,
        action: str,
        loan_id: int,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        amount: Optional[float] = None,
        user_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Log loan-related actions"""
        return await AuditService.log_action(
            db,
            action=action,
            entity_type="loan",
            entity_id=loan_id,
            user_id=user_id,
            old_value={"status": old_status},
            new_value={"status": new_status, "amount": amount},
            reason=reason
        )
    
    @staticmethod
    async def log_kyc_action(
        db: Session,
        action: str,
        user_id: int,
        old_status: Optional[str] = None,
        new_status: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Log KYC-related actions"""
        return await AuditService.log_action(
            db,
            action=action,
            entity_type="kyc",
            entity_id=user_id,
            user_id=user_id,
            old_value={"status": old_status},
            new_value={"status": new_status},
            reason=reason
        )
    
    @staticmethod
    async def log_authentication(
        db: Session,
        user_id: int,
        action: str,  # login, logout, failed_login, password_reset, 2fa_enable
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True
    ) -> bool:
        """Log authentication events"""
        return await AuditService.log_action(
            db,
            action=f"auth_{action}",
            entity_type="user",
            entity_id=user_id,
            user_id=user_id,
            new_value={"success": success},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    async def log_settlement(
        db: Session,
        transaction_id: int,
        old_status: str,
        new_status: str,
        settlement_rail: str,
        settlement_time: Optional[datetime] = None
    ) -> bool:
        """Log settlement-related actions"""
        return await AuditService.log_action(
            db,
            action="settle",
            entity_type="transaction",
            entity_id=transaction_id,
            old_value={"status": old_status},
            new_value={"status": new_status, "rail": settlement_rail, "time": settlement_time.isoformat() if settlement_time else None},
            reason=f"Settlement via {settlement_rail}"
        )
    
    @staticmethod
    async def log_compliance_action(
        db: Session,
        action: str,
        user_id: int,
        compliance_type: str,  # sanctions, kyc, aml, fraud, sar
        details: Optional[Dict] = None,
        outcome: Optional[str] = None
    ) -> bool:
        """Log compliance-related actions"""
        return await AuditService.log_action(
            db,
            action=f"compliance_{action}",
            entity_type=compliance_type,
            entity_id=user_id,
            user_id=user_id,
            new_value={"outcome": outcome, **details} if details else {"outcome": outcome}
        )
    
    @staticmethod
    async def get_audit_trail(
        db: Session,
        entity_type: str,
        entity_id: int,
        limit: int = 100
    ) -> Dict:
        """
        Retrieve audit trail for entity
        
        In production, this would query the immutable audit table
        """
        try:
            # This is a placeholder - would query AuditLog table in production
            log.info(f"Retrieved audit trail for {entity_type} {entity_id}")
            return {
                "success": True,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entries": []  # Would contain audit entries
            }
        except Exception as e:
            log.error(f"Error retrieving audit trail: {str(e)}")
            return {"success": False, "error": str(e)}


class ReconciliationService:
    """Daily/periodic reconciliation of settlement and accounting"""
    
    @staticmethod
    async def daily_reconciliation(db: Session) -> Dict:
        """Perform daily reconciliation of settled transactions"""
        try:
            from sqlalchemy import func
            from models import Settlement
            from datetime import date
            
            today = date.today()
            
            # Get all settled transactions today
            settled_txns = db.query(Settlement).filter(
                Settlement.status == "settled",
                Settlement.settlement_date == today
            ).all()
            
            if not settled_txns:
                return {
                    "success": True,
                    "reconciliation_date": today.isoformat(),
                    "message": "No transactions to reconcile"
                }
            
            # Calculate totals
            total_settled = sum(
                db.query(Transaction).filter(Transaction.id == s.transaction_id).first().amount
                for s in settled_txns if db.query(Transaction).filter(Transaction.id == s.transaction_id).first()
            )
            
            # Verify account balances
            discrepancies = []
            accounts = db.query(Account).all()
            for account in accounts:
                # Calculate balance from transactions
                from sqlalchemy import func
                calculated_balance = db.query(func.sum(Transaction.amount)).filter(
                    Transaction.receiver_account_id == account.id,
                    Transaction.status == "completed"
                ).scalar() or 0
                
                calculated_balance -= db.query(func.sum(Transaction.amount)).filter(
                    Transaction.sender_account_id == account.id,
                    Transaction.status == "completed"
                ).scalar() or 0
                
                if abs(calculated_balance - account.balance) > 0.01:
                    discrepancies.append({
                        "account_id": account.id,
                        "stored_balance": account.balance,
                        "calculated_balance": calculated_balance,
                        "difference": calculated_balance - account.balance
                    })
            
            await AuditService.log_action(
                db,
                action="reconcile",
                entity_type="settlement",
                entity_id=0,
                new_value={
                    "date": today.isoformat(),
                    "total_settled": total_settled,
                    "transaction_count": len(settled_txns),
                    "discrepancies": len(discrepancies)
                }
            )
            
            log.info(f"Daily reconciliation: {len(settled_txns)} transactions, {len(discrepancies)} discrepancies")
            
            return {
                "success": True,
                "reconciliation_date": today.isoformat(),
                "transactions_reconciled": len(settled_txns),
                "total_amount": total_settled,
                "discrepancies": discrepancies,
                "status": "success" if not discrepancies else "warning"
            }
        except Exception as e:
            log.error(f"Error in daily reconciliation: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def verify_balances(db: Session, account_id: int) -> Dict:
        """Verify account balance integrity"""
        try:
            from sqlalchemy import func
            
            account = db.query(Account).filter(Account.id == account_id).first()
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Calculate balance from transaction ledger
            calculated = db.query(func.sum(Transaction.amount)).filter(
                Transaction.receiver_account_id == account_id,
                Transaction.status == "completed"
            ).scalar() or 0
            
            calculated -= db.query(func.sum(Transaction.amount)).filter(
                Transaction.sender_account_id == account_id,
                Transaction.status == "completed"
            ).scalar() or 0
            
            difference = calculated - account.balance
            
            return {
                "success": True,
                "account_id": account_id,
                "stored_balance": account.balance,
                "calculated_balance": calculated,
                "difference": difference,
                "in_balance": abs(difference) < 0.01
            }
        except Exception as e:
            log.error(f"Error verifying balance: {str(e)}")
            return {"success": False, "error": str(e)}
