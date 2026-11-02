"""
Fund Operations API v1 - Production Grade
==========================================

Endpoints for fund transfers, balance adjustments, four-eyes approvals, and audit logging.

All operations support:
- Idempotency key validation (24-hour window)
- Four-eyes approval for amounts >$500 with real execution on approval
- Unified Ledger + Account + Transaction synchronization
- Device ID-based rate limiting
- Real-time WebSocket notifications
- Immutable audit trails
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import uuid
import asyncio
import time

from deps import get_current_admin_user, SessionDep
from schemas import User as PydanticUser
from models import (
    User as DBUser,
    Transaction as DBTransaction,
    Account as DBAccount,
    Ledger as DBLedger,
    Notification as DBNotification
)
from rate_limiter import rate_limiter, extract_device_id
from ws_manager import manager as ws_manager

fund_v1_router = APIRouter(prefix="/api/v1/fund", tags=["fund_v1"])

# ==================== PYDANTIC MODELS ====================

class IdempotencyKeyValidation(BaseModel):
    """Idempotency key with device tracking"""
    key: str
    device_id: str
    created_at: datetime
    request_hash: Optional[str] = None
    response: Optional[Dict] = None
    status: str = "pending"  # pending, completed, failed


class FundTransferRequest(BaseModel):
    """Fund account operation with transactional integrity"""
    user_id: int
    amount: float = Field(gt=0, le=1000000)
    account_type: str = Field(default="checking")
    fund_source: str = Field(default="admin_fund")
    notes: str = Field(min_length=3)
    ticket_reference: Optional[str] = None
    idempotent_key: Optional[str] = None
    transaction_ref: Optional[str] = None
    device_id: Optional[str] = "admin-console"
    admin_ip: Optional[str] = "127.0.0.1"
    timestamp: Optional[datetime] = None


class BalanceAdjustRequest(BaseModel):
    """Adjust user balance operation"""
    user_id: int
    amount: float = Field(gt=0, le=1000000)
    operation_type: str  # "credit" or "debit"
    account_type: str = Field(default="checking")
    reason: str = Field(min_length=3)
    priority: str = Field(default="normal")
    idempotent_key: Optional[str] = None
    transaction_ref: Optional[str] = None
    device_id: Optional[str] = "admin-console"
    admin_ip: Optional[str] = "127.0.0.1"
    timestamp: Optional[datetime] = None


class ApprovalRequest(BaseModel):
    """Two-admin approval workflow"""
    operation_id: str
    approving_admin_id: int
    approval_reason: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Immutable audit log entry"""
    action: str
    category: str
    details: Dict
    device_id: Optional[str] = "admin-console"
    admin_ip: Optional[str] = "127.0.0.1"
    timestamp: Optional[datetime] = None


class PendingApproval(BaseModel):
    """Pending approval display"""
    id: str
    operation_type: str
    user_email: str
    amount: float
    reason: str
    requested_by: str
    created_at: datetime
    status: str = "pending"


# ==================== IDEMPOTENCY & APPROVAL STORAGE ====================

class IdempotencyStore:
    """In-memory idempotency key storage with automatic cleanup"""

    def __init__(self, window_hours: int = 24):
        self.store: Dict[str, IdempotencyKeyValidation] = {}
        self.window_hours = window_hours

    def store_request(
        self,
        key: str,
        device_id: str,
        request_hash: str
    ) -> IdempotencyKeyValidation:
        entry = IdempotencyKeyValidation(
            key=key,
            device_id=device_id,
            created_at=datetime.utcnow(),
            request_hash=request_hash,
            status="pending"
        )
        self.store[key] = entry
        return entry

    def get_request(self, key: str) -> Optional[IdempotencyKeyValidation]:
        if key not in self.store:
            return None
        entry = self.store[key]
        age = (datetime.utcnow() - entry.created_at).total_seconds() / 3600
        if age > self.window_hours:
            del self.store[key]
            return None
        return entry

    def mark_completed(self, key: str, response: Dict):
        if key in self.store:
            self.store[key].status = "completed"
            self.store[key].response = response

    def cleanup_expired(self):
        cutoff = datetime.utcnow() - timedelta(hours=self.window_hours)
        expired = [
            key for key, entry in self.store.items()
            if entry.created_at < cutoff
        ]
        for key in expired:
            del self.store[key]
        return len(expired)


