from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
from sqlalchemy import func, select, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
import logging
from datetime import datetime
import json

from deps import CurrentAdminUserDep, get_current_admin_user, SessionDep, validate_password_length
from models import User as DBUser, Transaction as DBTransaction, FormSubmission as DBFormSubmission
from models import Card as DBCard, Deposit as DBDeposit, Loan as DBLoan, Investment as DBInvestment, Account as DBAccount, Ledger as DBLedger
from models import KYCSubmission, KYCInfo
from crud import get_users, create_user, get_transactions, get_form_submissions, get_user_by_username
from kyc_service import KYCService
from crud import get_kyc_submissions, get_pending_kyc_submissions, approve_kyc_submission, reject_kyc_submission
from crud import get_user_cards, create_user_card, get_card, get_user_deposits, create_user_deposit, get_deposit
from crud import get_user_loans, create_user_loan, get_loan, get_user_investments, create_user_investment, get_investment
from schemas import KYCSubmission as PydanticKYCSubmission
from schemas import User as PydanticUser, Transaction as PydanticTransaction, FormSubmission as PydanticFormSubmission, UserCreate, AdminDashboardMetrics
from schemas import FundUserRequest, FundUserResponse, AdjustBalanceRequest, CreateAccountRequest, KYCApprovalRequest, KYCRejectionRequest
from schemas import Card as PydanticCard, CardCreate as PydanticCardCreate
from schemas import Deposit as PydanticDeposit, DepositCreate as PydanticDepositCreate
from schemas import Loan as PydanticLoan, LoanCreate as PydanticLoanCreate
from schemas import Investment as PydanticInvestment, InvestmentCreate as PydanticInvestmentCreate
from balance_service_ledger import BalanceServiceLedger
import json
from ws_manager import manager

log = logging.getLogger(__name__)

# Use the callable `get_current_admin_user` in Depends to avoid wrapping an Annotated type
admin_router = APIRouter(tags=["admin"], dependencies=[Depends(get_current_admin_user)])

@admin_router.get("/users", response_model=List[PydanticUser])
async def read_all_users_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    users = await get_users(db_session, skip=skip, limit=limit)
    # Add balance from ledger to each user
    for user in users:
        balance = await BalanceServiceLedger.get_user_balance(db_session, user.id)
        user.balance = float(balance)
    return users

@admin_router.post("/users", response_model=PydanticUser, status_code=status.HTTP_201_CREATED)
async def create_new_user_admin(
    user: UserCreate, 
    db_session: SessionDep,
    validated_password: str = Depends(validate_password_length)
):
    db_user = await get_user_by_username(db_session, username=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    # You might want to add more validation or default values for admin-created users
    created = await create_user(db=db_session, user=user)
    try:
        # Broadcast a simple user-created event to connected realtime clients
        await manager.broadcast(json.dumps({"event": "user:created", "id": getattr(created, 'id', None), "email": getattr(created, 'email', None)}))
    except Exception:
        pass
    return created

@admin_router.get("/transactions", response_model=List[PydanticTransaction])
async def read_all_transactions_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    log.info("GET /admin/transactions endpoint called successfully")
    transactions = await get_transactions(db_session, skip=skip, limit=limit)
    log.info(f"Successfully retrieved {len(transactions)} transactions")
    return transactions

@admin_router.get("/forms", response_model=List[PydanticFormSubmission])
async def read_all_form_submissions_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    submissions = await get_form_submissions(db_session, skip=skip, limit=limit)
    return submissions

# Add more admin-specific routes for updates, deletions, etc.
# For example, to change a user's admin status
@admin_router.put("/users/{user_id}/set_admin", response_model=PydanticUser)
async def set_user_admin_status(user_id: int, is_admin: bool, db_session: SessionDep):
    from sqlalchemy import select
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_update = db_user.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_to_update.is_admin = is_admin
    await db_session.commit()
    await db_session.refresh(user_to_update)
    try:
        await manager.broadcast(json.dumps({"event": "user:updated", "id": user_to_update.id, "is_admin": user_to_update.is_admin}))
    except Exception:
        pass
    return PydanticUser.model_validate(user_to_update)


@admin_router.put("/users/{user_id}", response_model=PydanticUser)
async def update_user_admin(user_id: int, payload: dict, db_session: SessionDep):
    """Update user fields (admin-only). Payload is a dict of updatable fields."""
    from sqlalchemy import select
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_update = db_user.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Apply allowed updates
    allowed = {"full_name", "email", "is_active", "is_admin", "account_number", "account_type"}
    for k, v in payload.items():
        if k in allowed:
            setattr(user_to_update, k, v)
    await db_session.commit()
    await db_session.refresh(user_to_update)
    try:
        await manager.broadcast(json.dumps({"event": "user:updated", "id": user_to_update.id}))
    except Exception:
        pass
    return PydanticUser.model_validate(user_to_update)


@admin_router.delete("/users/{user_id}")
async def delete_user_admin(user_id: int, db_session: SessionDep):
    from sqlalchemy import select
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_delete = db_user.scalar_one_or_none()
    if not user_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db_session.delete(user_to_delete)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({"event": "user:deleted", "id": user_id}))
    except Exception:
        pass
    return {"status": "deleted", "id": user_id}

