# account_management_service.py
# Account lifecycle management, statements, holds, sweeps, interest accrual

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from models import (
    Account, AccountType, AccountHold, TransactionHistory, Statement,
    InterestAccrual, SweepRule, AccountClosure, Transaction, User
)


class AccountManagementService:
    """Core account management operations"""
    
    @staticmethod
    async def open_account(
        db: Session,
        owner_id: int,
        account_type_name: str,
        initial_deposit: float = 0.0
    ) -> Dict:
        """Open a new account"""
        try:
            # Get account type
            account_type = db.query(AccountType).filter(
                AccountType.name == account_type_name
            ).first()
            
            if not account_type:
                return {"success": False, "error": "Account type not found"}
            
            # Create account
            account = Account(
                account_number=f"ACC{datetime.now().timestamp()}",
                account_type=account_type_name,
                balance=initial_deposit,
                owner_id=owner_id,
                status="active",
                kyc_level="full"
            )
            
            db.add(account)
            db.commit()
            
            # Record opening transaction
            if initial_deposit > 0:
                txn = Transaction(
                    user_id=owner_id,
                    account_id=account.id,
                    amount=initial_deposit,
                    transaction_type="deposit",
                    direction="credit",
                    status="completed",
                    description="Initial deposit"
                )
                db.add(txn)
                db.commit()
            
            return {
                "success": True,
                "account_id": account.id,
                "account_number": account.account_number,
                "balance": account.balance
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def close_account(
        db: Session,
        account_id: int,
        closure_reason: str,
        initiated_by: int
    ) -> Dict:
        """Close an account"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Generate final statement
            await StatementGenerationService.generate_statement(db, account_id)
            
            # Record closure
            closure = AccountClosure(
                account_id=account_id,
                closure_reason=closure_reason,
                final_balance=account.balance,
                initiated_by=initiated_by
            )
            
            account.status = "closed"
            db.add(closure)
            db.commit()
            
            return {
                "success": True,
                "account_id": account_id,
                "final_balance": account.balance
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def place_hold(
        db: Session,
        account_id: int,
        hold_type: str,
        amount: Optional[float],
        reason: str,
        applied_by: int,
        expires_in_days: Optional[int] = None
    ) -> Dict:
        """Place a hold on account"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            hold = AccountHold(
                account_id=account_id,
                hold_type=hold_type,
                amount=amount,
                reason=reason,
                applied_by=applied_by,
                expires_at=expires_at
            )
            
            db.add(hold)
            db.commit()
            
            return {
                "success": True,
                "hold_id": hold.id,
                "hold_type": hold_type,
                "amount": amount,
                "expires_at": expires_at.isoformat() if expires_at else None
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def release_hold(
        db: Session,
        hold_id: int,
        release_reason: str
    ) -> Dict:
        """Release an account hold"""
        try:
            hold = db.query(AccountHold).filter(AccountHold.id == hold_id).first()
            
            if not hold:
                return {"success": False, "error": "Hold not found"}
            
            hold.released_at = datetime.utcnow()
            hold.release_reason = release_reason
            
            db.commit()
            
            return {"success": True, "hold_id": hold_id}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_account_balance(db: Session, account_id: int) -> Dict:
        """Get real-time account balance"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            return {
                "success": True,
                "account_id": account_id,
                "balance": account.balance,
                "last_updated": account.updated_at.isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_available_balance(db: Session, account_id: int) -> Dict:
        """Get available balance (excluding holds)"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Calculate holds
            total_holds = db.query(AccountHold).filter(
                and_(
                    AccountHold.account_id == account_id,
                    AccountHold.released_at == None
                )
            ).all()
            
            held_amount = sum(h.amount for h in total_holds if h.amount)
            available_balance = account.balance - held_amount
            
            return {
                "success": True,
                "account_id": account_id,
                "balance": account.balance,
                "held_amount": held_amount,
                "available_balance": available_balance
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class StatementGenerationService:
    """Statement generation and management"""
    
    @staticmethod
    async def generate_statement(
        db: Session,
        account_id: int,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Dict:
        """Generate account statement"""
        try:
            if period_end is None:
                period_end = datetime.utcnow()
            
            if period_start is None:
                # Default to last 30 days
                period_start = period_end - timedelta(days=30)
            
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Get transactions for period
            transactions = db.query(Transaction).filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.created_at >= period_start,
                    Transaction.created_at <= period_end,
                    Transaction.status == "completed"
                )
            ).all()
            
            # Calculate totals
            total_debits = sum(t.amount for t in transactions if t.direction == "debit")
            total_credits = sum(t.amount for t in transactions if t.direction == "credit")
            
            # Get interest accruals for period
            interest_transactions = db.query(InterestAccrual).filter(
                and_(
                    InterestAccrual.account_id == account_id,
                    InterestAccrual.accrual_date >= period_start,
                    InterestAccrual.accrual_date <= period_end
                )
            ).all()
            
            total_interest = sum(i.accrued_amount for i in interest_transactions)
            
            # Get opening balance
            opening_transactions = db.query(Transaction).filter(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.created_at < period_start,
                    Transaction.status == "completed"
                )
            ).order_by(desc(Transaction.created_at)).first()
            
            opening_balance = opening_transactions.amount if opening_transactions else 0.0
            closing_balance = account.balance
            
            # Create statement
            statement = Statement(
                account_id=account_id,
                statement_period_start=period_start,
                statement_period_end=period_end,
                opening_balance=opening_balance,
                closing_balance=closing_balance,
                total_debits=total_debits,
                total_credits=total_credits,
                interest_earned=total_interest,
                delivery_method="email"
            )
            
            db.add(statement)
            db.commit()
            
            return {
                "success": True,
                "statement_id": statement.id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "opening_balance": opening_balance,
                "closing_balance": closing_balance,
                "total_debits": total_debits,
                "total_credits": total_credits,
                "interest_earned": total_interest
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_statement(db: Session, statement_id: int) -> Dict:
        """Retrieve statement details"""
        try:
            statement = db.query(Statement).filter(Statement.id == statement_id).first()
            
            if not statement:
                return {"success": False, "error": "Statement not found"}
            
            return {
                "success": True,
                "statement_id": statement_id,
                "account_id": statement.account_id,
                "period_start": statement.statement_period_start.isoformat(),
                "period_end": statement.statement_period_end.isoformat(),
                "opening_balance": statement.opening_balance,
                "closing_balance": statement.closing_balance,
                "total_debits": statement.total_debits,
                "total_credits": statement.total_credits,
                "interest_earned": statement.interest_earned,
                "generated_at": statement.generated_at.isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class InterestAccrualService:
    """Interest calculation and accrual"""
    
    @staticmethod
    async def accrue_daily_interest(db: Session, account_id: int) -> Dict:
        """Calculate and accrue daily interest"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            # Get account type for interest rate
            account_type = db.query(AccountType).filter(
                AccountType.name == account.account_type
            ).first()
            
            if not account_type or account_type.interest_rate == 0:
                return {
                    "success": True,
                    "message": "No interest for this account type",
                    "accrued_amount": 0.0
                }
            
            # Calculate daily interest
            daily_rate = account_type.interest_rate / 365
            accrued_amount = account.balance * daily_rate / 100
            
            # Record accrual
            accrual = InterestAccrual(
                account_id=account_id,
                annual_rate=account_type.interest_rate,
                daily_balance=account.balance,
                accrued_amount=accrued_amount,
                accrual_type="daily"
            )
            
            # Add interest to account balance
            account.accrued_interest = account.accrued_interest + accrued_amount if hasattr(account, 'accrued_interest') else accrued_amount
            
            db.add(accrual)
            db.commit()
            
            return {
                "success": True,
                "account_id": account_id,
                "daily_balance": account.balance,
                "accrued_amount": accrued_amount,
                "annual_rate": account_type.interest_rate
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def post_monthly_interest(db: Session, account_id: int) -> Dict:
        """Post accrued interest monthly"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account or not hasattr(account, 'accrued_interest'):
                return {"success": False, "error": "Account not found"}
            
            accrued = account.accrued_interest or 0.0
            
            if accrued <= 0:
                return {"success": True, "message": "No interest to post", "posted_amount": 0.0}
            
            # Post interest
            txn = Transaction(
                user_id=account.owner_id,
                account_id=account_id,
                amount=accrued,
                transaction_type="interest",
                direction="credit",
                status="completed",
                description="Monthly interest posting"
            )
            
            account.balance += accrued
            account.accrued_interest = 0.0
            
            db.add(txn)
            db.commit()
            
            return {
                "success": True,
                "account_id": account_id,
                "posted_amount": accrued,
                "new_balance": account.balance
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class SweepService:
    """Automatic sweep management"""
    
    @staticmethod
    async def setup_sweep(
        db: Session,
        account_id: int,
        target_account_id: int,
        frequency: str,
        minimum_threshold: float,
        maximum_amount: Optional[float] = None
    ) -> Dict:
        """Configure automatic sweep"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            target = db.query(Account).filter(Account.id == target_account_id).first()
            
            if not account or not target:
                return {"success": False, "error": "Account not found"}
            
            sweep = SweepRule(
                account_id=account_id,
                source_account_id=account_id,
                target_account_id=target_account_id,
                sweep_frequency=frequency,
                minimum_threshold=minimum_threshold,
                maximum_amount=maximum_amount
            )
            
            db.add(sweep)
            db.commit()
            
            return {
                "success": True,
                "sweep_id": sweep.id,
                "frequency": frequency,
                "minimum_threshold": minimum_threshold
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def execute_sweep(db: Session, sweep_id: int) -> Dict:
        """Execute a single sweep"""
        try:
            sweep = db.query(SweepRule).filter(SweepRule.id == sweep_id).first()
            
            if not sweep or not sweep.is_active:
                return {"success": False, "error": "Sweep not found or inactive"}
            
            source = db.query(Account).filter(Account.id == sweep.source_account_id).first()
            target = db.query(Account).filter(Account.id == sweep.target_account_id).first()
            
            if not source or not target:
                return {"success": False, "error": "Account not found"}
            
            # Check threshold
            if source.balance < sweep.minimum_threshold:
                return {
                    "success": False,
                    "message": "Below minimum threshold",
                    "current_balance": source.balance
                }
            
            # Calculate sweep amount
            sweep_amount = source.balance - sweep.minimum_threshold
            
            if sweep.maximum_amount and sweep_amount > sweep.maximum_amount:
                sweep_amount = sweep.maximum_amount
            
            # Execute sweep
            source.balance -= sweep_amount
            target.balance += sweep_amount
            
            # Record transactions
            txn1 = Transaction(
                user_id=source.owner_id,
                account_id=sweep.source_account_id,
                amount=sweep_amount,
                transaction_type="sweep",
                direction="debit",
                status="completed",
                description="Automatic sweep"
            )
            
            txn2 = Transaction(
                user_id=target.owner_id,
                account_id=sweep.target_account_id,
                amount=sweep_amount,
                transaction_type="sweep",
                direction="credit",
                status="completed",
                description="Automatic sweep"
            )
            
            db.add_all([txn1, txn2])
            db.commit()
            
            return {
                "success": True,
                "sweep_amount": sweep_amount,
                "source_new_balance": source.balance,
                "target_new_balance": target.balance
            }
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}


class TransactionHistoryService:
    """Transaction history tracking and export"""
    
    @staticmethod
    async def record_transaction_history(
        db: Session,
        transaction_id: int,
        account_id: int,
        transaction_type: str,
        amount: float,
        description: str,
        merchant_category: Optional[str] = None
    ) -> Dict:
        """Record transaction in history"""
        try:
            account = db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return {"success": False, "error": "Account not found"}
            
            history = TransactionHistory(
                transaction_id=transaction_id,
                account_id=account_id,
                transaction_type=transaction_type,
                amount=amount,
                balance_after=account.balance,
                description=description,
                merchant_category=merchant_category
            )
            
            db.add(history)
            db.commit()
            
            return {"success": True, "history_id": history.id}
        except Exception as e:
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_transaction_history(
        db: Session,
        account_id: int,
        days: int = 90,
        limit: int = 100
    ) -> Dict:
        """Get transaction history"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            history = db.query(TransactionHistory).filter(
                and_(
                    TransactionHistory.account_id == account_id,
                    TransactionHistory.posting_date >= start_date
                )
            ).order_by(desc(TransactionHistory.posting_date)).limit(limit).all()
            
            return {
                "success": True,
                "account_id": account_id,
                "period_days": days,
                "transaction_count": len(history),
                "transactions": [
                    {
                        "date": h.posting_date.isoformat(),
                        "type": h.transaction_type,
                        "amount": h.amount,
                        "balance": h.balance_after,
                        "description": h.description,
                        "merchant_category": h.merchant_category
                    }
                    for h in history
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def export_transactions(
        db: Session,
        account_id: int,
        format_type: str = "csv",
        days: int = 90
    ) -> Dict:
        """Export transaction history"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            history = db.query(TransactionHistory).filter(
                and_(
                    TransactionHistory.account_id == account_id,
                    TransactionHistory.posting_date >= start_date
                )
            ).order_by(desc(TransactionHistory.posting_date)).all()
            
            if format_type == "csv":
                # Generate CSV
                csv_lines = ["Date,Type,Amount,Balance,Description,Merchant"]
                for h in history:
                    csv_lines.append(
                        f"{h.posting_date.isoformat()},{h.transaction_type},"
                        f"{h.amount},{h.balance_after},\"{h.description}\","
                        f"{h.merchant_category or ''}"
                    )
                
                return {
                    "success": True,
                    "format": "csv",
                    "data": "\n".join(csv_lines)
                }
            elif format_type == "json":
                return {
                    "success": True,
                    "format": "json",
                    "data": [
                        {
                            "date": h.posting_date.isoformat(),
                            "type": h.transaction_type,
                            "amount": h.amount,
                            "balance": h.balance_after,
                            "description": h.description
                        }
                        for h in history
                    ]
                }
            else:
                return {"success": False, "error": "Unsupported format"}
        except Exception as e:
            return {"success": False, "error": str(e)}
