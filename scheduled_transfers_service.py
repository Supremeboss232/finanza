# scheduled_transfers_service.py
# Scheduled transfers and recurring transfer management service

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import logging

log = logging.getLogger(__name__)


class ScheduledTransferService:
    """Service for managing one-time and recurring scheduled transfers"""
    
    @staticmethod
    async def create_transfer(
        db: Session,
        from_account_id: int,
        to_account_id: int,
        amount: float,
        scheduled_date: datetime,
        transfer_type: str,  # one_time, recurring
        description: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Create a scheduled transfer
        
        Args:
            from_account_id: Source account ID
            to_account_id: Destination account ID
            amount: Transfer amount
            scheduled_date: When to execute
            transfer_type: one_time or recurring
            description: Transfer description
            created_by: User ID who created
        
        Returns:
            {"success": bool, "transfer_id": int, "scheduled_date": str}
        """
        try:
            from models import Account, ScheduledTransfer
            
            # Verify accounts exist
            from_account = db.query(Account).filter(Account.id == from_account_id).first()
            to_account = db.query(Account).filter(Account.id == to_account_id).first()
            
            if not from_account or not to_account:
                return {"success": False, "error": "Account not found"}
            
            # Verify sufficient available balance
            if from_account.available_balance < amount:
                return {"success": False, "error": "Insufficient available balance"}
            
            # Create scheduled transfer
            transfer = ScheduledTransfer(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                scheduled_date=scheduled_date,
                transfer_type=transfer_type,
                status="scheduled",
                description=description,
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(transfer)
            db.commit()
            db.refresh(transfer)
            
            log.info(f"Scheduled transfer created: {transfer.id} from {from_account_id} to {to_account_id}")
            
            return {
                "success": True,
                "transfer_id": transfer.id,
                "from_account": from_account_id,
                "to_account": to_account_id,
                "amount": amount,
                "scheduled_date": scheduled_date.isoformat(),
                "status": "scheduled"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error creating scheduled transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def get_scheduled_transfers(
        db: Session,
        account_id: int,
        status: Optional[str] = None
    ) -> dict:
        """
        Get scheduled transfers for account
        
        Args:
            account_id: Account to query
            status: Filter by status (scheduled, executed, cancelled, failed)
        
        Returns:
            {"success": bool, "transfers": [...]}
        """
        try:
            from models import ScheduledTransfer
            
            query = db.query(ScheduledTransfer).filter(
                (ScheduledTransfer.from_account_id == account_id) |
                (ScheduledTransfer.to_account_id == account_id)
            )
            
            if status:
                query = query.filter(ScheduledTransfer.status == status)
            
            transfers = query.order_by(ScheduledTransfer.scheduled_date).all()
            
            return {
                "success": True,
                "transfer_count": len(transfers),
                "transfers": [
                    {
                        "transfer_id": t.id,
                        "from_account": t.from_account_id,
                        "to_account": t.to_account_id,
                        "amount": t.amount,
                        "scheduled_date": t.scheduled_date.isoformat(),
                        "status": t.status,
                        "description": t.description,
                        "created_at": t.created_at.isoformat()
                    }
                    for t in transfers
                ]
            }
        except Exception as e:
            log.error(f"Error fetching scheduled transfers: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def cancel_transfer(
        db: Session,
        transfer_id: int,
        cancelled_by: Optional[int] = None
    ) -> dict:
        """
        Cancel a scheduled transfer
        
        Returns:
            {"success": bool, "transfer_id": int}
        """
        try:
            from models import ScheduledTransfer
            
            transfer = db.query(ScheduledTransfer).filter(
                ScheduledTransfer.id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            if transfer.status == "executed":
                return {"success": False, "error": "Cannot cancel executed transfer"}
            
            transfer.status = "cancelled"
            transfer.cancelled_at = datetime.utcnow()
            transfer.cancelled_by = cancelled_by
            
            db.commit()
            
            log.info(f"Scheduled transfer cancelled: {transfer_id}")
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "status": "cancelled"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error cancelling transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def execute_transfer(
        db: Session,
        transfer_id: int
    ) -> dict:
        """
        Execute a scheduled transfer (called by scheduled job)
        
        Returns:
            {"success": bool, "transaction_id": int}
        """
        try:
            from models import ScheduledTransfer, Account, Transaction
            
            transfer = db.query(ScheduledTransfer).filter(
                ScheduledTransfer.id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            if transfer.status != "scheduled":
                return {"success": False, "error": f"Transfer is {transfer.status}"}
            
            # Get accounts
            from_account = db.query(Account).filter(
                Account.id == transfer.from_account_id
            ).first()
            to_account = db.query(Account).filter(
                Account.id == transfer.to_account_id
            ).first()
            
            # Verify balance
            if from_account.available_balance < transfer.amount:
                transfer.status = "failed"
                transfer.failed_reason = "Insufficient available balance"
                db.commit()
                return {"success": False, "error": "Insufficient funds at execution time"}
            
            # Execute transfer
            from_account.available_balance -= transfer.amount
            from_account.balance -= transfer.amount
            to_account.available_balance += transfer.amount
            to_account.balance += transfer.amount
            
            # Record transactions
            from_txn = Transaction(
                account_id=from_account.id,
                amount=transfer.amount,
                transaction_type="transfer_out",
                status="completed",
                description=f"Scheduled transfer to {to_account.id}",
                created_at=datetime.utcnow()
            )
            
            to_txn = Transaction(
                account_id=to_account.id,
                amount=transfer.amount,
                transaction_type="transfer_in",
                status="completed",
                description=f"Scheduled transfer from {from_account.id}",
                created_at=datetime.utcnow()
            )
            
            db.add(from_txn)
            db.add(to_txn)
            
            # Update transfer
            transfer.status = "executed"
            transfer.executed_at = datetime.utcnow()
            transfer.transaction_id_from = from_txn.id
            transfer.transaction_id_to = to_txn.id
            
            db.commit()
            
            log.info(f"Scheduled transfer executed: {transfer_id}")
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "status": "executed",
                "from_transaction": from_txn.id,
                "to_transaction": to_txn.id,
                "executed_at": transfer.executed_at.isoformat()
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error executing transfer: {e}")
            return {"success": False, "error": str(e)}


class RecurringTransferService:
    """Service for managing recurring transfers"""
    
    @staticmethod
    async def setup_recurring(
        db: Session,
        from_account_id: int,
        to_account_id: int,
        amount: float,
        frequency: str,  # daily, weekly, biweekly, monthly
        start_date: datetime,
        end_date: Optional[datetime] = None,
        created_by: Optional[int] = None
    ) -> dict:
        """
        Setup recurring transfer
        
        Args:
            frequency: daily, weekly, biweekly, monthly
            end_date: When to stop (None = indefinite)
        
        Returns:
            {"success": bool, "recurring_id": int}
        """
        try:
            from models import RecurringTransfer, Account
            
            # Verify accounts
            from_account = db.query(Account).filter(Account.id == from_account_id).first()
            to_account = db.query(Account).filter(Account.id == to_account_id).first()
            
            if not from_account or not to_account:
                return {"success": False, "error": "Account not found"}
            
            # Create recurring transfer
            recurring = RecurringTransfer(
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                status="active",
                created_by=created_by,
                created_at=datetime.utcnow()
            )
            
            db.add(recurring)
            db.commit()
            db.refresh(recurring)
            
            log.info(f"Recurring transfer setup: {recurring.id} - {frequency}")
            
            return {
                "success": True,
                "recurring_id": recurring.id,
                "frequency": frequency,
                "status": "active"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error setting up recurring transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def modify_recurring(
        db: Session,
        recurring_id: int,
        amount: Optional[float] = None,
        frequency: Optional[str] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """
        Modify recurring transfer
        
        Returns:
            {"success": bool, "recurring_id": int}
        """
        try:
            from models import RecurringTransfer
            
            recurring = db.query(RecurringTransfer).filter(
                RecurringTransfer.id == recurring_id
            ).first()
            
            if not recurring:
                return {"success": False, "error": "Recurring transfer not found"}
            
            if recurring.status != "active":
                return {"success": False, "error": "Can only modify active transfers"}
            
            if amount:
                recurring.amount = amount
            if frequency:
                recurring.frequency = frequency
            if end_date:
                recurring.end_date = end_date
            
            recurring.modified_at = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Recurring transfer modified: {recurring_id}")
            
            return {
                "success": True,
                "recurring_id": recurring_id,
                "amount": recurring.amount,
                "frequency": recurring.frequency
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error modifying recurring transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def suspend_recurring(
        db: Session,
        recurring_id: int
    ) -> dict:
        """
        Suspend recurring transfer (pause)
        
        Returns:
            {"success": bool, "recurring_id": int}
        """
        try:
            from models import RecurringTransfer
            
            recurring = db.query(RecurringTransfer).filter(
                RecurringTransfer.id == recurring_id
            ).first()
            
            if not recurring:
                return {"success": False, "error": "Recurring transfer not found"}
            
            recurring.status = "suspended"
            recurring.suspended_at = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Recurring transfer suspended: {recurring_id}")
            
            return {
                "success": True,
                "recurring_id": recurring_id,
                "status": "suspended"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error suspending recurring transfer: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def resume_recurring(
        db: Session,
        recurring_id: int
    ) -> dict:
        """
        Resume suspended recurring transfer
        
        Returns:
            {"success": bool, "recurring_id": int}
        """
        try:
            from models import RecurringTransfer
            
            recurring = db.query(RecurringTransfer).filter(
                RecurringTransfer.id == recurring_id
            ).first()
            
            if not recurring:
                return {"success": False, "error": "Recurring transfer not found"}
            
            if recurring.status != "suspended":
                return {"success": False, "error": "Transfer is not suspended"}
            
            recurring.status = "active"
            recurring.resumed_at = datetime.utcnow()
            
            db.commit()
            
            log.info(f"Recurring transfer resumed: {recurring_id}")
            
            return {
                "success": True,
                "recurring_id": recurring_id,
                "status": "active"
            }
        except Exception as e:
            db.rollback()
            log.error(f"Error resuming recurring transfer: {e}")
            return {"success": False, "error": str(e)}


class TransferScheduleService:
    """Service for managing transfer schedules and batch execution"""
    
    @staticmethod
    async def calculate_next_execution(
        frequency: str,
        current_date: datetime = None
    ) -> datetime:
        """
        Calculate next execution date based on frequency
        
        Returns:
            Next execution datetime
        """
        if current_date is None:
            current_date = datetime.utcnow()
        
        if frequency == "daily":
            return current_date + timedelta(days=1)
        elif frequency == "weekly":
            return current_date + timedelta(weeks=1)
        elif frequency == "biweekly":
            return current_date + timedelta(weeks=2)
        elif frequency == "monthly":
            # Add one month
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        else:
            return current_date + timedelta(days=1)
    
    @staticmethod
    async def get_due_transfers(
        db: Session
    ) -> list:
        """
        Get all transfers due for execution
        
        Returns:
            List of due transfer IDs
        """
        try:
            from models import ScheduledTransfer
            
            now = datetime.utcnow()
            
            due_transfers = db.query(ScheduledTransfer).filter(
                ScheduledTransfer.status == "scheduled",
                ScheduledTransfer.scheduled_date <= now
            ).all()
            
            return [t.id for t in due_transfers]
        except Exception as e:
            log.error(f"Error getting due transfers: {e}")
            return []
    
    @staticmethod
    async def process_batch_transfers(
        db: Session
    ) -> dict:
        """
        Process all due transfers (batch job)
        
        Returns:
            {"success": bool, "processed": int, "succeeded": int, "failed": int}
        """
        try:
            from models import ScheduledTransfer
            
            due_ids = await TransferScheduleService.get_due_transfers(db)
            
            processed = 0
            succeeded = 0
            failed = 0
            
            for transfer_id in due_ids:
                result = await ScheduledTransferService.execute_transfer(db, transfer_id)
                processed += 1
                
                if result["success"]:
                    succeeded += 1
                else:
                    failed += 1
            
            log.info(f"Batch transfer processing: {processed} processed, {succeeded} succeeded, {failed} failed")
            
            return {
                "success": True,
                "processed": processed,
                "succeeded": succeeded,
                "failed": failed
            }
        except Exception as e:
            log.error(f"Error processing batch transfers: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def verify_available_funds(
        db: Session,
        transfer_id: int
    ) -> dict:
        """
        Verify account has available funds for transfer
        
        Returns:
            {"success": bool, "has_funds": bool, "available_balance": float}
        """
        try:
            from models import ScheduledTransfer, Account
            
            transfer = db.query(ScheduledTransfer).filter(
                ScheduledTransfer.id == transfer_id
            ).first()
            
            if not transfer:
                return {"success": False, "error": "Transfer not found"}
            
            account = db.query(Account).filter(
                Account.id == transfer.from_account_id
            ).first()
            
            has_funds = account.available_balance >= transfer.amount
            
            return {
                "success": True,
                "transfer_id": transfer_id,
                "has_funds": has_funds,
                "required_amount": transfer.amount,
                "available_balance": account.available_balance
            }
        except Exception as e:
            log.error(f"Error verifying funds: {e}")
            return {"success": False, "error": str(e)}