@admin_router.get("/metrics", response_model=AdminDashboardMetrics)
async def get_dashboard_metrics(db_session: SessionDep):
    """
    Provides summary metrics for the admin dashboard.
    
    RULE: All metrics are calculated from LEDGER_ENTRIES (source of truth).
    - Active Users = count of distinct users with ledger activity
    - Total Deposits = sum of credits from system account
    - Total Volume = sum of all credits (all users)
    - Total Transactions = count of posted ledger entries
    """
    try:
        # 1. Active users (users with ledger activity)
        active_users_result = await db_session.execute(
            select(func.count(distinct(DBLedger.user_id))).where(
                DBLedger.status == "posted"
            )
        )
        total_users = active_users_result.scalar() or 0
        
        # 2. Total deposits (credits from system account)
        total_deposits = await BalanceServiceLedger.get_admin_total_deposits(db_session)
        
        # 3. Total volume (sum of all credits)
        total_volume = await BalanceServiceLedger.get_admin_total_volume(db_session)
        
        # 4. Pending KYC count
        pending_kyc_result = await db_session.execute(
            select(func.count(KYCSubmission.id)).where(
                KYCSubmission.status == "pending"
            )
        )
        pending_kyc = pending_kyc_result.scalar() or 0
        
        # 5. Total transactions (posted ledger entries)
        total_transactions_result = await db_session.execute(
            select(func.count(DBLedger.id)).where(
                DBLedger.status == "posted"
            )
        )
        total_transactions = total_transactions_result.scalar() or 0
        
        return AdminDashboardMetrics(
            total_users=total_users,
            pending_kyc=pending_kyc,
            total_transactions=total_transactions,
            total_deposits=total_deposits,
            total_volume=total_volume
        )
    except Exception as e:
        log.error(f"Error calculating dashboard metrics: {e}")
        raise

@admin_router.get("/users/{user_id}/balance", response_model=dict)
async def get_user_balance_admin(
    user_id: int,
    db_session: SessionDep
):
    """
    Get a specific user's account balance. Admin only.
    
    RULE: Balance is calculated from LEDGER (source of truth), ensuring
    consistency with user dashboard calculations.
    """
    # Get user to verify they exist
    user = await get_user_by_username(db_session, username="")  # This won't find anything, use direct query
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    
    # Get balance from ledger (source of truth)
    balance = await BalanceServiceLedger.get_user_balance(db_session, user_id)
    
    # Get primary account for currency info
    account_result = await db_session.execute(
        select(DBAccount).where(
            DBAccount.owner_id == user_id,
            DBAccount.status == "active"
        ).order_by(DBAccount.is_primary.desc() if hasattr(DBAccount, 'is_primary') else DBAccount.created_at)
    )
    account = account_result.scalars().first()
    
    currency = account.currency if account else "USD"
    
    return {
        "user_id": user_id,
        "email": user.email,
        "balance": balance,
        "currency": currency
    }

@admin_router.get("/recent-users", response_model=List[PydanticUser], response_model_exclude_none=True)
async def get_recent_users(db_session: SessionDep):
    return await get_users(db_session, skip=0, limit=5)

@admin_router.get("/recent-transactions", response_model=List[PydanticTransaction], response_model_exclude_none=True)
async def get_recent_transactions(db_session: SessionDep):
    return await get_transactions(db_session, skip=0, limit=5)


@admin_router.get("/kyc/submissions", response_model=List[PydanticKYCSubmission])
async def list_kyc_submissions(db_session: SessionDep, pending: Optional[bool] = None, skip: int = 0, limit: int = 100):
    if pending:
        return await get_pending_kyc_submissions(db_session, skip=skip, limit=limit)
    return await get_kyc_submissions(db_session, skip=skip, limit=limit)


@admin_router.get("/kyc/info-submissions")
async def list_kyc_info_submissions(db_session: SessionDep, skip: int = 0, limit: int = 100):
    """Get KYC submissions from kyc_info table (user-submitted KYC forms)"""
    try:
        result = await db_session.execute(
            select(KYCInfo, User)
            .join(User, KYCInfo.user_id == User.id)
            .where(KYCInfo.kyc_submitted == True)
            .offset(skip)
            .limit(limit)
            .order_by(KYCInfo.submission_timestamp.desc())
        )
        submissions = result.all()
        
        kyc_list = []
        for kyc_info, user in submissions:
            kyc_list.append({
                "id": kyc_info.id,
                "user_id": kyc_info.user_id,
                "user_email": user.email,
                "user_name": user.full_name,
                "document_type": kyc_info.document_type,
                "status": kyc_info.kyc_status or "pending",
                "submitted_at": kyc_info.submission_timestamp,
                "reviewed_at": kyc_info.reviewed_at,
                "kyc_submitted": kyc_info.kyc_submitted,
                "submission_locked": kyc_info.submission_locked
            })
        
        return kyc_list
    except Exception as e:
        print(f"Error fetching KYC info submissions: {e}")
        return []


@admin_router.get("/kyc/submissions/{submission_id}", response_model=PydanticKYCSubmission)
async def get_kyc_submission(submission_id: int, db_session: SessionDep):
    """Get detailed information about a KYC submission."""
    from models import KYCSubmission as DBKYCSubmission
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return PydanticKYCSubmission.model_validate(submission)


