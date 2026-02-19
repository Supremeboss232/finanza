"""Business Analysis API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from deps import SessionDep, CurrentUserDep, get_current_user
from models import Transaction, User, Account
from schemas import UserCreate

router = APIRouter(prefix="/api/user/analysis", tags=["analysis"])


@router.get("/business/metrics")
async def get_business_metrics(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    days: int = 30
):
    """Get business analysis metrics for the current user."""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get total income (deposits/transfers in)
        income_query = select(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type.in_(["deposit", "transfer_in", "income"]),
            Transaction.created_at >= start_date
        )
        income_result = await db_session.execute(income_query)
        total_income = income_result.scalar() or 0
        
        # Get total expenses (withdrawals/transfers out)
        expense_query = select(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type.in_(["withdrawal", "transfer_out", "expense"]),
            Transaction.created_at >= start_date
        )
        expense_result = await db_session.execute(expense_query)
        total_expenses = expense_result.scalar() or 0
        
        # Get transaction count
        tx_count_query = select(func.count(Transaction.id)).filter(
            Transaction.user_id == current_user.id,
            Transaction.created_at >= start_date
        )
        tx_count_result = await db_session.execute(tx_count_query)
        transaction_count = tx_count_result.scalar() or 0
        
        # Get account balance
        account_balance_query = select(func.sum(Account.balance)).filter(
            Account.owner_id == current_user.id
        )
        balance_result = await db_session.execute(account_balance_query)
        total_balance = balance_result.scalar() or 0
        
        # Calculate net income
        net_income = total_income - total_expenses
        
        # Calculate average transaction
        avg_transaction = (total_income + total_expenses) / transaction_count if transaction_count > 0 else 0
        
        return {
            "period_days": days,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "net_income": float(net_income),
            "transaction_count": transaction_count,
            "average_transaction": float(avg_transaction),
            "total_balance": float(total_balance),
            "expense_ratio": (total_expenses / total_income * 100) if total_income > 0 else 0,
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating metrics: {str(e)}")


@router.get("/business/trends")
async def get_business_trends(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    months: int = 6
):
    """Get business trends over time."""
    try:
        trends = []
        end_date = datetime.utcnow()
        
        for i in range(months):
            month_start = (end_date - timedelta(days=30 * (i + 1))).replace(day=1)
            month_end = (end_date - timedelta(days=30 * i)).replace(day=1) - timedelta(days=1)
            
            # Income for month
            income_query = select(func.sum(Transaction.amount)).filter(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type.in_(["deposit", "transfer_in", "income"]),
                Transaction.created_at.between(month_start, month_end)
            )
            income_result = await db_session.execute(income_query)
            income = income_result.scalar() or 0
            
            # Expenses for month
            expense_query = select(func.sum(Transaction.amount)).filter(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type.in_(["withdrawal", "transfer_out", "expense"]),
                Transaction.created_at.between(month_start, month_end)
            )
            expense_result = await db_session.execute(expense_query)
            expenses = expense_result.scalar() or 0
            
            trends.append({
                "month": month_start.strftime("%B %Y"),
                "income": float(income),
                "expenses": float(expenses),
                "net": float(income - expenses)
            })
        
        return {"trends": trends[::-1]}  # Return in chronological order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trends: {str(e)}")


@router.get("/business/summary")
async def get_business_summary(
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    """Get overall business summary."""
    try:
        # Total transactions
        tx_count_query = select(func.count(Transaction.id)).filter(
            Transaction.user_id == current_user.id
        )
        tx_count_result = await db_session.execute(tx_count_query)
        total_transactions = tx_count_result.scalar() or 0
        
        # All-time income
        all_income_query = select(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type.in_(["deposit", "transfer_in", "income"])
        )
        all_income_result = await db_session.execute(all_income_query)
        lifetime_income = all_income_result.scalar() or 0
        
        # All-time expenses
        all_expense_query = select(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type.in_(["withdrawal", "transfer_out", "expense"])
        )
        all_expense_result = await db_session.execute(all_expense_query)
        lifetime_expenses = all_expense_result.scalar() or 0
        
        # Current balance
        balance_query = select(func.sum(Account.balance)).filter(
            Account.owner_id == current_user.id
        )
        balance_result = await db_session.execute(balance_query)
        current_balance = balance_result.scalar() or 0
        
        return {
            "lifetime_income": float(lifetime_income),
            "lifetime_expenses": float(lifetime_expenses),
            "lifetime_net": float(lifetime_income - lifetime_expenses),
            "total_transactions": total_transactions,
            "current_balance": float(current_balance),
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")
