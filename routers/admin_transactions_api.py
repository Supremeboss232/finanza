"""
Admin Transactions API Router
Provides admin dashboard endpoints for transaction metrics, disputes, and returns
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Dict, List

from deps import SessionDep, get_current_admin_user
from models import Transaction, TransactionDispute, ReturnProcessing, User as DBUser


admin_transactions_router = APIRouter(
    prefix="/api/v1/transactions",
    tags=["admin-transactions"],
    dependencies=[Depends(get_current_admin_user)]
)


@admin_transactions_router.get("")
async def list_transactions(
    db_session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: str = Query(None),
    transaction_type: str = Query(None),
    direction: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    min_amount: float = Query(None, ge=0),
    max_amount: float = Query(None, ge=0),
    search: str = Query(None)
):
    """Get all transactions with advanced filtering"""
    try:
        query = select(Transaction).join(DBUser, Transaction.user_id == DBUser.id)
        
        if status:
            query = query.where(Transaction.status == status)
        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)
        if direction:
            query = query.where(Transaction.direction == direction)
        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.where(Transaction.created_at >= start_dt)
            except:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.where(Transaction.created_at <= end_dt)
            except:
                pass
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (DBUser.email.ilike(search_term)) |
                (Transaction.id.cast(str).contains(search))
            )
        
        # Get total count
        count_query = select(func.count(Transaction.id)).select_from(Transaction)
        if status:
            count_query = count_query.where(Transaction.status == status)
        if transaction_type:
            count_query = count_query.where(Transaction.transaction_type == transaction_type)
        if direction:
            count_query = count_query.where(Transaction.direction == direction)
        if min_amount is not None:
            count_query = count_query.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            count_query = count_query.where(Transaction.amount <= max_amount)
        
        total = await db_session.scalar(count_query) or 0
        
        # Apply sorting and pagination
        query = query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit)
        result = await db_session.execute(query)
        transactions = result.unique().scalars().all()
        
        transactions_list = []
        for txn in transactions:
            transactions_list.append({
                "id": txn.id,
                "user_id": txn.user_id,
                "user_email": txn.user.email if txn.user else None,
                "amount": float(txn.amount),
                "status": txn.status,
                "type": txn.transaction_type,
                "transaction_type": txn.transaction_type,
                "direction": getattr(txn, "direction", None),
                "description": txn.description,
                "reference_number": txn.reference_number or f"TXN-{txn.id}",
                "timestamp": txn.created_at.isoformat() if txn.created_at else None,
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
                "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
                "transaction_hash": None,
                "txid": None,
                "exchange_rate": 1.0
            })
        
        return {
            "success": True,
            "data": transactions_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "total": 0
        }


@admin_transactions_router.get("/metrics")
async def get_transaction_metrics(db_session: SessionDep):
    """Get transaction metrics and analytics for admin dashboard"""
    try:
        today = datetime.utcnow().date()
        
        # Total transactions count
        total_count_query = select(func.count(Transaction.id))
        total_transactions = await db_session.scalar(total_count_query) or 0
        
        # 24-hour metrics
        last_24h = datetime.utcnow() - timedelta(hours=24)
        completed_24h_query = select(func.count(Transaction.id)).where(
            (Transaction.status == "completed") & (Transaction.created_at >= last_24h)
        )
        completed_24h = await db_session.scalar(completed_24h_query) or 0
        
        failed_24h_query = select(func.count(Transaction.id)).where(
            (Transaction.status == "failed") & (Transaction.created_at >= last_24h)
        )
        failed_24h = await db_session.scalar(failed_24h_query) or 0
        
        pending_24h_query = select(func.count(Transaction.id)).where(
            (Transaction.status == "pending") & (Transaction.created_at >= last_24h)
        )
        pending_24h = await db_session.scalar(pending_24h_query) or 0
        
        volume_24h_query = select(func.sum(Transaction.amount)).where(
            Transaction.created_at >= last_24h
        )
        volume_24h = await db_session.scalar(volume_24h_query) or 0
        
        # Status breakdown
        status_completed_query = select(func.count(Transaction.id)).where(
            Transaction.status == "completed"
        )
        status_completed = await db_session.scalar(status_completed_query) or 0
        
        status_pending_query = select(func.count(Transaction.id)).where(
            Transaction.status == "pending"
        )
        status_pending = await db_session.scalar(status_pending_query) or 0
        
        status_failed_query = select(func.count(Transaction.id)).where(
            Transaction.status == "failed"
        )
        status_failed = await db_session.scalar(status_failed_query) or 0
        
        return {
            "success": True,
            "total_transactions": int(total_transactions),
            "completed_24h": int(completed_24h),
            "failed_24h": int(failed_24h),
            "pending_24h": int(pending_24h),
            "volume_24h": float(volume_24h or 0),
            "status_breakdown": {
                "completed": int(status_completed),
                "pending": int(status_pending),
                "failed": int(status_failed)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_transactions": 0,
            "completed_24h": 0,
            "failed_24h": 0,
            "pending_24h": 0,
            "volume_24h": 0
        }


@admin_transactions_router.get("/disputes")
async def get_transaction_disputes(
    db_session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None)
):
    """Get all transaction disputes with optional status filter"""
    try:
        query = select(TransactionDispute)
        
        if status:
            query = query.where(TransactionDispute.dispute_status == status)
        
        query = query.order_by(TransactionDispute.filed_date.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        disputes = result.scalars().all()
        
        # Get total count for pagination
        count_query = select(func.count(TransactionDispute.id))
        if status:
            count_query = count_query.where(TransactionDispute.dispute_status == status)
        
        total = await db_session.scalar(count_query) or 0
        
        disputes_list = []
        for dispute in disputes:
            disputes_list.append({
                "id": dispute.id,
                "transaction_id": dispute.transaction_id,
                "user_id": dispute.user_id,
                "dispute_reason": dispute.dispute_reason,
                "dispute_amount": float(dispute.dispute_amount),
                "dispute_status": dispute.dispute_status,
                "filed_date": dispute.filed_date.isoformat() if dispute.filed_date else None,
                "resolved_date": dispute.resolved_date.isoformat() if dispute.resolved_date else None,
                "created_at": dispute.created_at.isoformat() if dispute.created_at else None
            })
        
        return {
            "success": True,
            "data": disputes_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "total": 0
        }


@admin_transactions_router.get("/returns")
async def get_transaction_returns(
    db_session: SessionDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    return_type: str = Query(None),
    status: str = Query(None)
):
    """Get all transaction returns with optional type and status filters"""
    try:
        query = select(ReturnProcessing)
        
        if return_type:
            query = query.where(ReturnProcessing.return_type == return_type)
        
        if status:
            query = query.where(ReturnProcessing.status == status)
        
        query = query.order_by(ReturnProcessing.received_date.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        returns = result.scalars().all()
        
        # Get total count for pagination
        count_query = select(func.count(ReturnProcessing.id))
        if return_type:
            count_query = count_query.where(ReturnProcessing.return_type == return_type)
        if status:
            count_query = count_query.where(ReturnProcessing.status == status)
        
        total = await db_session.scalar(count_query) or 0
        
        returns_list = []
        for return_item in returns:
            returns_list.append({
                "id": return_item.id,
                "return_type": return_item.return_type,
                "reference_id": return_item.reference_id,
                "status": return_item.status,
                "amount": float(return_item.amount),
                "return_code": return_item.return_code,
                "reason": return_item.reason,
                "received_date": return_item.received_date.isoformat() if return_item.received_date else None,
                "processed_date": return_item.processed_date.isoformat() if return_item.processed_date else None,
                "created_at": return_item.created_at.isoformat() if return_item.created_at else None
            })
        
        return {
            "success": True,
            "data": returns_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "total": 0
        }