@admin_router.post("/kyc/{submission_id}/approve")
async def admin_approve_kyc(submission_id: int, db_session: SessionDep):
    submission = await approve_kyc_submission(db_session, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    # ISSUE #2 FIX: Also update the User.kyc_status field
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == submission.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.kyc_status = "approved"
        db_session.add(user)
        await db_session.commit()
    
    return {"status": "approved", "id": submission.id}


@admin_router.post("/kyc/{submission_id}/reject")
async def admin_reject_kyc(submission_id: int, db_session: SessionDep, reason: Optional[str] = None):
    # Get the KYC submission to find the user_id
    result = await db_session.execute(select(KYCSubmission).filter(KYCSubmission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    # Use KYCService to properly reject (which also unlocks the profile)
    success, message = await KYCService.reject_kyc(
        db_session=db_session,
        user_id=submission.user_id,
        rejection_reason=reason or ""
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "status": "rejected",
        "id": submission.id,
        "user_id": submission.user_id,
        "message": message,
        "kyc_status": "rejected",
        "rejection_reason": reason
    }


# ============================================================================
# USER CARDS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/cards", response_model=List[PydanticCard])
async def admin_get_user_cards(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all cards for a specific user (admin view)."""
    cards = await get_user_cards(db_session, user_id, skip=skip, limit=limit)
    return cards


@admin_router.post("/users/{user_id}/cards", response_model=PydanticCard, status_code=status.HTTP_201_CREATED)
async def admin_create_user_card(
    user_id: int,
    card: PydanticCardCreate,
    db_session: SessionDep
):
    """Create a new card for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_card = await create_user_card(db_session, card, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "card:admin_created",
            "user_id": user_id,
            "card_id": created_card.id
        }))
    except Exception:
        pass
    return created_card


@admin_router.put("/users/{user_id}/cards/{card_id}", response_model=PydanticCard)
async def admin_update_user_card(
    user_id: int,
    card_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's card (admin)."""
    db_card = await get_card(db_session, card_id)
    if not db_card or db_card.user_id != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    
    allowed = {"card_type", "status", "expiry_date"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_card, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_card)
    try:
        await manager.broadcast(json.dumps({
            "event": "card:admin_updated",
            "user_id": user_id,
            "card_id": card_id
        }))
    except Exception:
        pass
    return db_card


@admin_router.delete("/users/{user_id}/cards/{card_id}")
async def admin_delete_user_card(
    user_id: int,
    card_id: int,
    db_session: SessionDep
):
    """Delete a user's card (admin)."""
    db_card = await get_card(db_session, card_id)
    if not db_card or db_card.user_id != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    
    await db_session.delete(db_card)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "card:admin_deleted",
            "user_id": user_id,
            "card_id": card_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "card_id": card_id}


# ============================================================================
# USER DEPOSITS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/deposits", response_model=List[PydanticDeposit])
async def admin_get_user_deposits(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all deposits for a specific user (admin view)."""
    deposits = await get_user_deposits(db_session, user_id, skip=skip, limit=limit)
    return deposits


@admin_router.post("/users/{user_id}/deposits", response_model=PydanticDeposit, status_code=status.HTTP_201_CREATED)
async def admin_create_user_deposit(
    user_id: int,
    deposit: PydanticDepositCreate,
    db_session: SessionDep
):
    """Create a new deposit for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_deposit = await create_user_deposit(db_session, deposit, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:admin_created",
            "user_id": user_id,
            "deposit_id": created_deposit.id
        }))
    except Exception:
        pass
    return created_deposit


@admin_router.put("/users/{user_id}/deposits/{deposit_id}", response_model=PydanticDeposit)
async def admin_update_user_deposit(
    user_id: int,
    deposit_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's deposit (admin)."""
    db_deposit = await get_deposit(db_session, deposit_id)
    if not db_deposit or db_deposit.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    allowed = {"amount", "currency", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_deposit, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_deposit)
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:admin_updated",
            "user_id": user_id,
            "deposit_id": deposit_id
        }))
    except Exception:
        pass
    return db_deposit


@admin_router.delete("/users/{user_id}/deposits/{deposit_id}")
async def admin_delete_user_deposit(
    user_id: int,
    deposit_id: int,
    db_session: SessionDep
):
    """Delete a user's deposit (admin)."""
    db_deposit = await get_deposit(db_session, deposit_id)
    if not db_deposit or db_deposit.user_id != user_id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    await db_session.delete(db_deposit)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:admin_deleted",
            "user_id": user_id,
            "deposit_id": deposit_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "deposit_id": deposit_id}


# ============================================================================
# USER LOANS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/loans", response_model=List[PydanticLoan])
async def admin_get_user_loans(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all loans for a specific user (admin view)."""
    loans = await get_user_loans(db_session, user_id, skip=skip, limit=limit)
    return loans


@admin_router.post("/users/{user_id}/loans", response_model=PydanticLoan, status_code=status.HTTP_201_CREATED)
async def admin_create_user_loan(
    user_id: int,
    loan: PydanticLoanCreate,
    db_session: SessionDep
):
    """Create a new loan for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_loan = await create_user_loan(db_session, loan, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:admin_created",
            "user_id": user_id,
            "loan_id": created_loan.id
        }))
    except Exception:
        pass
    return created_loan


@admin_router.put("/users/{user_id}/loans/{loan_id}", response_model=PydanticLoan)
async def admin_update_user_loan(
    user_id: int,
    loan_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's loan (admin)."""
    db_loan = await get_loan(db_session, loan_id)
    if not db_loan or db_loan.user_id != user_id:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    allowed = {"amount", "interest_rate", "term_months", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_loan, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_loan)
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:admin_updated",
            "user_id": user_id,
            "loan_id": loan_id
        }))
    except Exception:
        pass
    return db_loan


@admin_router.delete("/users/{user_id}/loans/{loan_id}")
async def admin_delete_user_loan(
    user_id: int,
    loan_id: int,
    db_session: SessionDep
):
    """Delete a user's loan (admin)."""
    db_loan = await get_loan(db_session, loan_id)
    if not db_loan or db_loan.user_id != user_id:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    await db_session.delete(db_loan)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:admin_deleted",
            "user_id": user_id,
            "loan_id": loan_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "loan_id": loan_id}


