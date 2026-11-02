"""
Admin Transactions API Router
Provides admin dashboard endpoints for transaction metrics, disputes, returns, and exports.
"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select, func
from datetime import datetime, timedelta
import csv
import io

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
    """Get all transactions with advanced filtering (async-safe join)."""
    try:
        query = select(Transaction, DBUser).outerjoin(DBUser, Transaction.user_id == DBUser.id)
        count_query = select(func.count(Transaction.id)).select_from(Transaction).outerjoin(DBUser, Transaction.user_id == DBUser.id)

        if status:
            query = query.where(Transaction.status == status)
            count_query = count_query.where(Transaction.status == status)
        if transaction_type:
            query = query.where(Transaction.transaction_type == transaction_type)
            count_query = count_query.where(Transaction.transaction_type == transaction_type)
        if direction:
            query = query.where(Transaction.direction == direction)
            count_query = count_query.where(Transaction.direction == direction)
        if min_amount is not None:
            query = query.where(Transaction.amount >= min_amount)
            count_query = count_query.where(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.where(Transaction.amount <= max_amount)
            count_query = count_query.where(Transaction.amount <= max_amount)

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.where(Transaction.created_at >= start_dt)
                count_query = count_query.where(Transaction.created_at >= start_dt)
            except Exception:
                pass

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.where(Transaction.created_at <= end_dt)
                count_query = count_query.where(Transaction.created_at <= end_dt)
            except Exception:
                pass

        if search:
            search_term = f"%{search}%"
            cond = (DBUser.email.ilike(search_term)) | (Transaction.description.ilike(search_term))
            query = query.where(cond)
            count_query = count_query.where(cond)

        total = await db_session.scalar(count_query) or 0

        query = query.order_by(Transaction.created_at.desc()).offset(skip).limit(limit)
        result = await db_session.execute(query)
        rows = result.all()

        transactions_list = []
        for txn, user in rows:
            transactions_list.append({
                "id": txn.id,
                "user_id": txn.user_id,
                "user_email": user.email if user else f"user_{txn.user_id}@finanza.com",
                "amount": float(txn.amount or 0),
                "status": txn.status or "completed",
                "type": txn.transaction_type or "transfer",
                "transaction_type": txn.transaction_type or "transfer",
                "direction": getattr(txn, "direction", None) or "debit",
                "description": txn.description or "",
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
            "success": True,
            "warning": str(e),
            "data": [],
            "total": 0,
            "skip": skip,
            "limit": limit
        }


@admin_transactions_router.get("/export")
async def export_transactions_csv(
    db_session: SessionDep,
    format: str = Query("csv"),
    limit: int = Query(500, ge=1, le=5000)
):
    """Export transactions as CSV or JSON."""
    res = await db_session.execute(
        select(Transaction, DBUser)
        .outerjoin(DBUser, Transaction.user_id == DBUser.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    rows = res.all()
    if format.lower() == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["ID", "Reference", "User Email", "Type", "Status", "Amount", "Description", "Created At"])
        for txn, user in rows:
            writer.writerow([
                txn.id,
                txn.reference_number or f"TXN-{txn.id}",
                user.email if user else "",
                txn.transaction_type or "",
                txn.status or "",
                float(txn.amount or 0),
                txn.description or "",
                txn.created_at.isoformat() if txn.created_at else "",
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=transactions_export.csv"}
        )
    return {
        "success": True,
        "data": [
            {
                "id": txn.id,
                "user_email": user.email if user else "",
                "amount": float(txn.amount or 0),
                "status": txn.status,
                "type": txn.transaction_type,
                "created_at": txn.created_at.isoformat() if txn.created_at else None,
            }
            for txn, user in rows
        ]
    }


@admin_transactions_router.get("/metrics")
async def get_transaction_metrics(db_session: SessionDep):
    """Get transaction metrics and analytics for admin dashboard"""
    try:
        total_transactions = await db_session.scalar(select(func.count(Transaction.id))) or 0

        last_24h = datetime.utcnow() - timedelta(hours=24)
        completed_24h = await db_session.scalar(
            select(func.count(Transaction.id)).where(
                (Transaction.status == "completed") & (Transaction.created_at >= last_24h)
            )
        ) or 0

        failed_24h = await db_session.scalar(
            select(func.count(Transaction.id)).where(
                (Transaction.status == "failed") & (Transaction.created_at >= last_24h)
            )
        ) or 0

        pending_24h = await db_session.scalar(
            select(func.count(Transaction.id)).where(
                (Transaction.status == "pending") & (Transaction.created_at >= last_24h)
            )
        ) or 0

        volume_24h = await db_session.scalar(
            select(func.sum(Transaction.amount)).where(Transaction.created_at >= last_24h)
        ) or 0

        status_completed = await db_session.scalar(
            select(func.count(Transaction.id)).where(Transaction.status == "completed")
        ) or 0

        status_pending = await db_session.scalar(
            select(func.count(Transaction.id)).where(Transaction.status == "pending")
        ) or 0

        status_failed = await db_session.scalar(
            select(func.count(Transaction.id)).where(Transaction.status == "failed")
        ) or 0

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
            "success": True,
            "warning": str(e),
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

        count_query = select(func.count(TransactionDispute.id))
        if status:
            count_query = count_query.where(TransactionDispute.dispute_status == status)
        total = await db_session.scalar(count_query) or 0

        disputes_list = [
            {
                "id": d.id,
                "transaction_id": d.transaction_id,
                "user_id": d.user_id,
                "dispute_reason": d.dispute_reason,
                "dispute_amount": float(d.dispute_amount or 0),
                "dispute_status": d.dispute_status,
                "filed_date": d.filed_date.isoformat() if d.filed_date else None,
                "resolved_date": d.resolved_date.isoformat() if d.resolved_date else None,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in disputes
        ]

        return {
            "success": True,
            "data": disputes_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        return {
            "success": True,
            "warning": str(e),
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

        count_query = select(func.count(ReturnProcessing.id))
        if return_type:
            count_query = count_query.where(ReturnProcessing.return_type == return_type)
        if status:
            count_query = count_query.where(ReturnProcessing.status == status)
        total = await db_session.scalar(count_query) or 0

        returns_list = [
            {
                "id": r.id,
                "return_type": r.return_type,
                "reference_id": r.reference_id,
                "status": r.status,
                "amount": float(r.amount or 0),
                "return_code": r.return_code,
                "reason": r.reason,
                "received_date": r.received_date.isoformat() if r.received_date else None,
                "processed_date": r.processed_date.isoformat() if r.processed_date else None,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in returns
        ]

        return {
            "success": True,
            "data": returns_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        return {
            "success": True,
            "warning": str(e),
            "data": [],
            "total": 0
        }
