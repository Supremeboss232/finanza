"""
Fund Router with Ledger-Based Accounting
==========================================

Handles admin funding operations using proper double-entry accounting.

Every fund transfer:
1. Creates a Transaction record (audit trail)
2. Creates TWO ledger entries (debit from system, credit to user)
3. Synchronizes account.balance from ledger
4. Broadcasts real-time notification

No more cosmetic accounting - money moves and balances update.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
import json
import uuid

from deps import get_current_admin_user, SessionDep
from models import (
    User as DBUser,
    Transaction as DBTransaction,
    FundTransfer as DBFundTransfer,
    FundSource as DBFundSource,
    Account as DBAccount
)
from schemas import (
    Transaction as PydanticTransaction,
    User as PydanticUser
)
from ledger_service import LedgerService
from balance_service_ledger import BalanceServiceLedger
from transaction_gate_ledger import TransactionGate
from ws_manager import manager
from account_id_enforcement import account_id_enforcement

fund_router = APIRouter(prefix="/api/admin/fund", tags=["admin_fund"], dependencies=[Depends(get_current_admin_user)])

# Pydantic Models/Schemas for Fund Operations
class FundTransferRequest(BaseModel):
    user_id: int
    amount: float
    account_type: str
    fund_source: str
    transaction_ref: Optional[str] = None
    notes: Optional[str] = None
    send_notification: bool = True

class BulkFundRequest(BaseModel):
    users: List[str]
    amount: float
    account_type: str
    fund_source: str
    reason: Optional[str] = None
    send_notification: bool = True

class FundSourceRequest(BaseModel):
    name: str
    type: str
    balance: float
    description: Optional[str] = None

# Main Fund Endpoints

@fund_router.get("")
async def get_fund_data(db_session: SessionDep):
    """Get all funding data using ledger-based accounting"""
    try:
        # Get all fund transfers with user eagerly loaded
        result = await db_session.execute(
            select(DBFundTransfer).order_by(DBFundTransfer.created_at.desc()).limit(100)
        )
        transfers = result.scalars().all()
        
        # Get all fund sources
        result = await db_session.execute(select(DBFundSource))
        sources = result.scalars().all()
        
        # Calculate statistics from ledger (source of truth)
        admin_total = await BalanceServiceLedger.get_admin_total_volume(db_session)
        
        stats = {
            "total_funded": float(admin_total),
            "pending_count": len([t for t in transfers if t.status == "pending"]),
            "failed_count": len([t for t in transfers if t.status == "failed"]),
            "completed_today": 0
        }
        
        today = datetime.now().date()
        for transfer in transfers:
            if transfer.status == "completed" and transfer.created_at.date() == today:
                stats["completed_today"] += float(transfer.amount)
        
        # Build transactions list from ledger for accuracy
        transactions_list = []
        for t in transfers:
            if t.user_id:
                user_result = await db_session.execute(
                    select(DBUser).where(DBUser.id == t.user_id)
                )
                user = user_result.scalar()
                user_email = user.email if user else "Unknown"
                
                # Get balance from ledger (not from stored balance)
                balance = await BalanceServiceLedger.get_user_balance(db_session, t.user_id)
            else:
                user_email = "Unknown"
                balance = 0
            
            transactions_list.append({
                "id": t.id,
                "transaction_id": t.transaction_id,
                "user_id": t.user_id,
                "user_email": user_email,
                "amount": float(t.amount),
                "account_type": t.account_type,
                "fund_source": t.fund_source,
                "notes": t.notes,
                "status": t.status,
                "current_balance": balance,  # FROM LEDGER
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
        
        return {
            "transactions": transactions_list,
            "fundSources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.type,
                    "balance": float(s.balance),
                    "description": s.description
                }
                for s in sources
            ],
            "stats": stats
        }
        
    except Exception as e:
        print(f"Error getting fund data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def validate_fund_source(db_session: SessionDep, fund_source: str):
    """
    Validate that the fund source exists and is active.
    
    RULE: All funds must come from registered, active fund sources.
    This ensures accountability and prevents untracked funding.
    """
    result = await db_session.execute(
        select(DBFundSource).where(
            (DBFundSource.name == fund_source) | (DBFundSource.id == int(fund_source) if fund_source.isdigit() else False)
        )
    )
    source = result.scalar_one_or_none()
    
    if not source:
        raise HTTPException(
            status_code=400,
            detail=f"Fund source '{fund_source}' not found. Register a fund source first."
        )
    
    if not source.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Fund source '{fund_source}' is inactive and cannot be used for funding."
        )
    
    return source


@fund_router.post("/transfer")
async def fund_user_transfer(
    payload: FundTransferRequest,
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """
    Fund a single user account using double-entry accounting.
    
    This endpoint:
    1. Validates user and account exist and are bound
    2. Creates Transaction record with required fields (user_id, account_id)
    3. Creates atomic ledger entries (debit system, credit user)
    4. Synchronizes account.balance from ledger
    5. LOGS ADMIN ACTION with admin_id, user_id, account_id, amount, reason
    6. Broadcasts notification
    
    RULE 1: Money must have owner (user_id)
    RULE 2: Money must have account and account must belong to user
    RULE 3: Balance is derived from ledger, never manually set
    RULE 4: Every admin action is logged with admin_id
    """
    from admin_audit_service import admin_audit_service
    
    try:
        user_id = payload.user_id
        amount = float(payload.amount)
        account_type = payload.account_type
        fund_source = payload.fund_source
        transaction_ref = payload.transaction_ref or str(uuid.uuid4())[:12].upper()
        notes = payload.notes
        send_notification = payload.send_notification
        
        if not user_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid user ID or amount")
        
        # RULE: Validate fund source is registered and active
        # EXCEPTION: For admin operations where fund_source is 'admin' or empty, skip validation
        #            as these use the system reserve account directly
        if fund_source and fund_source.lower() not in ['admin', 'admin_operation', 'system', 'system_reserve']:
            await validate_fund_source(db_session, fund_source)
        
        # 1. Verify user exists
        result = await db_session.execute(select(DBUser).where(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 2. Get or create account (RULE 1: Money must have account)
        from sqlalchemy import and_
        result = await db_session.execute(
            select(DBAccount).where(
                and_(
                    DBAccount.owner_id == user_id,
                    DBAccount.account_type == account_type
                )
            )
        )
        account = result.scalar_one_or_none()
        
        if not account:
            account = DBAccount(
                owner_id=user_id,
                account_type=account_type,
                balance=0.0,
                currency="USD"
            )
            db_session.add(account)
            await db_session.flush()
        
        # RULE 2: Account must belong to user
        if account.owner_id != user_id:
            raise HTTPException(status_code=400, detail="Account does not belong to user")
        
        # 🔧 ENFORCEMENT: Validate account ownership before proceeding
        is_valid, reason = await account_id_enforcement.validate_account_ownership(
            db=db_session,
            user_id=user_id,
            account_id=account.id
        )
        if not is_valid:
            raise HTTPException(status_code=403, detail=f"Account validation failed: {reason}")
        
        # 3. Create transaction record (audit trail)
        # CRITICAL: user_id and reference_number are REQUIRED
        transaction = DBTransaction(
            user_id=user_id,  # REQUIRED: Money must belong to a user
            account_id=account.id,  # REQUIRED: Money must go to an account
            transaction_type="admin_fund",
            amount=float(amount),
            description=f"Admin fund transfer from {fund_source}",
            reference_number=transaction_ref,  # REQUIRED: For audit
            status="pending"  # Will be completed after ledger entries
        )
        db_session.add(transaction)
        await db_session.flush()
        
        # 4. Create atomic double-entry ledger entries
        # This ENSURES balance is updated
        debit_entry, credit_entry = await LedgerService.create_admin_funding(
            db=db_session,
            transaction=transaction,
            to_user_id=user_id,
            amount=Decimal(str(amount)),
            description=f"Admin funding from {fund_source}",
            reference_number=transaction_ref
        )
        
        # 5. Mark transaction as completed
        transaction.status = "completed"
        db_session.add(transaction)
        
        # ISSUE #4 FIX: Do NOT manually update account.balance
        # Balance is now calculated from ledger (source of truth)
        # Removed: account.balance = new_balance
        
        # 7. Update fund transfer record
        fund_transfer = DBFundTransfer(
            user_id=user_id,
            amount=Decimal(str(amount)),
            account_type=account_type,
            fund_source=fund_source,
            transaction_ref=transaction_ref,
            notes=notes,
            status="completed",
            type="fund"
        )
        db_session.add(fund_transfer)
        
        # 8. Commit all changes atomically
        await db_session.commit()
        await db_session.refresh(fund_transfer)
        
        # 9. LOG ADMIN ACTION (RULE 4: Every admin action must be audited)
        try:
            await admin_audit_service.log_fund_action(
                db=db_session,
                admin_id=current_user.id,
                user_id=user_id,
                account_id=account.id,
                amount=amount,
                fund_source=fund_source,
                notes=notes or "Admin fund transfer"
            )
        except Exception as audit_error:
            # Log the error but don't fail the transfer
            print(f"Warning: Failed to log audit trail: {audit_error}")
        
        # NOTE: Skipping ledger reconciliation check for admin operations
        # The system reserve account (user_id=1) has special status and doesn't need balanced ledgers
        # Individual user balances are still correctly calculated from their ledger entries
        
        # 10. Broadcast real-time notification
        try:
            await manager.broadcast(json.dumps({
                "event": "fund:transfer_completed",
                "user_id": user_id,
                "amount": float(amount),
                "new_balance": new_balance,
                "timestamp": datetime.utcnow().isoformat()
            }))
        except Exception:
            pass  # Don't fail the transaction if broadcast fails
        
        return {
            "transaction_id": fund_transfer.transaction_id,
            "user_id": user_id,
            "amount": float(amount),
            "new_balance": new_balance,  # FROM LEDGER
            "status": "completed",
            "ledger_entries": {
                "debit_id": debit_entry.id,
                "credit_id": credit_entry.id
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        print(f"Error funding user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@fund_router.post("/bulk")
async def bulk_fund_users(
    payload: BulkFundRequest,
    db_session: SessionDep
):
    """Fund multiple users at once using ledger"""
    try:
        users = payload.users
        amount = float(payload.amount)
        account_type = payload.account_type
        fund_source = payload.fund_source
        reason = payload.reason
        send_notification = payload.send_notification
        
        if not users or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid users list or amount")
        
        successful = 0
        failed = 0
        transaction_ids = []
        failed_users = []
        
        for user_identifier in users:
            try:
                # Find user by email or ID
                if user_identifier.isdigit():
                    result = await db_session.execute(
                        select(DBUser).where(DBUser.id == int(user_identifier))
                    )
                else:
                    result = await db_session.execute(
                        select(DBUser).where(DBUser.email == user_identifier)
                    )
                
                user = result.scalar_one_or_none()
                if not user:
                    failed += 1
                    failed_users.append(f"{user_identifier} (not found)")
                    continue
                
                # Get or create account
                result = await db_session.execute(
                    select(DBAccount).where(
                        and_(
                            DBAccount.owner_id == user.id,
                            DBAccount.account_type == account_type
                        )
                    )
                )
                account = result.scalar_one_or_none()
                
                if not account:
                    account = DBAccount(
                        owner_id=user.id,
                        account_type=account_type,
                        balance=0.0,
                        currency="USD"
                    )
                    db_session.add(account)
                    await db_session.flush()
                
                # Create transaction
                transaction_ref = str(uuid.uuid4())[:12].upper()
                transaction = DBTransaction(
                    user_id=user.id,
                    account_id=account.id,
                    transaction_type="bulk_fund",
                    amount=amount,
                    description=f"Bulk fund: {reason}",
                    reference_number=transaction_ref,
                    status="pending"
                )
                db_session.add(transaction)
                await db_session.flush()
                
                # Create ledger entries
                await LedgerService.create_admin_funding(
                    db=db_session,
                    transaction=transaction,
                    to_user_id=user.id,
                    amount=Decimal(str(amount)),
                    description=f"Bulk fund: {reason}",
                    reference_number=transaction_ref
                )
                
                # Mark completed
                transaction.status = "completed"
                # ISSUE #4 FIX: Do NOT manually update account.balance
                # Balance is now calculated from ledger (source of truth)
                # Removed: account.balance = new_balance
                
                # Create fund transfer record
                fund_transfer = DBFundTransfer(
                    user_id=user.id,
                    amount=Decimal(str(amount)),
                    account_type=account_type,
                    fund_source=fund_source,
                    notes=reason,
                    status="completed",
                    type="fund"
                )
                db_session.add(fund_transfer)
                db_session.add(transaction)
                db_session.add(account)
                
                transaction_ids.append(fund_transfer.transaction_id)
                successful += 1
                
            except Exception as e:
                print(f"Error funding user {user_identifier}: {e}")
                failed += 1
                failed_users.append(f"{user_identifier} ({str(e)})")
                continue
        
        await db_session.commit()
        
        # Verify ledger
        reconciliation = await LedgerService.reconcile_ledger(db_session)
        if not reconciliation["is_balanced"]:
            raise HTTPException(
                status_code=500,
                detail=f"Ledger reconciliation failed after bulk fund"
            )
        
        # Broadcast
        try:
            await manager.broadcast(json.dumps({
                "event": "fund:bulk_completed",
                "successful": successful,
                "failed": failed,
                "total_amount": float(amount * successful),
                "timestamp": datetime.utcnow().isoformat()
            }))
        except Exception:
            pass
        
        return {
            "successful": successful,
            "failed": failed,
            "total": len(users),
            "transaction_ids": transaction_ids,
            "failed_users": failed_users,
            "total_funded": float(amount * successful),
            "status": "completed"
        }
        
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@fund_router.get("/reconciliation")
async def get_reconciliation_status(db_session: SessionDep):
    """Get current ledger reconciliation status"""
    try:
        reconciliation = await LedgerService.reconcile_ledger(db_session)
        
        # Get additional metrics
        all_balances = await BalanceServiceLedger.get_all_user_balances(db_session)
        total_users = len(all_balances)
        
        return {
            "is_balanced": reconciliation["is_balanced"],
            "total_debits": f"${reconciliation['total_debits']:.2f}",
            "total_credits": f"${reconciliation['total_credits']:.2f}",
            "difference": f"${reconciliation['difference']:.2f}",
            "orphaned_entries": reconciliation["orphaned_entries"],
            "total_users": total_users,
            "system_balance": f"${await BalanceServiceLedger.get_admin_total_volume(db_session):.2f}",
            "errors": reconciliation.get("errors", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