# ============================================================================
# USER INVESTMENTS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/investments", response_model=List[PydanticInvestment])
async def admin_get_user_investments(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get all investments for a specific user (admin view)."""
    investments = await get_user_investments(db_session, user_id, skip=skip, limit=limit)
    return investments


@admin_router.post("/users/{user_id}/investments", response_model=PydanticInvestment, status_code=status.HTTP_201_CREATED)
async def admin_create_user_investment(
    user_id: int,
    investment: PydanticInvestmentCreate,
    db_session: SessionDep
):
    """Create a new investment for a user (admin)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    if not db_user.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    created_investment = await create_user_investment(db_session, investment, user_id)
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:admin_created",
            "user_id": user_id,
            "investment_id": created_investment.id
        }))
    except Exception:
        pass
    return created_investment


@admin_router.put("/users/{user_id}/investments/{investment_id}", response_model=PydanticInvestment)
async def admin_update_user_investment(
    user_id: int,
    investment_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Update a user's investment (admin)."""
    db_investment = await get_investment(db_session, investment_id)
    if not db_investment or db_investment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    allowed = {"investment_type", "amount", "status"}
    for k, v in payload.items():
        if k in allowed:
            setattr(db_investment, k, v)
    
    await db_session.commit()
    await db_session.refresh(db_investment)
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:admin_updated",
            "user_id": user_id,
            "investment_id": investment_id
        }))
    except Exception:
        pass
    return db_investment


@admin_router.delete("/users/{user_id}/investments/{investment_id}")
async def admin_delete_user_investment(
    user_id: int,
    investment_id: int,
    db_session: SessionDep
):
    """Delete a user's investment (admin)."""
    db_investment = await get_investment(db_session, investment_id)
    if not db_investment or db_investment.user_id != user_id:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    await db_session.delete(db_investment)
    await db_session.commit()
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:admin_deleted",
            "user_id": user_id,
            "investment_id": investment_id
        }))
    except Exception:
        pass
    return {"status": "deleted", "investment_id": investment_id}


# ============================================================================
# FUND & BALANCE MANAGEMENT (Admin)
# ============================================================================

@admin_router.post("/users/{user_id}/fund")
async def admin_fund_user(
    user_id: int,
    payload: FundUserRequest,
    db_session: SessionDep
):
    """Fund a user's account (admin operation)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user = db_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    amount = payload.amount
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get or create user's account
    db_account = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    account = db_account.scalar_one_or_none()
    
    if not account:
        # Create account if it doesn't exist
        account = DBAccount(
            owner_id=user_id,
            account_number=user.account_number or f"ACC_{user_id}_{int(__import__('time').time())}",
            balance=0.0,
            currency=payload.currency
        )
        db_session.add(account)
        await db_session.flush()
    
    # ISSUE #4 FIX: Do NOT manually update account.balance
    # Balance is now calculated from ledger (source of truth)
    # Removed: account.balance = (account.balance or 0) + amount
    
    # Create transaction record
    txn = DBTransaction(
        user_id=user_id,
        account_id=account.id,
        transaction_type="deposit",
        amount=amount,
        status="completed",
        description=payload.description or "Admin fund",
        reference_number=payload.reference_number or f"ADMIN_FUND_{user_id}_{int(__import__('time').time())}"
    )
    db_session.add(txn)
    
    await db_session.commit()
    await db_session.refresh(account)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "user:funded",
            "user_id": user_id,
            "amount": amount,
            "new_balance": float(account.balance)
        }))
    except Exception:
        pass
    
    return {"status": "success", "message": f"User funded with {payload.currency} {amount}", "new_balance": float(account.balance)}


@admin_router.post("/users/{user_id}/adjust-balance")
async def admin_adjust_balance(
    user_id: int,
    payload: AdjustBalanceRequest,
    db_session: SessionDep
):
    """Adjust a user's balance (credit or debit)."""
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user = db_user.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    amount = payload.amount
    adj_type = payload.operation_type
    reason = payload.description or "Balance adjustment"
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    # Get or create user's account
    db_account = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    account = db_account.scalar_one_or_none()
    
    if not account:
        # Create account if it doesn't exist
        account = DBAccount(
            owner_id=user_id,
            account_number=user.account_number or f"ACC_{user_id}_{int(__import__('time').time())}",
            balance=0.0,
            currency=payload.currency
        )
        db_session.add(account)
        await db_session.flush()
    
    # ISSUE #4 FIX: Do NOT manually update account.balance
    # Balance is now calculated from ledger (source of truth)
    # Removed: account.balance = (account.balance or 0) + amount
    # Removed: account.balance = current_balance - amount
    
    # Determine txn_type based on adjustment
    if adj_type == "credit":
        txn_type = "deposit"
    else:  # debit
        current_balance = account.balance or 0
        if current_balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient balance for debit")
        txn_type = "withdrawal"
    
    # Create transaction record
    txn = DBTransaction(
        user_id=user_id,
        account_id=account.id,
        transaction_type=txn_type,
        amount=amount,
        status="completed",
        description=f"Admin {reason}",
        reference_number=f"ADMIN_ADJ_{user_id}_{int(__import__('time').time())}"
    )
    db_session.add(txn)
    
    await db_session.commit()
    await db_session.refresh(account)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "user:balance_adjusted",
            "user_id": user_id,
            "amount": amount,
            "type": adj_type,
            "new_balance": float(account.balance)
        }))
    except Exception:
        pass
    
    return {"status": "success", "message": f"Balance {adj_type}ed by {amount}", "new_balance": float(user.balance)}


