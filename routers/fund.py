from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel
import json

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
from ws_manager import manager
from system_fund_service import SystemFundService

fund_router = APIRouter(prefix="/api/admin/fund", tags=["admin_fund"], dependencies=[Depends(get_current_admin_user)])

# Helper function to get system reserve account
async def get_system_reserve_account(db_session: AsyncSession) -> DBAccount:
    """
    Get the system reserve account (SYS-RESERVE-0001).
    This is used as the source for all admin funding operations.
    """
    result = await db_session.execute(
        select(DBAccount).filter(DBAccount.account_number == "SYS-RESERVE-0001")
    )
    reserve_account = result.scalar_one_or_none()
    if not reserve_account:
        raise HTTPException(
            status_code=500,
            detail="System Reserve Account not found. Please restart the application."
        )
    return reserve_account

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
    """Get all funding data: transactions, sources, and statistics"""
    try:
        # Get all fund transfers with user eagerly loaded
        result = await db_session.execute(
            select(DBFundTransfer).order_by(DBFundTransfer.created_at.desc()).limit(100)
        )
        transfers = result.scalars().all()
        
        # Get all fund sources
        result = await db_session.execute(select(DBFundSource))
        sources = result.scalars().all()
        
        # Calculate statistics
        stats = {
            "total_funded": 0,
            "pending_count": 0,
            "failed_count": 0,
            "completed_today": 0
        }
        
        today = datetime.now().date()
        for transfer in transfers:
            stats["total_funded"] += float(transfer.amount)
            if transfer.status == "pending":
                stats["pending_count"] += 1
            elif transfer.status == "failed":
                stats["failed_count"] += 1
            
            if transfer.status == "completed" and transfer.created_at.date() == today:
                stats["completed_today"] += float(transfer.amount)
        
        # Build transactions list - fetch user separately to avoid lazy loading in async
        transactions_list = []
        for t in transfers:
            # Get user data in a single query
            if t.user_id:
                user_result = await db_session.execute(
                    select(DBUser.email).where(DBUser.id == t.user_id)
                )
                user_email = user_result.scalar() or "Unknown"
            else:
                user_email = "Unknown"
            
            transactions_list.append({
                "id": t.id,
                "transaction_id": t.transaction_id,
                "user_id": t.user_id,
                "user_email": user_email,
                "amount": float(t.amount),
                "type": t.type,
                "fund_source": t.fund_source,
                "account_type": t.account_type,
                "transaction_ref": t.transaction_ref,
                "notes": t.notes,
                "status": t.status,
                "created_at": t.created_at.isoformat()
            })
        
        return {
            "transactions": transactions_list,
            "fundSources": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.type,
                    "description": s.description,
                    "balance": float(s.balance),
                    "total_funded": float(s.total_funded or 0),
                    "is_active": s.is_active
                }
                for s in sources
            ],
            "stats": stats
        }
    except Exception as e:
        print(f"Error fetching fund data: {e}")
        return {
            "transactions": [],
            "fundSources": [],
            "stats": {"total_funded": 0, "pending_count": 0, "failed_count": 0, "completed_today": 0}
        }