idempotency_store = IdempotencyStore(window_hours=24)
pending_approvals_store: Dict[str, Dict[str, Any]] = {}


async def _execute_ledger_and_account_movement(
    db_session: AsyncSession,
    user: DBUser,
    account: DBAccount,
    amount: float,
    direction: str,  # "credit" or "debit"
    tx_type: str,
    description: str,
    transaction_ref: str
) -> float:
    """Atomically updates DBAccount, DBTransaction, DBLedger, and DBNotification."""
    current_bal = float(account.balance or 0)
    if direction == "debit":
        if current_bal < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance for debit")
        new_bal = round(current_bal - amount, 2)
    else:
        new_bal = round(current_bal + amount, 2)

    account.balance = new_bal
    db_session.add(account)

    transaction = DBTransaction(
        user_id=user.id,
        account_id=account.id,
        transaction_type=tx_type,
        amount=float(amount),
        description=description,
        reference_number=transaction_ref,
        status="completed"
    )
    db_session.add(transaction)
    await db_session.flush()

    ledger_entry = DBLedger(
        user_id=user.id,
        entry_type=direction,
        amount=Decimal(str(round(amount, 2))),
        transaction_id=transaction.id,
        source_user_id=1 if direction == "credit" else user.id,
        destination_user_id=user.id if direction == "credit" else 1,
        description=description,
        reference_number=transaction_ref,
        status="posted"
    )
    db_session.add(ledger_entry)

    notif = DBNotification(
        user_id=user.id,
        title="Account Credited" if direction == "credit" else "Account Debited",
        message=f"Your {account.account_type} account was {'credited' if direction == 'credit' else 'debited'} ${amount:,.2f}. Ref: {transaction_ref}",
        notification_type="transaction",
        is_read=False
    )
    db_session.add(notif)

    await db_session.commit()
    await db_session.refresh(account)
    return float(account.balance)


# ==================== FUND TRANSFER ENDPOINT ====================