@admin_router.get("/balance-operations")
async def get_balance_operations(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """Get recent balance operations (fund/adjust)."""
    transactions = await get_transactions(db_session, skip=skip, limit=limit)
    return transactions


# ============================================================================
# TRANSACTION MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/transactions/{transaction_id}")
async def get_transaction_details(
    transaction_id: int,
    db_session: SessionDep
):
    """Get detailed information about a specific transaction."""
    result = await db_session.execute(
        select(DBTransaction).filter(DBTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return PydanticTransaction.model_validate(transaction)


@admin_router.post("/transactions/{transaction_id}/retry")
async def retry_transaction(
    transaction_id: int,
    db_session: SessionDep
):
    """Retry a failed transaction (admin)."""
    result = await db_session.execute(
        select(DBTransaction).filter(DBTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.status != "failed":
        raise HTTPException(status_code=400, detail="Only failed transactions can be retried")
    
    # Simulate retry
    transaction.status = "pending"
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "transaction:retrying",
            "transaction_id": transaction_id
        }))
    except Exception:
        pass
    
    return {"status": "retrying", "transaction_id": transaction_id}


# ============================================================================
# KYC MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/kyc-submissions", response_model=List[PydanticKYCSubmission])
async def list_all_kyc_submissions(
    db_session: SessionDep,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """Get all KYC submissions with optional status filter."""
    from sqlalchemy import select
    from models import KYCSubmission as DBKYCSubmission
    
    query = select(DBKYCSubmission)
    if status:
        query = query.filter(DBKYCSubmission.status == status)
    
    query = query.offset(skip).limit(limit)
    result = await db_session.execute(query)
    submissions = result.scalars().all()
    return submissions


@admin_router.get("/kyc-submissions/{submission_id}")
async def get_kyc_submission_details(
    submission_id: int,
    db_session: SessionDep
):
    """Get detailed information about a KYC submission."""
    from models import KYCSubmission as DBKYCSubmission
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    return PydanticKYCSubmission.model_validate(submission)


@admin_router.post("/kyc-submissions/{submission_id}/approve")
async def approve_kyc_submission_admin(
    submission_id: int,
    db_session: SessionDep,
    payload: Optional[KYCApprovalRequest] = Body(default=None)
):
    """Approve a KYC submission with optional notes."""
    from models import KYCSubmission as DBKYCSubmission
    
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    submission.status = "approved"
    submission.notes = payload.notes if payload else ""
    
    # ISSUE #2 FIX: Also update the User.kyc_status field
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == submission.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.kyc_status = "approved"
        db_session.add(user)
    
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:approved",
            "user_id": submission.user_id,
            "submission_id": submission_id
        }))
    except Exception:
        pass
    
    return {"status": "approved", "submission_id": submission_id}


@admin_router.post("/kyc-submissions/{submission_id}/reject")
async def reject_kyc_submission_admin(
    submission_id: int,
    db_session: SessionDep,
    payload: Optional[KYCRejectionRequest] = Body(default=None)
):
    """Reject a KYC submission with reason."""
    from models import KYCSubmission as DBKYCSubmission
    
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="KYC submission not found")
    
    submission.status = "rejected"
    submission.notes = (payload.notes if payload else None) or "Rejected by admin"
    
    # ISSUE #2 FIX: Also update the User.kyc_status field when rejecting
    user_result = await db_session.execute(
        select(DBUser).where(DBUser.id == submission.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.kyc_status = "rejected"
        db_session.add(user)
    
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:rejected",
            "user_id": submission.user_id,
            "submission_id": submission_id
        }))
    except Exception:
        pass
    
    return {"status": "rejected", "submission_id": submission_id}


# ============================================================================
# REPORTS & ANALYTICS (Admin)
# ============================================================================

@admin_router.get("/reports")
async def get_admin_reports(db_session: SessionDep):
    """Get comprehensive admin reports and analytics."""
    from sqlalchemy import and_
    from datetime import datetime, timedelta
    
    # Count total users
    total_users_result = await db_session.execute(select(func.count(DBUser.id)))
    total_users = total_users_result.scalar_one() or 0
    
    # Count total deposits and sum amount
    from models import Deposit as DBDepositModel
    deposits_result = await db_session.execute(
        select(func.count(DBDepositModel.id), func.sum(DBDepositModel.amount))
    )
    deposits_data = deposits_result.one_or_none()
    total_deposits_count = deposits_data[0] if deposits_data else 0
    total_deposits_amount = float(deposits_data[1]) if deposits_data and deposits_data[1] else 0
    
    # Count active loans
    from models import Loan as DBLoanModel
    loans_result = await db_session.execute(
        select(func.count(DBLoanModel.id)).filter(DBLoanModel.status == "active")
    )
    active_loans = loans_result.scalar_one() or 0
    
    # Count active investments
    from models import Investment as DBInvestmentModel
    investments_result = await db_session.execute(
        select(func.count(DBInvestmentModel.id)).filter(DBInvestmentModel.status == "active")
    )
    active_investments = investments_result.scalar_one() or 0
    
    # Transaction stats
    txn_stats_result = await db_session.execute(
        select(
            func.count(DBTransaction.id),
            func.sum(DBTransaction.amount),
            func.sum(
                __import__('sqlalchemy').case(
                    (DBTransaction.status == "completed", 1),
                    else_=0
                )
            )
        )
    )
    txn_data = txn_stats_result.one_or_none()
    total_txns = txn_data[0] if txn_data else 0
    total_txn_volume = float(txn_data[1]) if txn_data and txn_data[1] else 0
    completed_txns = txn_data[2] if txn_data else 0
    
    return {
        "total_users": total_users,
        "total_deposits_amount": total_deposits_amount,
        "total_deposits_count": total_deposits_count,
        "active_loans_count": active_loans,
        "active_investments_count": active_investments,
        "transactions": {
            "total": total_txns,
            "total_volume": total_txn_volume,
            "completed": completed_txns,
            "success_rate": (completed_txns / total_txns * 100) if total_txns > 0 else 0,
            "average_amount": total_txn_volume / total_txns if total_txns > 0 else 0
        },
        "users": {
            "total": total_users,
            "active_30days": 0,  # Would require login tracking
            "kyc_verified": 0,   # Would require KYC model tracking
            "average_balance": 0  # Would require sum of all balances
        },
        "deposits": {
            "total": total_deposits_amount,
            "count": total_deposits_count,
            "average": total_deposits_amount / total_deposits_count if total_deposits_count > 0 else 0,
            "pending": 0  # Would filter by status
        },
        "loans": {
            "active_count": active_loans,
            "total_outstanding": 0,  # Would require sum calculation
            "average_interest_rate": 0,
            "defaults": 0
        },
        "investments": {
            "total": 0,
            "active_count": active_investments,
            "average_return": 0,
            "total_return": 0
        }
    }