@fund_router.post("/transfer")
async def fund_user_transfer(
    payload: FundTransferRequest,
    db_session: SessionDep,
    current_admin: DBUser = Depends(get_current_admin_user)
):
    """
    Fund a single user account from System Reserve Account.
    
    ⚠️ ADMIN OPERATION - Core Financial Transaction
    
    Process:
    1. Get/create target user account
    2. Use SystemFundService to create double-entry ledger
    3. FROM: SYS-RESERVE-0001 (debit)
    4. TO: User account (credit)
    5. Create audit log entry
    6. Update balance atomically
    
    Returns: Transaction details with ledger entry IDs
    """
    debug_log = f"[{datetime.now().isoformat()}] Fund transfer endpoint called\n"
    try:
        user_id = payload.user_id
        amount = float(payload.amount)
        account_type = payload.account_type
        fund_source = payload.fund_source or "admin_operation"
        transaction_ref = payload.transaction_ref
        notes = payload.notes
        
        debug_log += f"  Payload: user_id={user_id}, amount={amount}, account_type={account_type}\n"
        
        if not user_id or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid user ID or amount")
        
        # Get target user
        result = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        debug_log += f"  User found: {user.email}\n"
        
        # Get or create target account
        result = await db_session.execute(
            select(DBAccount).filter(
                DBAccount.owner_id == user_id,
                DBAccount.account_type == account_type
            )
        )
        account = result.scalar_one_or_none()
        debug_log += f"  Account lookup for user {user_id}/{account_type}: {account}\n"
        
        if not account:
            # Generate account number
            import time
            account_number = f"ACC-{user_id}-{int(time.time() * 1000) % 1000000}"
            debug_log += f"  Creating new account with number: {account_number}\n"
            account = DBAccount(
                account_number=account_number,
                owner_id=user_id,
                account_type=account_type,
                balance=0.0
            )
            db_session.add(account)
            await db_session.flush()
            debug_log += f"  New account created: ID={account.id}, Number={account.account_number}\n"
        
        old_balance = float(account.balance)
        
        # Use SystemFundService to perform the fund transfer
        debug_log += f"  Calling SystemFundService.fund_user_from_system...\n"
        result = await SystemFundService.fund_user_from_system(
            db=db_session,
            target_user_id=user_id,
            target_account_id=account.id,
            amount=amount,
            admin_user_id=current_admin.id,
            reason=notes or f"Admin funding via {fund_source}"
        )
        
        debug_log += f"  SystemFundService result: {result}\n"
        
        if not result["success"]:
            debug_log += f"  ❌ Fund transfer failed: {result.get('error')}\n"
            with open('/tmp/fund_debug.log', 'a') as f:
                f.write(debug_log)
            raise HTTPException(status_code=500, detail=f"Fund transfer failed: {result.get('error')}")
        
        debug_log += f"  ✅ Fund transfer successful\n"
        
        # Broadcast notification
        try:
            await manager.broadcast(json.dumps({
                "event": "fund:transfer_completed",
                "user_id": user_id,
                "amount": amount,
                "new_balance": result["new_balance"],
                "source": "SYS-RESERVE-0001",
                "admin_id": current_admin.id,
                "timestamp": result["timestamp"]
            }))
        except Exception:
            pass
        
        # Return comprehensive response
        with open('/tmp/fund_debug.log', 'a') as f:
            f.write(debug_log)
        
        return {
            "success": True,
            "transaction_id": result["transaction_id"],
            "debit_entry_id": result["debit_entry_id"],
            "credit_entry_id": result["credit_entry_id"],
            "audit_log_id": result["audit_log_id"],
            "user_id": user_id,
            "amount": amount,
            "old_balance": old_balance,
            "new_balance": result["new_balance"],
            "source_account": "SYS-RESERVE-0001",
            "target_account": result["target_account"],
            "status": "completed",
            "initiated_by_admin_id": current_admin.id,
            "timestamp": result["timestamp"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"[{datetime.now().isoformat()}] Fund transfer failed: {str(e)}\n"
        import traceback
        error_msg += traceback.format_exc()
        debug_log += f"  ❌ Exception: {str(e)}\n"
        debug_log += traceback.format_exc() + "\n"
        with open('/tmp/fund_debug.log', 'a') as f:
            f.write(debug_log)
            f.write(error_msg)
        raise HTTPException(status_code=500, detail=f"Fund transfer failed: {str(e)}")

@fund_router.post("/bulk")
async def bulk_fund_users(
    payload: BulkFundRequest,
    db_session: SessionDep
):
    """Fund multiple users at once"""
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
        
        for user_identifier in users:
            try:
                # Find user by email or ID
                if user_identifier.isdigit():
                    result = await db_session.execute(
                        select(DBUser).filter(DBUser.id == int(user_identifier))
                    )
                else:
                    result = await db_session.execute(
                        select(DBUser).filter(DBUser.email == user_identifier)
                    )
                
                user = result.scalar_one_or_none()
                if not user:
                    failed += 1
                    continue
                
                # Get or create account
                result = await db_session.execute(
                    select(DBAccount).filter(
                        DBAccount.owner_id == user.id,
                        DBAccount.account_type == account_type
                    )
                )
                account = result.scalar_one_or_none()
                
                if not account:
                    account = DBAccount(
                        user_id=user.id,
                        account_type=account_type,
                        balance=0.0
                    )
                    db_session.add(account)
                    await db_session.flush()
                
                # Update balance
                account.balance = float(account.balance) + amount
                
                # Create fund transfer
                transfer = DBFundTransfer(
                    user_id=user.id,
                    amount=Decimal(str(amount)),
                    account_type=account_type,
                    fund_source=fund_source,
                    notes=reason,
                    status="completed",
                    type="fund"
                )
                db_session.add(transfer)
                
                # Create transaction
                transaction = DBTransaction(
                    user_id=user.id,
                    account_id=account.id,
                    transaction_type="bulk_fund",
                    amount=Decimal(str(amount)),
                    description=f"Bulk fund: {reason}",
                    status="completed"
                )
                db_session.add(transaction)
                
                transaction_ids.append(transfer.transaction_id)
                successful += 1
                
            except Exception as e:
                print(f"Error funding user {user_identifier}: {e}")
                failed += 1
                continue
        
        await db_session.commit()
        
        # Broadcast
        try:
            await manager.broadcast(json.dumps({
                "event": "fund:bulk_completed",
                "successful": successful,
                "failed": failed,
                "total_amount": float(amount * successful)
            }))
        except Exception:
            pass
        
        return {
            "successful": successful,
            "failed": failed,
            "total_funded": float(amount * successful),
            "transaction_ids": transaction_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        print(f"Error in bulk funding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@fund_router.get("/transfer/{transfer_id}")
async def get_transfer_details(transfer_id: int, db_session: SessionDep):
    """Get details of a specific fund transfer"""
    result = await db_session.execute(
        select(DBFundTransfer).filter(DBFundTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    return {
        "id": transfer.id,
        "transaction_id": transfer.transaction_id,
        "user_id": transfer.user_id,
        "user_email": transfer.user.email if transfer.user else "Unknown",
        "amount": float(transfer.amount),
        "type": transfer.type,
        "fund_source": transfer.fund_source,
        "account_type": transfer.account_type,
        "transaction_ref": transfer.transaction_ref,
        "notes": transfer.notes,
        "status": transfer.status,
        "created_at": transfer.created_at.isoformat()
    }

@fund_router.post("/retry/{transfer_id}")
async def retry_failed_transfer(transfer_id: int, db_session: SessionDep):
    """Retry a failed fund transfer"""
    result = await db_session.execute(
        select(DBFundTransfer).filter(DBFundTransfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if transfer.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed transfers can be retried")
    
    try:
        # Get user and account
        user = transfer.user
        result = await db_session.execute(
            select(DBAccount).filter(
                DBAccount.owner_id == transfer.user_id,
                DBAccount.account_type == transfer.account_type
            )
        )
        account = result.scalar_one_or_none()
        
        if account:
            account.balance = float(account.balance) + float(transfer.amount)
        
        transfer.status = "completed"
        await db_session.commit()
        
        return {"status": "success", "message": "Transfer retried successfully"}
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# Fund Sources Management

@fund_router.get("/sources")
async def get_fund_sources(db_session: SessionDep):
    """Get all fund sources"""
    result = await db_session.execute(select(DBFundSource))
    sources = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "type": s.type,
            "description": s.description,
            "balance": float(s.balance),
            "total_funded": float(s.total_funded or 0),
            "is_active": s.is_active
        }
        for s in sources
    ]

@fund_router.post("/sources")
async def create_fund_source(payload: FundSourceRequest, db_session: SessionDep):
    """Create a new fund source"""
    try:
        source = DBFundSource(
            name=payload.name,
            type=payload.type,
            balance=Decimal(str(payload.balance)),
            description=payload.description,
            is_active=True
        )
        db_session.add(source)
        await db_session.commit()
        await db_session.refresh(source)
        
        return {
            "id": source.id,
            "name": source.name,
            "type": source.type,
            "description": source.description,
            "balance": float(source.balance),
            "is_active": source.is_active
        }
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@fund_router.delete("/sources/{source_id}")
async def delete_fund_source(source_id: int, db_session: SessionDep):
    """Delete a fund source"""
    result = await db_session.execute(
        select(DBFundSource).filter(DBFundSource.id == source_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Fund source not found")
    
    await db_session.delete(source)
    await db_session.commit()
    return {"status": "deleted"}

# User Search for Fund Operations

@fund_router.get("/users/search")
async def search_users_for_funding(q: str, db_session: SessionDep):
    """Search users for funding operations"""
    if len(q) < 2:
        return []
    
    result = await db_session.execute(
        select(DBUser).where(
            (DBUser.email.ilike(f"%{q}%")) |
            (DBUser.full_name.ilike(f"%{q}%")) |
            (DBUser.id == int(q) if q.isdigit() else False)
        ).limit(20)
    )
    users = result.scalars().all()
    
    # Get account info for each user
    user_list = []
    for user in users:
        # Get total balance across all accounts
        balance_result = await db_session.execute(
            select(func.sum(DBAccount.balance)).filter(DBAccount.owner_id == user.id)
        )
        total_balance = balance_result.scalar() or 0
        
        user_list.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "balance": float(total_balance),
            "is_active": user.is_active,
            "account_number": getattr(user, 'account_number', None)
        })
    
    return user_list