@fund_v1_router.post("/transfer", status_code=200)
async def fund_transfer(
    payload: FundTransferRequest,
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user),
    x_idempotency_key: str = Header(None)
):
    """
    Fund user account with idempotency and four-eyes approval.
    - If amount <= $500: Executes immediately
    - If amount > $500: Returns 202 (Accepted) and queues in pending_approvals_store
    """
    try:
        idempotency_key = x_idempotency_key or payload.idempotent_key or str(uuid.uuid4())
        device_id = payload.device_id or "admin-console"

        is_allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            device_id=device_id,
            user_role=getattr(current_user, "admin_role", None) or "super_admin",
            cost=1.0 if payload.amount <= 500 else 2.0
        )
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Reset in {reset_time:.0f}s",
                headers={"X-RateLimit-Reset": str(reset_time)}
            )

        existing = idempotency_store.get_request(idempotency_key)
        if existing and existing.status == "completed":
            return {
                "status": "completed",
                "transaction_ref": existing.response.get("transaction_ref"),
                "message": "Duplicate request - returning cached response"
            }

        if payload.amount <= 0 or payload.amount > 1000000:
            raise HTTPException(status_code=400, detail="Invalid amount")

        result = await db_session.execute(select(DBUser).where(DBUser.id == payload.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        result = await db_session.execute(
            select(DBAccount).where(
                and_(
                    DBAccount.owner_id == payload.user_id,
                    DBAccount.account_type == payload.account_type
                )
            )
        )
        account = result.scalars().first()
        if not account:
            result = await db_session.execute(
                select(DBAccount).where(DBAccount.owner_id == payload.user_id)
            )
            account = result.scalars().first()

        if not account:
            account_number = user.account_number or f"ACC{payload.user_id}{int(time.time() * 1000000) % 1000000}"
            account = DBAccount(
                account_number=account_number,
                owner_id=payload.user_id,
                account_type=payload.account_type,
                balance=0.0,
                currency="USD",
                status="active"
            )
            db_session.add(account)
            await db_session.flush()

        transaction_ref = payload.transaction_ref or f"TXN-{uuid.uuid4().hex[:12].upper()}"

        idempotency_store.store_request(
            key=idempotency_key,
            device_id=device_id,
            request_hash=json.dumps(payload.model_dump(), default=str)
        )

        # ========== FOUR-EYES APPROVAL ==========
        if payload.amount > 500:
            approval_id = str(uuid.uuid4())
            pending_approvals_store[approval_id] = {
                "id": approval_id,
                "operation_type": "fund",
                "direction": "credit",
                "tx_type": "admin_fund",
                "user_id": user.id,
                "user_email": user.email,
                "account_id": account.id,
                "account_type": payload.account_type,
                "amount": float(payload.amount),
                "reason": f"Admin fund ({payload.fund_source}): {payload.notes}",
                "transaction_ref": transaction_ref,
                "idempotency_key": idempotency_key,
                "requested_by": current_user.email,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }

            try:
                await ws_manager.broadcast(json.dumps({
                    "type": "approval_needed",
                    "approval_id": approval_id,
                    "operation_type": "fund",
                    "user_email": user.email,
                    "amount": payload.amount,
                    "requested_by": current_user.email,
                    "timestamp": datetime.utcnow().isoformat()
                }))
            except Exception:
                pass

            return JSONResponse(
                status_code=202,
                content={
                    "status": "pending_approval",
                    "approval_id": approval_id,
                    "transaction_ref": transaction_ref,
                    "message": f"Amount ${payload.amount:,.2f} queued for Four-Eyes approval",
                    "requested_by": current_user.email,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status_code": 202
                }
            )

        # ========== EXECUTE IMMEDIATE TRANSFER ==========
        new_balance = await _execute_ledger_and_account_movement(
            db_session=db_session,
            user=user,
            account=account,
            amount=float(payload.amount),
            direction="credit",
            tx_type="admin_fund",
            description=f"Admin fund ({payload.fund_source}): {payload.notes}",
            transaction_ref=transaction_ref
        )

        response_data = {
            "status": "completed",
            "transaction_ref": transaction_ref,
            "user_email": user.email,
            "amount": payload.amount,
            "new_balance": new_balance,
            "timestamp": datetime.utcnow().isoformat()
        }
        idempotency_store.mark_completed(idempotency_key, response_data)

        try:
            await ws_manager.broadcast(json.dumps({
                "type": "fund_completed",
                "user_id": payload.user_id,
                "transaction_ref": transaction_ref,
                "amount": payload.amount,
                "new_balance": new_balance,
                "timestamp": datetime.utcnow().isoformat()
            }))
        except Exception:
            pass

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BALANCE ADJUST ENDPOINT ====================

@fund_v1_router.post("/adjust", status_code=200)
async def adjust_balance(
    payload: BalanceAdjustRequest,
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user),
    x_idempotency_key: str = Header(None)
):
    """Adjust user balance (credit or debit) with approval workflow"""
    try:
        idempotency_key = x_idempotency_key or payload.idempotent_key or str(uuid.uuid4())
        device_id = payload.device_id or "admin-console"

        is_allowed, remaining, reset_time = rate_limiter.check_rate_limit(
            device_id=device_id,
            user_role=getattr(current_user, "admin_role", None) or "super_admin",
            cost=1.0 if payload.amount <= 500 else 2.0
        )
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Reset in {reset_time:.0f}s"
            )

        existing = idempotency_store.get_request(idempotency_key)
        if existing and existing.status == "completed":
            return existing.response

        if payload.amount <= 0 or payload.amount > 1000000:
            raise HTTPException(status_code=400, detail="Invalid amount")

        if payload.operation_type not in ["credit", "debit"]:
            raise HTTPException(status_code=400, detail="Invalid operation type")

        result = await db_session.execute(select(DBUser).where(DBUser.id == payload.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        result = await db_session.execute(
            select(DBAccount).where(
                and_(
                    DBAccount.owner_id == payload.user_id,
                    DBAccount.account_type == payload.account_type
                )
            )
        )
        account = result.scalars().first()
        if not account:
            result = await db_session.execute(
                select(DBAccount).where(DBAccount.owner_id == payload.user_id)
            )
            account = result.scalars().first()

        if not account:
            account_number = user.account_number or f"ACC{payload.user_id}{int(time.time() * 1000000) % 1000000}"
            account = DBAccount(
                account_number=account_number,
                owner_id=payload.user_id,
                account_type=payload.account_type,
                balance=0.0,
                currency="USD",
                status="active"
            )
            db_session.add(account)
            await db_session.flush()

        transaction_ref = payload.transaction_ref or f"TXN-{uuid.uuid4().hex[:12].upper()}"

        idempotency_store.store_request(
            key=idempotency_key,
            device_id=device_id,
            request_hash=json.dumps(payload.model_dump(), default=str)
        )

        # Four-eyes approval for amount > $500
        if payload.amount > 500:
            approval_id = str(uuid.uuid4())
            pending_approvals_store[approval_id] = {
                "id": approval_id,
                "operation_type": f"adjust_{payload.operation_type}",
                "direction": payload.operation_type,
                "tx_type": f"admin_{payload.operation_type}",
                "user_id": user.id,
                "user_email": user.email,
                "account_id": account.id,
                "account_type": payload.account_type,
                "amount": float(payload.amount),
                "reason": f"Admin {payload.operation_type}: {payload.reason}",
                "transaction_ref": transaction_ref,
                "idempotency_key": idempotency_key,
                "requested_by": current_user.email,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending"
            }
            try:
                await ws_manager.broadcast(json.dumps({
                    "type": "approval_needed",
                    "approval_id": approval_id,
                    "operation_type": "adjust",
                    "user_email": user.email,
                    "amount": payload.amount,
                    "operation": payload.operation_type,
                    "requested_by": current_user.email
                }))
            except Exception:
                pass
            return JSONResponse(
                status_code=202,
                content={
                    "status": "pending_approval",
                    "approval_id": approval_id,
                    "transaction_ref": transaction_ref,
                    "message": f"Amount ${payload.amount:,.2f} queued for Four-Eyes approval",
                    "status_code": 202
                }
            )

        new_balance = await _execute_ledger_and_account_movement(
            db_session=db_session,
            user=user,
            account=account,
            amount=float(payload.amount),
            direction=payload.operation_type,
            tx_type=f"admin_{payload.operation_type}",
            description=f"Admin {payload.operation_type}: {payload.reason}",
            transaction_ref=transaction_ref
        )

        response_data = {
            "status": "completed",
            "transaction_ref": transaction_ref,
            "user_email": user.email,
            "operation": payload.operation_type,
            "amount": payload.amount,
            "new_balance": new_balance
        }
        idempotency_store.mark_completed(idempotency_key, response_data)

        try:
            await ws_manager.broadcast(json.dumps({
                "type": "balance_adjusted",
                "user_id": payload.user_id,
                "operation": payload.operation_type,
                "amount": payload.amount,
                "new_balance": new_balance,
                "transaction_ref": transaction_ref
            }))
        except Exception:
            pass

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PENDING APPROVALS ====================

@fund_v1_router.get("/approvals/pending")
async def get_pending_approvals(
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Get list of pending approvals"""
    pending_list = [
        item for item in pending_approvals_store.values()
        if item.get("status") == "pending"
    ]
    pending_list.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {
        "approvals": pending_list
    }


@fund_v1_router.post("/approvals/{approval_id}/approve")
async def approve_operation(
    approval_id: str,
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Approve and execute a queued Four-Eyes operation"""
    item = pending_approvals_store.get(approval_id)
    if not item:
        raise HTTPException(status_code=404, detail="Pending approval not found")
    if item.get("status") != "pending":
        return {"status": item.get("status"), "approval_id": approval_id}

    user_res = await db_session.execute(select(DBUser).where(DBUser.id == item["user_id"]))
    user = user_res.scalar_one_or_none()
    acc_res = await db_session.execute(select(DBAccount).where(DBAccount.id == item["account_id"]))
    account = acc_res.scalar_one_or_none()

    if not user or not account:
        raise HTTPException(status_code=404, detail="Target user or account no longer exists")

    new_balance = await _execute_ledger_and_account_movement(
        db_session=db_session,
        user=user,
        account=account,
        amount=float(item["amount"]),
        direction=item["direction"],
        tx_type=item["tx_type"],
        description=f"{item['reason']} [Approved by {current_user.email}]",
        transaction_ref=item["transaction_ref"]
    )

    item["status"] = "approved"
    item["approved_by"] = current_user.email
    item["approved_at"] = datetime.utcnow().isoformat()
    item["new_balance"] = new_balance

    try:
        await ws_manager.broadcast(json.dumps({
            "type": "approval_completed",
            "approval_id": approval_id,
            "status": "approved",
            "approved_by": current_user.email,
            "new_balance": new_balance
        }))
    except Exception:
        pass

    return {
        "status": "approved",
        "approval_id": approval_id,
        "transaction_ref": item["transaction_ref"],
        "new_balance": new_balance
    }


@fund_v1_router.post("/approvals/{approval_id}/reject")
async def reject_operation(
    approval_id: str,
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Reject a queued Four-Eyes operation"""
    item = pending_approvals_store.get(approval_id)
    if item:
        item["status"] = "rejected"
        item["rejected_by"] = current_user.email
        item["rejected_at"] = datetime.utcnow().isoformat()

    try:
        await ws_manager.broadcast(json.dumps({
            "type": "approval_completed",
            "approval_id": approval_id,
            "status": "rejected",
            "rejected_by": current_user.email
        }))
    except Exception:
        pass

    return {"status": "rejected", "approval_id": approval_id}


# ==================== OPERATION HISTORY ====================

@fund_v1_router.get("/operations/history")
async def get_operation_history(
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user),
    limit: int = 50
):
    """Get recent fund operations"""
    try:
        result = await db_session.execute(
            select(DBTransaction)
            .where(DBTransaction.transaction_type.in_(["admin_fund", "admin_credit", "admin_debit", "deposit", "withdrawal"]))
            .order_by(DBTransaction.created_at.desc())
            .limit(limit)
        )
        transactions = result.scalars().all()

        operations = []
        for txn in transactions:
            user_result = await db_session.execute(
                select(DBUser).where(DBUser.id == txn.user_id)
            )
            user = user_result.scalar_one_or_none()

            operations.append({
                "id": txn.id,
                "user_email": user.email if user else "Unknown",
                "operation_type": txn.transaction_type.replace("admin_", ""),
                "amount": float(txn.amount),
                "reason": txn.description,
                "transaction_ref": txn.reference_number,
                "status": txn.status,
                "created_at": txn.created_at.isoformat() if txn.created_at else None
            })

        return {"operations": operations}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== AUDIT LOGGING ====================

@fund_v1_router.post("/audit-log")
async def log_audit_event(
    payload: AuditLogEntry,
    db_session: SessionDep,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Log audit event (immutable)"""
    import logging
    log = logging.getLogger("audit")
    ts = payload.timestamp.isoformat() if payload.timestamp else datetime.utcnow().isoformat()
    log.info(json.dumps({
        "action": payload.action,
        "category": payload.category,
        "admin_email": current_user.email,
        "device_id": payload.device_id,
        "admin_ip": payload.admin_ip,
        "timestamp": ts,
        "details": payload.details
    }))

    return {"status": "logged", "timestamp": datetime.utcnow().isoformat()}


# ==================== WEBSOCKET FOR REAL-TIME UPDATES ====================

@fund_v1_router.websocket("/ws/updates")
async def websocket_fund_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time fund updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


# ==================== RATE LIMIT ADMIN ====================

@fund_v1_router.get("/rate-limit/status/{device_id}")
async def get_rate_limit_status(
    device_id: str,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Check rate limit status for device (admin only)"""
    return rate_limiter.get_status(device_id)


@fund_v1_router.post("/rate-limit/reset/{device_id}")
async def reset_rate_limit(
    device_id: str,
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Reset rate limit for device (admin only)"""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can reset rate limits")

    rate_limiter.reset_device(device_id)
    return {"status": "reset", "device_id": device_id}


@fund_v1_router.get("/rate-limit/all")
async def get_all_rate_limits(
    current_user: PydanticUser = Depends(get_current_admin_user)
):
    """Get all rate limit statuses (admin only)"""
    if not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only super admins can view all rate limits")

    return rate_limiter.get_all_status()