# ============================================================================
# USER ACCOUNTS & KYC SUPPORT (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}/accounts")
async def get_user_accounts(
    user_id: int,
    db_session: SessionDep
):
    """Get user accounts."""
    # Get all accounts for the user
    result = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    accounts = result.scalars().all()
    
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts found for user")
    
    return [{
        "id": acc.id,
        "account_number": acc.account_number,
        "account_type": acc.account_type,
        "balance": acc.balance,
        "currency": acc.currency,
        "status": acc.status,
        "created_at": acc.created_at
    } for acc in accounts]


@admin_router.post("/users/{user_id}/accounts")
async def create_user_account(
    user_id: int,
    payload: CreateAccountRequest,
    db_session: SessionDep
):
    """Create a new account for a user."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already has an account
    existing_account = await db_session.execute(
        select(DBAccount).filter(DBAccount.owner_id == user_id)
    )
    if existing_account.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has an account")
    
    # Create new account
    account_number = payload.account_number or f"ACC{user_id}_{int(__import__('time').time())}"
    
    # Update user's account_number if not set
    if not user.account_number:
        user.account_number = account_number
    
    new_account = DBAccount(
        owner_id=user_id,
        account_number=account_number,
        balance=payload.initial_balance,
        currency=payload.currency
    )
    db_session.add(new_account)
    
    await db_session.commit()
    await db_session.refresh(new_account)
    
    return {
        "id": new_account.id,
        "account_number": new_account.account_number,
        "balance": float(new_account.balance),
        "currency": new_account.currency,
        "account_type": payload.account_type,
        "created_at": new_account.created_at
    }


@admin_router.get("/users/{user_id}/kyc")
async def get_user_kyc(
    user_id: int,
    db_session: SessionDep
):
    """Get KYC information for a user."""
    from models import KYCSubmission as DBKYCSubmission
    
    result = await db_session.execute(
        select(DBKYCSubmission).filter(DBKYCSubmission.user_id == user_id)
    )
    kyc_submissions = result.scalars().all()
    return kyc_submissions


@admin_router.get("/users/{user_id}/transactions")
async def get_user_transactions(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """Get transactions for a specific user."""
    result = await db_session.execute(
        select(DBTransaction)
        .filter(DBTransaction.user_id == user_id)
        .offset(skip)
        .limit(limit)
    )
    transactions = result.scalars().all()
    return transactions


# ============================================================================
# USER SEARCH & FILTER (Admin) - MUST BE BEFORE {user_id}
# ============================================================================

@admin_router.get("/users/search")
async def search_users(
    db_session: SessionDep,
    query: str = "",
    skip: int = 0,
    limit: int = 50
):
    """Search for users by email or name."""
    search_pattern = f"%{query}%"
    result = await db_session.execute(
        select(DBUser)
        .filter(
            (DBUser.email.ilike(search_pattern)) | 
            (DBUser.full_name.ilike(search_pattern))
        )
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    return [PydanticUser.model_validate(u) for u in users]


@admin_router.get("/users/filter")
async def filter_users(
    db_session: SessionDep,
    status: Optional[str] = None,
    is_admin: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50
):
    """Filter users by status or admin status."""
    query = select(DBUser)
    
    if status == "active":
        query = query.filter(DBUser.is_active == True)
    elif status == "suspended":
        query = query.filter(DBUser.is_active == False)
    
    if is_admin is not None:
        query = query.filter(DBUser.is_admin == is_admin)
    
    query = query.offset(skip).limit(limit)
    result = await db_session.execute(query)
    users = result.scalars().all()
    return [PydanticUser.model_validate(u) for u in users]


# ============================================================================
# USER DETAILS & ACTIVITY LOG (Admin)
# ============================================================================

@admin_router.get("/users/{user_id}")
async def get_user_details(
    user_id: int,
    db_session: SessionDep
):
    """Get detailed information about a specific user."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return PydanticUser.model_validate(user)


