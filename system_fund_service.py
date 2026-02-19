"""
System Fund Service

Handles all fund transfers from the System Reserve Account.
Creates ledger entries and maintains atomic balance updates.

Core Principle:
- Every fund transfer creates double-entry ledger entries
- FROM: SYS-RESERVE-0001 (System Account)
- TO: Target User Account
- ALL transactions are logged in audit table
"""

import json
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from models import Account, User, Ledger, Transaction, AuditLog
from typing import Dict, Any, Optional


class SystemFundService:
    """Service for managing admin fund operations from system reserve account."""
    
    SYSTEM_RESERVE_ACCOUNT = "SYS-RESERVE-0001"
    SYSTEM_USER_ID = 1
    
    @staticmethod
    async def get_system_reserve_account(db: AsyncSession) -> Account:
        """Get the system reserve account. Raises error if not found."""
        result = await db.execute(
            select(Account).filter(Account.account_number == SystemFundService.SYSTEM_RESERVE_ACCOUNT)
        )
        account = result.scalars().first()
        if not account:
            raise ValueError(f"System Reserve Account {SystemFundService.SYSTEM_RESERVE_ACCOUNT} not found")
        return account
    
    @staticmethod
    async def fund_user_from_system(
        db: AsyncSession,
        target_user_id: int,
        target_account_id: int,
        amount: float,
        admin_user_id: int,
        reason: Optional[str] = None,
        transaction_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fund a user account from the System Reserve Account.
        
        Creates:
        1. Debit entry: Money leaves system reserve
        2. Credit entry: Money enters target user account
        3. Transaction record: Links both entries
        4. AuditLog entry: Records admin action
        
        Returns: Dictionary with operation details
        """
        try:
            print(f"[SystemFundService] Starting fund transfer: user_id={target_user_id}, account_id={target_account_id}, amount={amount}")
            
            # Get system reserve account
            reserve_account = await SystemFundService.get_system_reserve_account(db)
            print(f"[SystemFundService] Got reserve account: {reserve_account.account_number}")
            
            # Get target account
            result = await db.execute(select(Account).filter(Account.id == target_account_id))
            target_account = result.scalars().first()
            if not target_account:
                raise ValueError(f"Target account {target_account_id} not found")
            print(f"[SystemFundService] Got target account: {target_account.account_number}")
            
            # Get target user
            result = await db.execute(select(User).filter(User.id == target_user_id))
            target_user = result.scalars().first()
            if not target_user:
                raise ValueError(f"Target user {target_user_id} not found")
            print(f"[SystemFundService] Got target user: {target_user.email}")
            
            # Get admin user
            result = await db.execute(select(User).filter(User.id == admin_user_id))
            admin_user = result.scalars().first()
            if not admin_user:
                raise ValueError(f"Admin user {admin_user_id} not found")
            print(f"[SystemFundService] Got admin user: {admin_user.email}")
            
            amount_decimal = Decimal(str(amount))
            print(f"[SystemFundService] Amount: {amount_decimal}")
            
            # Create or get transaction record if not provided
            if not transaction_id:
                print(f"[SystemFundService] Creating transaction record...")
                tx = Transaction(
                    user_id=target_user_id,
                    account_id=target_account_id,
                    transaction_type="fund_transfer",
                    amount=float(amount),
                    direction="credit",
                    status="completed",
                    description=f"Admin funding from System Reserve Account",
                    kyc_status_at_time=target_user.kyc_status
                )
                db.add(tx)
                await db.flush()
                transaction_id = tx.id
                print(f"[SystemFundService] Transaction created: ID={transaction_id}")
            
            # Step 1: Create DEBIT entry (money leaves system reserve)
            debit_entry = Ledger(
                user_id=SystemFundService.SYSTEM_USER_ID,  # System user
                entry_type="debit",  # Money leaving the account
                amount=amount_decimal,
                transaction_id=transaction_id,
                destination_user_id=target_user_id,  # Going to this user
                description=f"Fund transfer to {target_user.email}",
                status="posted"
            )
            db.add(debit_entry)
            await db.flush()
            
            # Step 2: Create CREDIT entry (money enters target account)
            credit_entry = Ledger(
                user_id=target_user_id,  # Target user
                entry_type="credit",  # Money entering the account
                amount=amount_decimal,
                transaction_id=transaction_id,
                source_user_id=SystemFundService.SYSTEM_USER_ID,  # From system
                related_entry_id=debit_entry.id,  # Link to matching entry
                description=f"Admin funding from System Reserve Account",
                status="posted"
            )
            db.add(credit_entry)
            await db.flush()
            
            # Link the debit entry to credit entry for double-entry verification
            debit_entry.related_entry_id = credit_entry.id
            db.add(debit_entry)
            await db.flush()
            
            # ISSUE #4 FIX: Do NOT manually update account.balance
            # Balance is now calculated from ledger (source of truth)
            # Step removed: target_account.balance = float(target_account.balance) + amount
            
            # Step 4: Create AuditLog entry
            audit_details = {
                "source_account": SystemFundService.SYSTEM_RESERVE_ACCOUNT,
                "target_account": target_account.account_number,
                "amount": float(amount),
                "debit_entry_id": debit_entry.id,
                "credit_entry_id": credit_entry.id,
                "transaction_id": transaction_id
            }
            audit_log = AuditLog(
                admin_id=admin_user_id,
                user_id=target_user_id,
                account_id=target_account_id,
                action_type="fund",
                reason=reason or "Admin funding from system reserve",
                details=json.dumps(audit_details)  # Convert dict to JSON string
            )
            db.add(audit_log)
            await db.flush()
            
            # Commit all changes atomically
            await db.commit()
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "debit_entry_id": debit_entry.id,
                "credit_entry_id": credit_entry.id,
                "audit_log_id": audit_log.id,
                "source_account": SystemFundService.SYSTEM_RESERVE_ACCOUNT,
                "target_account": target_account.account_number,
                "amount": float(amount),
                "new_balance": target_account.balance,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            await db.rollback()
            import traceback
            error_details = f"[{datetime.now().isoformat()}] SystemFundService.fund_user_from_system failed:\n"
            error_details += f"  Error: {str(e)}\n"
            error_details += f"  Type: {type(e).__name__}\n"
            error_details += traceback.format_exc() + "\n"
            
            # Write to file
            try:
                with open('/tmp/fund_debug.log', 'a') as f:
                    f.write(error_details)
                    f.flush()
            except Exception as write_error:
                pass
            
            print(f"❌ SystemFundService.fund_user_from_system failed:")
            print(f"   Error: {str(e)}")
            print(f"   Type: {type(e).__name__}")
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_reserve_balance(db: AsyncSession) -> float:
        """Get current balance of system reserve account."""
        reserve = await SystemFundService.get_system_reserve_account(db)
        return float(reserve.balance)
    
    @staticmethod
    async def get_reserve_ledger_summary(db: AsyncSession) -> Dict[str, Any]:
        """Get summary of system reserve ledger entries."""
        result = await db.execute(
            select(Ledger).filter(Ledger.user_id == SystemFundService.SYSTEM_USER_ID)
        )
        entries = result.scalars().all()
        
        total_debits = sum(
            float(e.amount) for e in entries if e.entry_type == "debit"
        )
        total_credits = sum(
            float(e.amount) for e in entries if e.entry_type == "credit"
        )
        
        return {
            "total_entries": len(entries),
            "total_debits": total_debits,
            "total_credits": total_credits,
            "net_balance": total_credits - total_debits,
            "entries": [{
                "id": e.id,
                "entry_type": e.entry_type,
                "amount": float(e.amount),
                "description": e.description,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None
            } for e in entries]
        }