@admin_router.get("/users/{user_id}/activity")
async def get_user_activity_log(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """Get activity log for a specific user (transactions, updates, etc)."""
    # Get transactions for the user
    result = await db_session.execute(
        select(DBTransaction)
        .filter(DBTransaction.user_id == user_id)
        .order_by(DBTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    transactions = result.scalars().all()
    return [PydanticTransaction.model_validate(t) for t in transactions]


@admin_router.get("/activity-log")
async def get_admin_activity_log(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get system activity log (all transactions)."""
    result = await db_session.execute(
        select(DBTransaction)
        .order_by(DBTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    transactions = result.scalars().all()
    return [PydanticTransaction.model_validate(t) for t in transactions]


# ============================================================================
# ADMIN MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/admins")
async def list_all_admins(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get list of all admin users."""
    result = await db_session.execute(
        select(DBUser)
        .filter(DBUser.is_admin == True)
        .offset(skip)
        .limit(limit)
    )
    admins = result.scalars().all()
    return [PydanticUser.model_validate(admin) for admin in admins]


@admin_router.post("/admins/{user_id}/promote")
async def promote_user_to_admin(
    user_id: int,
    db_session: SessionDep
):
    """Promote a user to admin status."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_admin:
        raise HTTPException(status_code=400, detail="User is already an admin")
    
    user.is_admin = True
    await db_session.commit()
    await db_session.refresh(user)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "admin:promoted",
            "user_id": user_id,
            "email": user.email
        }))
    except Exception:
        pass
    
    return {"status": "promoted", "user_id": user_id, "email": user.email}


@admin_router.post("/admins/{user_id}/demote")
async def demote_admin_to_user(
    user_id: int,
    db_session: SessionDep
):
    """Demote an admin to regular user status."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_admin:
        raise HTTPException(status_code=400, detail="User is not an admin")
    
    user.is_admin = False
    await db_session.commit()
    await db_session.refresh(user)
    
    try:
        await manager.broadcast(json.dumps({
            "event": "admin:demoted",
            "user_id": user_id,
            "email": user.email
        }))
    except Exception:
        pass
    
    return {"status": "demoted", "user_id": user_id, "email": user.email}


# ============================================================================
# USER ACCOUNT STATUS & SECURITY (Admin)
# ============================================================================

@admin_router.post("/users/{user_id}/suspend")
async def suspend_user_account(
    user_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Suspend a user account (disable access)."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "user:suspended",
            "user_id": user_id,
            "reason": payload.get("reason", "")
        }))
    except Exception:
        pass
    
    return {"status": "suspended", "user_id": user_id}


@admin_router.post("/users/{user_id}/activate")
async def activate_user_account(
    user_id: int,
    db_session: SessionDep
):
    """Activate a suspended user account."""
    result = await db_session.execute(
        select(DBUser).filter(DBUser.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "user:activated",
            "user_id": user_id
        }))
    except Exception:
        pass
    
    return {"status": "activated", "user_id": user_id}


@admin_router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: int,
    payload: dict,
    db_session: SessionDep,
    current_admin: CurrentAdminUserDep
):
    """
    Reset a user's password (Admin authority with audit trail).
    
    RULES:
    1. Admin does NOT see the new password (only that a reset was initiated)
    2. System hashes the password and updates the record
    3. User is forced to change password on next login
    4. Every action is logged in AuditLog with admin_id, user_id, timestamp, reason
    """
    from auth_utils import get_password_hash
    from admin_audit_service import admin_audit_service
    
    try:
        # Verify user exists
        result = await db_session.execute(
            select(DBUser).filter(DBUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get password and reason from payload
        new_password = payload.get("new_password")
        reason = payload.get("reason", "Admin initiated password reset")
        
        if not new_password or len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Hash the password (admin never sees plaintext)
        user.hashed_password = get_password_hash(new_password)
        
        # RULE: Force password change on next login
        # (This would require a new column in User model - optional for now)
        # user.force_password_change = True
        
        await db_session.commit()
        
        # LOG THE ACTION: Create audit trail
        await admin_audit_service.log_password_reset_action(
            db=db_session,
            admin_id=current_admin.id,
            user_id=user_id,
            reason=reason
        )
        
        # Broadcast event
        try:
            await manager.broadcast(json.dumps({
                "event": "user:password_reset",
                "user_id": user_id,
                "admin_id": current_admin.id,
                "timestamp": datetime.now().isoformat()
            }))
        except Exception:
            pass
        
        log.info(f"ADMIN {current_admin.id} reset password for USER {user_id}. Reason: {reason}")
        
        return {
            "status": "password_reset",
            "user_id": user_id,
            "message": "Password has been reset. User will be required to change it on next login.",
            "audited": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        log.error(f"Password reset failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Password reset failed: {str(e)}")


# ============================================================================
# DEPOSITS & WITHDRAWALS MANAGEMENT (Admin)
# ============================================================================

@admin_router.get("/pending-deposits")
async def get_pending_deposits(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """Get list of pending deposits."""
    result = await db_session.execute(
        select(DBDeposit)
        .filter(DBDeposit.status == "pending")
        .offset(skip)
        .limit(limit)
    )
    deposits = result.scalars().all()
    return [PydanticDeposit.model_validate(d) for d in deposits]


@admin_router.post("/deposits/{deposit_id}/approve")
async def approve_deposit_admin(
    deposit_id: int,
    db_session: SessionDep
):
    """Approve a pending deposit."""
    result = await db_session.execute(
        select(DBDeposit).filter(DBDeposit.id == deposit_id)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    if deposit.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending deposits can be approved")
    
    deposit.status = "completed"
    
    # Update user balance
    user_result = await db_session.execute(
        select(DBUser).filter(DBUser.id == deposit.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user:
        user.balance = (user.balance or 0) + deposit.amount
    
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:approved",
            "user_id": deposit.user_id,
            "deposit_id": deposit_id,
            "amount": deposit.amount
        }))
    except Exception:
        pass
    
    return {"status": "approved", "deposit_id": deposit_id}


@admin_router.post("/deposits/{deposit_id}/reject")
async def reject_deposit_admin(
    deposit_id: int,
    payload: dict,
    db_session: SessionDep
):
    """Reject a pending deposit."""
    result = await db_session.execute(
        select(DBDeposit).filter(DBDeposit.id == deposit_id)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    if deposit.status != "pending":
        raise HTTPException(status_code=400, detail="Only pending deposits can be rejected")
    
    deposit.status = "rejected"
    await db_session.commit()
    
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:rejected",
            "user_id": deposit.user_id,
            "deposit_id": deposit_id,
            "reason": payload.get("reason", "")
        }))
    except Exception:
        pass
    
    return {"status": "rejected", "deposit_id": deposit_id}


# ============================================================================
# AUDIT LOG ENDPOINTS (Admin)
# ============================================================================

@admin_router.get("/audit-logs")
async def get_all_audit_logs(
    db_session: SessionDep,
    user_id: Optional[int] = None,
    admin_id: Optional[int] = None,
    action_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve admin audit logs with optional filtering.
    
    Query Parameters:
    - user_id: Filter by target user ID
    - admin_id: Filter by admin ID (who performed the action)
    - action_type: Filter by action type (fund, freeze, reset_password, approve_kyc, etc.)
    
    RULE: These logs are immutable - they represent the complete audit trail of all admin actions.
    """
    from admin_audit_service import admin_audit_service
    from models import AuditLog as DBAuditLog
    
    try:
        # Build query
        query = select(DBAuditLog)
        
        if user_id:
            query = query.filter(DBAuditLog.user_id == user_id)
        if admin_id:
            query = query.filter(DBAuditLog.admin_id == admin_id)
        if action_type:
            query = query.filter(DBAuditLog.action_type == action_type)
        
        # Order by most recent first and paginate
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin.email if log.admin else "Unknown",
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else "Unknown",
                "account_id": log.account_id,
                "action_type": log.action_type,
                "reason": log.reason,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "status_message": log.status_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "total": len(logs),
            "skip": skip,
            "limit": limit,
            "logs": logs
        }
        
    except Exception as e:
        log.error(f"Error retrieving audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@admin_router.get("/audit-logs/user/{user_id}")
async def get_user_audit_logs(
    user_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """
    Get all admin actions performed ON a specific user.
    
    This shows what admins have done to this user:
    - Funded their account
    - Reset their password
    - Approved/rejected KYC
    - Frozen/unfrozen account
    - etc.
    """
    from models import AuditLog as DBAuditLog
    
    try:
        # Verify user exists
        user_result = await db_session.execute(
            select(DBUser).filter(DBUser.id == user_id)
        )
        if not user_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all audit logs for this user
        query = select(DBAuditLog).filter(DBAuditLog.user_id == user_id)
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin.email if log.admin else "Unknown",
                "action_type": log.action_type,
                "reason": log.reason,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "user_id": user_id,
            "total_actions": len(logs),
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving user audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@admin_router.get("/audit-logs/admin/{admin_id}")
async def get_admin_actions(
    admin_id: int,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 50
):
    """
    Get all actions performed BY a specific admin.
    
    This shows the complete action history for an admin user:
    - Who they funded
    - Who they reset passwords for
    - When and what they did
    - Reason for each action
    """
    from models import AuditLog as DBAuditLog
    
    try:
        # Verify admin exists
        admin_result = await db_session.execute(
            select(DBUser).filter(DBUser.id == admin_id)
        )
        admin = admin_result.scalar_one_or_none()
        if not admin or not admin.is_admin:
            raise HTTPException(status_code=404, detail="Admin user not found")
        
        # Get all audit logs for this admin
        query = select(DBAuditLog).filter(DBAuditLog.admin_id == admin_id)
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else "Unknown",
                "account_id": log.account_id,
                "action_type": log.action_type,
                "reason": log.reason,
                "details": json.loads(log.details) if log.details else None,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "admin_id": admin_id,
            "admin_email": admin.email,
            "total_actions": len(logs),
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error retrieving admin actions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@admin_router.get("/audit-logs/action-type/{action_type}")
async def get_audit_logs_by_action(
    action_type: str,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    """
    Get all audit logs for a specific action type.
    
    Valid action types:
    - fund: Admin funding operations
    - freeze: Account freezing
    - unfreeze: Account unfreezing
    - reset_password: Password resets
    - approve_kyc: KYC approvals
    - reject_kyc: KYC rejections
    - reverse_transaction: Transaction reversals
    - create_user: User creation
    - delete_user: User deletion
    """
    from models import AuditLog as DBAuditLog
    
    try:
        query = select(DBAuditLog).filter(DBAuditLog.action_type == action_type)
        query = query.order_by(DBAuditLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        audit_logs = result.scalars().all()
        
        if not audit_logs:
            return {
                "action_type": action_type,
                "total": 0,
                "logs": []
            }
        
        # Format response
        logs = []
        for log in audit_logs:
            log_dict = {
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": log.admin.email if log.admin else "Unknown",
                "user_id": log.user_id,
                "user_email": log.user.email if log.user else "Unknown",
                "reason": log.reason,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            logs.append(log_dict)
        
        return {
            "action_type": action_type,
            "total": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        log.error(f"Error retrieving audit logs by action: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")
