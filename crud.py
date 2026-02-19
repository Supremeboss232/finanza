# crud.py
# Contains database operations (Create, Read, Update, Delete) for all models.

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from typing import Optional

import models, schemas
from auth_utils import get_password_hash, verify_password
import secrets
from datetime import datetime
import json
from ws_manager import manager

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.User).filter(models.User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str, options: list = None):
    query = select(models.User).filter(models.User.email == email)
    if options:
        query = query.options(*options)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def get_user_by_account_number(db: AsyncSession, account_number: str):
    result = await db.execute(select(models.User).filter(models.User.account_number == account_number))
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str):
    # Assuming username is the email for login purposes
    result = await db.execute(select(models.User).filter(models.User.email == username))
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user(db: AsyncSession, user: schemas.UserCreate, *, is_active: bool = False, is_verified: bool = False, account_number: Optional[str] = None):
    """Create a new user. By default new users are inactive and unverified.
    Admin callers may pass is_active=True and/or is_verified=True.
    
    CRITICAL: Creates primary account immediately on user registration.
    This enforces the non-negotiable rule: Every user MUST have a primary account.
    """
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        account_number=account_number,
        is_active=is_active,
        is_verified=is_verified,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    # ============================================================================
    # CREATE PRIMARY ACCOUNT IMMEDIATELY
    # ============================================================================
    # Rule 1: Every user must have a primary account on registration
    # Rule 2: Balance MUST default to 0.0, NEVER NULL
    # Rule 3: Account status MUST be ACTIVE
    # ============================================================================
    from datetime import datetime
    primary_account = models.Account(
        owner_id=db_user.id,
        account_number=account_number or _generate_account_number(),
        account_type="checking",  # Primary account type
        balance=0.0,  # Balance MUST be 0.0, NEVER NULL
        currency="USD",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(primary_account)
    await db.commit()
    await db.refresh(primary_account)
    # Broadcast user creation
    try:
        await manager.broadcast(json.dumps({
            "event": "user:created",
            "id": db_user.id,
            "email": db_user.email,
            "full_name": db_user.full_name,
            "is_active": db_user.is_active,
            "is_verified": db_user.is_verified,
            "account_number": db_user.account_number
        }))
    except Exception:
        pass
    return db_user

async def update_user(db: AsyncSession, user_id: int, user: schemas.UserUpdate):
    db_user = await get_user(db, user_id)
    if db_user:
        for var, value in vars(user).items():
            if value is not None:
                setattr(db_user, var, value)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
    # Broadcast user update
    try:
        if db_user:
            await manager.broadcast(json.dumps({
                "event": "user:updated",
                "id": db_user.id,
                "email": db_user.email,
                "full_name": db_user.full_name,
                "is_active": db_user.is_active,
                "is_verified": db_user.is_verified,
                "account_number": db_user.account_number
            }))
    except Exception:
        pass
    return db_user

async def delete_user(db: AsyncSession, user_id: int):
    db_user = await get_user(db, user_id)
    if db_user:
        await db.delete(db_user)
        await db.commit()
    # Broadcast user deletion
    try:
        if db_user:
            await manager.broadcast(json.dumps({
                "event": "user:deleted",
                "id": db_user.id,
                "email": db_user.email
            }))
    except Exception:
        pass
    return db_user

# Generic CRUD for other models

async def get_transactions(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Get transactions, handling missing columns gracefully"""
    try:
        # Try to get transactions with all columns
        result = await db.execute(select(models.Transaction).offset(skip).limit(limit))
        return result.scalars().all()
    except Exception as e:
        # Rollback the failed transaction to clear the error state
        await db.rollback()
        
        # Query only the core columns that should always exist
        try:
            from sqlalchemy import text
            # Get raw rows with only essential columns
            result = await db.execute(text("""
                SELECT id, user_id, account_id, amount, transaction_type, status, 
                       created_at, updated_at
                FROM transactions
                LIMIT :limit OFFSET :offset
            """), {"limit": limit, "offset": skip})
            rows = result.all()
            transactions = []
            for row in rows:
                t = models.Transaction()
                t.id = row[0]
                t.user_id = row[1]
                t.account_id = row[2]
                t.amount = row[3]
                t.transaction_type = row[4]
                t.status = row[5]
                t.created_at = row[6]
                t.updated_at = row[7]
                t.description = None
                t.reference_number = None
                transactions.append(t)
            return transactions
        except Exception as fallback_error:
            # Rollback again and return empty list
            await db.rollback()
            import logging
            logging.error(f"Error getting transactions: {fallback_error}")
            return []

async def get_user_transactions(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    """Get transactions for a specific user, handling missing columns gracefully"""
    try:
        # Try to get transactions with all columns
        result = await db.execute(select(models.Transaction).filter(models.Transaction.user_id == user_id).offset(skip).limit(limit))
        return result.scalars().all()
    except Exception as e:
        # Rollback the failed transaction to clear the error state
        await db.rollback()
        
        # Query only the core columns that should always exist
        try:
            from sqlalchemy import text
            # Get raw rows with only essential columns
            result = await db.execute(text("""
                SELECT id, user_id, account_id, amount, transaction_type, status, 
                       created_at, updated_at
                FROM transactions
                WHERE user_id = :user_id
                LIMIT :limit OFFSET :offset
            """), {"user_id": user_id, "limit": limit, "offset": skip})
            rows = result.all()
            transactions = []
            for row in rows:
                t = models.Transaction()
                t.id = row[0]
                t.user_id = row[1]
                t.account_id = row[2]
                t.amount = row[3]
                t.transaction_type = row[4]
                t.status = row[5]
                t.created_at = row[6]
                t.updated_at = row[7]
                t.description = None
                t.reference_number = None
                transactions.append(t)
            return transactions
        except Exception as fallback_error:
            # Rollback again and return empty list
            await db.rollback()
            import logging
            logging.error(f"Error getting user transactions: {fallback_error}")
            return []

async def create_user_transaction(db: AsyncSession, transaction: schemas.TransactionCreate, user_id: int, account_id: int = None):
    # Unpack transaction data - schema already contains user_id and account_id
    tx_data = transaction.model_dump()
    # Override with provided values if different (for explicit control)
    tx_data['user_id'] = user_id
    tx_data['account_id'] = account_id or tx_data.get('account_id')
    db_transaction = models.Transaction(**tx_data)
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    # Broadcast the new transaction to realtime clients
    try:
        await manager.broadcast(json.dumps({
            "event": "transaction:created",
            "id": db_transaction.id,
            "user_id": db_transaction.user_id,
            "amount": db_transaction.amount,
            "transaction_type": db_transaction.transaction_type,
            "status": db_transaction.status,
            "created_at": db_transaction.created_at.isoformat() if db_transaction.created_at else None
        }))
    except Exception:
        pass
    return db_transaction

async def get_transaction(db: AsyncSession, transaction_id: int):
    result = await db.execute(select(models.Transaction).filter(models.Transaction.id == transaction_id))
    return result.scalar_one_or_none()

async def get_form_submissions(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.FormSubmission).offset(skip).limit(limit))
    return result.scalars().all()

async def create_form_submission(db: AsyncSession, submission: schemas.FormSubmissionCreate, user_id: Optional[int] = None):
    db_submission = models.FormSubmission(**submission.model_dump(), user_id=user_id)
    db.add(db_submission)
    await db.commit()
    await db.refresh(db_submission)
    # Broadcast generic form submission (best-effort)
    try:
        await manager.broadcast(json.dumps({
            "event": "form:submitted",
            "id": db_submission.id,
            "user_id": db_submission.user_id,
            "form_type": db_submission.form_type,
            "submitted_at": db_submission.submitted_at.isoformat() if db_submission.submitted_at else None
        }))
    except Exception:
        pass
    return db_submission


async def create_kyc_submission(db: AsyncSession, user_id: int, document_type: str, document_file_path: str):
    db_submission = models.KYCSubmission(user_id=user_id, document_type=document_type, document_file_path=document_file_path)
    db.add(db_submission)
    await db.commit()
    await db.refresh(db_submission)
    # Broadcast KYC submission event
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:submitted",
            "submission_id": db_submission.id,
            "user_id": db_submission.user_id,
            "document_type": db_submission.document_type,
            "submitted_at": db_submission.submitted_at.isoformat() if db_submission.submitted_at else None
        }))
    except Exception:
        pass
    return db_submission


async def get_kyc_submissions(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.KYCSubmission).offset(skip).limit(limit))
    return result.scalars().all()


async def get_pending_kyc_submissions(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.KYCSubmission).filter(models.KYCSubmission.status == "pending").offset(skip).limit(limit))
    return result.scalars().all()


def _generate_account_number() -> str:
    # Example: AC-<6 random hex>-<timestamp>
    rand = secrets.token_hex(3).upper()
    ts = datetime.utcnow().strftime("%y%m%d%H%M%S")
    return f"AC-{rand}-{ts}"


async def approve_kyc_submission(db: AsyncSession, submission_id: int, approver_id: Optional[int] = None):
    result = await db.execute(select(models.KYCSubmission).filter(models.KYCSubmission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        return None
    # update submission
    submission.status = "approved"
    submission.reviewed_at = datetime.utcnow()

    # update user
    user = await get_user(db, submission.user_id)
    if user:
        user.is_verified = True
        user.is_active = True
        user.kyc_status = "approved"  # Update KYC status to approved
        if not user.account_number:
            user.account_number = _generate_account_number()
        db.add(user)

    # Also update the KYCInfo record if it exists
    kyc_info_result = await db.execute(
        select(models.KYCInfo).filter(models.KYCInfo.user_id == submission.user_id)
    )
    kyc_info = kyc_info_result.scalars().first()
    if kyc_info:
        kyc_info.kyc_status = "approved"
        kyc_info.reviewed_at = datetime.utcnow()
        db.add(kyc_info)

    db.add(submission)
    await db.commit()
    if user:
        await db.refresh(user)
    await db.refresh(submission)
    # Broadcast KYC approval event
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:approved",
            "submission_id": submission.id,
            "user_id": submission.user_id,
            "approved_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
            "account_number": getattr(user, 'account_number', None)
        }))
    except Exception:
        pass
    return submission


async def reject_kyc_submission(db: AsyncSession, submission_id: int, reason: Optional[str] = None):
    result = await db.execute(select(models.KYCSubmission).filter(models.KYCSubmission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        return None
    submission.status = "rejected"
    submission.reviewed_at = datetime.utcnow()
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    # Broadcast KYC rejection event
    try:
        await manager.broadcast(json.dumps({
            "event": "kyc:rejected",
            "submission_id": submission.id,
            "user_id": submission.user_id,
            "rejected_at": submission.reviewed_at.isoformat() if submission.reviewed_at else None,
            "reason": reason
        }))
    except Exception:
        pass
    return submission

async def get_form_submission(db: AsyncSession, submission_id: int):
    result = await db.execute(select(models.FormSubmission).filter(models.FormSubmission.id == submission_id))
    return result.scalar_one_or_none()

# Placeholder CRUD for other routers to prevent import errors

async def get_user_deposits(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Deposit).filter(models.Deposit.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_deposit(db: AsyncSession, deposit: schemas.DepositCreate, user_id: int):
    deposit_data = deposit.model_dump()
    # Set current_balance to amount if not provided
    if deposit_data.get('current_balance') is None:
        deposit_data['current_balance'] = deposit_data.get('amount', 0.0)
    db_deposit = models.Deposit(**deposit_data, user_id=user_id)
    db.add(db_deposit)
    await db.commit()
    await db.refresh(db_deposit)
    # Broadcast deposit creation
    try:
        await manager.broadcast(json.dumps({
            "event": "deposit:created",
            "id": db_deposit.id,
            "user_id": db_deposit.user_id,
            "amount": db_deposit.amount,
            "current_balance": db_deposit.current_balance,
            "currency": db_deposit.currency,
            "status": db_deposit.status,
            "created_at": db_deposit.created_at.isoformat() if db_deposit.created_at else None
        }))
    except Exception:
        pass
    return db_deposit

async def get_deposit(db: AsyncSession, deposit_id: int):
    result = await db.execute(select(models.Deposit).filter(models.Deposit.id == deposit_id))
    return result.scalar_one_or_none()

async def get_user_loans(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Loan).filter(models.Loan.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_loan(db: AsyncSession, loan: schemas.LoanCreate, user_id: int):
    loan_data = loan.model_dump()
    # Set remaining_balance to amount if not provided
    if loan_data.get('remaining_balance') is None:
        loan_data['remaining_balance'] = loan_data.get('amount', 0.0)
    # Calculate monthly payment if not provided
    if loan_data.get('monthly_payment') is None or loan_data['monthly_payment'] == 0:
        amount = loan_data.get('amount', 0.0)
        rate = loan_data.get('interest_rate', 0.0) / 100 / 12  # Monthly rate
        months = loan_data.get('term_months', 12)
        if rate > 0 and months > 0:
            # PMT formula: P * [r(1+r)^n] / [(1+r)^n - 1]
            loan_data['monthly_payment'] = amount * (rate * (1 + rate)**months) / ((1 + rate)**months - 1)
        elif months > 0:
            loan_data['monthly_payment'] = amount / months
    db_loan = models.Loan(**loan_data, user_id=user_id)
    db.add(db_loan)
    await db.commit()
    await db.refresh(db_loan)
    # Broadcast loan creation
    try:
        await manager.broadcast(json.dumps({
            "event": "loan:created",
            "id": db_loan.id,
            "user_id": db_loan.user_id,
            "amount": db_loan.amount,
            "remaining_balance": db_loan.remaining_balance,
            "monthly_payment": db_loan.monthly_payment,
            "interest_rate": db_loan.interest_rate,
            "term_months": db_loan.term_months,
            "status": db_loan.status,
            "created_at": db_loan.created_at.isoformat() if db_loan.created_at else None
        }))
    except Exception:
        pass
    return db_loan

async def get_loan(db: AsyncSession, loan_id: int):
    result = await db.execute(select(models.Loan).filter(models.Loan.id == loan_id))
    return result.scalar_one_or_none()

async def get_user_investments(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Investment).filter(models.Investment.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_investment(db: AsyncSession, investment: schemas.InvestmentCreate, user_id: int):
    inv_data = investment.model_dump()
    # Set current_value to amount if not provided
    if inv_data.get('current_value') is None:
        inv_data['current_value'] = inv_data.get('amount', 0.0)
    db_investment = models.Investment(**inv_data, user_id=user_id)
    db.add(db_investment)
    await db.commit()
    await db.refresh(db_investment)
    # Broadcast investment creation
    try:
        await manager.broadcast(json.dumps({
            "event": "investment:created",
            "id": db_investment.id,
            "user_id": db_investment.user_id,
            "investment_type": db_investment.investment_type,
            "amount": db_investment.amount,
            "current_value": db_investment.current_value,
            "annual_return_rate": db_investment.annual_return_rate,
            "status": db_investment.status,
            "created_at": db_investment.created_at.isoformat() if db_investment.created_at else None
        }))
    except Exception:
        pass
    return db_investment

async def get_investment(db: AsyncSession, investment_id: int):
    result = await db.execute(select(models.Investment).filter(models.Investment.id == investment_id))
    return result.scalar_one_or_none()

async def get_user_cards(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Card).filter(models.Card.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user_card(db: AsyncSession, card: schemas.CardCreate, user_id: int):
    db_card = models.Card(**card.model_dump(), user_id=user_id)
    db.add(db_card)
    await db.commit()
    await db.refresh(db_card)
    # Broadcast card creation
    try:
        await manager.broadcast(json.dumps({
            "event": "card:created",
            "id": db_card.id,
            "user_id": db_card.user_id,
            "card_number": db_card.card_number,
            "card_type": db_card.card_type,
            "expiry_date": db_card.expiry_date,
            "status": db_card.status,
            "created_at": db_card.created_at.isoformat() if db_card.created_at else None
        }))
    except Exception:
        pass
    return db_card

async def get_card(db: AsyncSession, card_id: int):
    result = await db.execute(select(models.Card).filter(models.Card.id == card_id))
    return result.scalar_one_or_none()

# ===== POLICIES & CLAIMS =====

async def create_policy(db: AsyncSession, policy: schemas.PolicyCreate, user_id: int):
    db_policy = models.Policy(**policy.model_dump(), user_id=user_id)
    db.add(db_policy)
    await db.commit()
    await db.refresh(db_policy)
    return db_policy

async def get_user_policies(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Policy).filter(models.Policy.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def get_policy(db: AsyncSession, policy_id: int):
    result = await db.execute(select(models.Policy).filter(models.Policy.id == policy_id))
    return result.scalar_one_or_none()

async def update_policy(db: AsyncSession, policy_id: int, policy_data: dict):
    db_policy = await get_policy(db, policy_id)
    if db_policy:
        for key, value in policy_data.items():
            if value is not None:
                setattr(db_policy, key, value)
        db.add(db_policy)
        await db.commit()
        await db.refresh(db_policy)
    return db_policy

async def delete_policy(db: AsyncSession, policy_id: int):
    db_policy = await get_policy(db, policy_id)
    if db_policy:
        await db.delete(db_policy)
        await db.commit()
    return db_policy

async def create_claim(db: AsyncSession, claim: schemas.ClaimCreate, policy_id: int):
    db_claim = models.Claim(**claim.model_dump(), policy_id=policy_id)
    db.add(db_claim)
    await db.commit()
    await db.refresh(db_claim)
    return db_claim

async def get_policy_claims(db: AsyncSession, policy_id: int):
    result = await db.execute(select(models.Claim).filter(models.Claim.policy_id == policy_id))
    return result.scalars().all()

async def get_claim(db: AsyncSession, claim_id: int):
    result = await db.execute(select(models.Claim).filter(models.Claim.id == claim_id))
    return result.scalar_one_or_none()

async def update_claim(db: AsyncSession, claim_id: int, claim_data: dict):
    db_claim = await get_claim(db, claim_id)
    if db_claim:
        for key, value in claim_data.items():
            if value is not None:
                setattr(db_claim, key, value)
        db.add(db_claim)
        await db.commit()
        await db.refresh(db_claim)
    return db_claim

# ===== BUDGETS & GOALS =====

async def create_budget(db: AsyncSession, budget: schemas.BudgetCreate, user_id: int):
    db_budget = models.Budget(**budget.model_dump(), user_id=user_id)
    db.add(db_budget)
    await db.commit()
    await db.refresh(db_budget)
    return db_budget

async def get_user_budgets(db: AsyncSession, user_id: int, month: str = None):
    query = select(models.Budget).filter(models.Budget.user_id == user_id)
    if month:
        query = query.filter(models.Budget.month == month)
    result = await db.execute(query)
    return result.scalars().all()

async def get_budget(db: AsyncSession, budget_id: int):
    result = await db.execute(select(models.Budget).filter(models.Budget.id == budget_id))
    return result.scalar_one_or_none()

async def update_budget(db: AsyncSession, budget_id: int, budget_data: dict):
    db_budget = await get_budget(db, budget_id)
    if db_budget:
        for key, value in budget_data.items():
            if value is not None:
                setattr(db_budget, key, value)
        db.add(db_budget)
        await db.commit()
        await db.refresh(db_budget)
    return db_budget

async def delete_budget(db: AsyncSession, budget_id: int):
    db_budget = await get_budget(db, budget_id)
    if db_budget:
        await db.delete(db_budget)
        await db.commit()
    return db_budget

async def create_goal(db: AsyncSession, goal: schemas.GoalCreate, user_id: int):
    db_goal = models.Goal(**goal.model_dump(), user_id=user_id)
    db.add(db_goal)
    await db.commit()
    await db.refresh(db_goal)
    return db_goal

async def get_user_goals(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Goal).filter(models.Goal.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def get_goal(db: AsyncSession, goal_id: int):
    result = await db.execute(select(models.Goal).filter(models.Goal.id == goal_id))
    return result.scalar_one_or_none()

async def update_goal(db: AsyncSession, goal_id: int, goal_data: dict):
    db_goal = await get_goal(db, goal_id)
    if db_goal:
        for key, value in goal_data.items():
            if value is not None:
                setattr(db_goal, key, value)
        db.add(db_goal)
        await db.commit()
        await db.refresh(db_goal)
    return db_goal

async def delete_goal(db: AsyncSession, goal_id: int):
    db_goal = await get_goal(db, goal_id)
    if db_goal:
        await db.delete(db_goal)
        await db.commit()
    return db_goal

# ===== NOTIFICATIONS =====

async def create_notification(db: AsyncSession, notification: schemas.NotificationCreate, user_id: int):
    db_notification = models.Notification(**notification.model_dump(), user_id=user_id)
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return db_notification

async def get_user_notifications(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50):
    result = await db.execute(select(models.Notification).filter(models.Notification.user_id == user_id).order_by(models.Notification.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()

async def get_unread_notifications_count(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Notification).filter(models.Notification.user_id == user_id, models.Notification.is_read == False))
    return len(result.scalars().all())

async def get_notification(db: AsyncSession, notification_id: int):
    result = await db.execute(select(models.Notification).filter(models.Notification.id == notification_id))
    return result.scalar_one_or_none()

async def mark_notification_as_read(db: AsyncSession, notification_id: int):
    db_notification = await get_notification(db, notification_id)
    if db_notification:
        db_notification.is_read = True
        db.add(db_notification)
        await db.commit()
        await db.refresh(db_notification)
    return db_notification

async def mark_all_notifications_as_read(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.Notification).filter(models.Notification.user_id == user_id, models.Notification.is_read == False))
    notifications = result.scalars().all()
    for notification in notifications:
        notification.is_read = True
    await db.commit()
    return notifications

async def delete_notification(db: AsyncSession, notification_id: int):
    db_notification = await get_notification(db, notification_id)
    if db_notification:
        await db.delete(db_notification)
        await db.commit()
    return db_notification

# ===== SUPPORT TICKETS =====

async def create_support_ticket(db: AsyncSession, ticket: schemas.SupportTicketCreate, user_id: int = None):
    ticket_number = f"TKT-{secrets.token_hex(4).upper()}"
    db_ticket = models.SupportTicket(**ticket.model_dump(), user_id=user_id, ticket_number=ticket_number)
    db.add(db_ticket)
    await db.commit()
    await db.refresh(db_ticket)
    return db_ticket

async def get_support_ticket(db: AsyncSession, ticket_id: int):
    result = await db.execute(select(models.SupportTicket).filter(models.SupportTicket.id == ticket_id))
    return result.scalar_one_or_none()

async def get_support_ticket_by_number(db: AsyncSession, ticket_number: str):
    result = await db.execute(select(models.SupportTicket).filter(models.SupportTicket.ticket_number == ticket_number))
    return result.scalar_one_or_none()

async def get_user_support_tickets(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.SupportTicket).filter(models.SupportTicket.user_id == user_id).order_by(models.SupportTicket.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()

async def get_all_support_tickets(db: AsyncSession, skip: int = 0, limit: int = 100, status: str = None):
    query = select(models.SupportTicket)
    if status:
        query = query.filter(models.SupportTicket.status == status)
    query = query.order_by(models.SupportTicket.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

async def update_support_ticket(db: AsyncSession, ticket_id: int, ticket_data: dict):
    db_ticket = await get_support_ticket(db, ticket_id)
    if db_ticket:
        if ticket_data.get("status") == "resolved":
            ticket_data["resolved_at"] = datetime.now()
        for key, value in ticket_data.items():
            if value is not None:
                setattr(db_ticket, key, value)
        db.add(db_ticket)
        await db.commit()
        await db.refresh(db_ticket)
    return db_ticket

async def delete_support_ticket(db: AsyncSession, ticket_id: int):
    db_ticket = await get_support_ticket(db, ticket_id)
    if db_ticket:
        await db.delete(db_ticket)
        await db.commit()
    return db_ticket

# ===== USER SETTINGS =====

async def get_or_create_user_settings(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.UserSettings).filter(models.UserSettings.user_id == user_id))
    db_settings = result.scalar_one_or_none()
    if not db_settings:
        db_settings = models.UserSettings(user_id=user_id)
        db.add(db_settings)
        await db.commit()
        await db.refresh(db_settings)
    return db_settings

async def get_user_settings(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.UserSettings).filter(models.UserSettings.user_id == user_id))
    return result.scalar_one_or_none()

async def update_user_settings(db: AsyncSession, user_id: int, settings_data: dict):
    db_settings = await get_or_create_user_settings(db, user_id)
    for key, value in settings_data.items():
        if value is not None:
            setattr(db_settings, key, value)
    db.add(db_settings)
    await db.commit()
    await db.refresh(db_settings)
    return db_settings

# ===== PROJECTS =====

async def create_project(db: AsyncSession, project: schemas.ProjectCreate, user_id: int):
    db_project = models.Project(**project.model_dump(), user_id=user_id)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

async def get_user_projects(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Project).filter(models.Project.user_id == user_id).offset(skip).limit(limit))
    return result.scalars().all()

async def get_project(db: AsyncSession, project_id: int):
    result = await db.execute(select(models.Project).filter(models.Project.id == project_id))
    return result.scalar_one_or_none()

async def update_project(db: AsyncSession, project_id: int, project_data: dict):
    db_project = await get_project(db, project_id)
    if db_project:
        for key, value in project_data.items():
            if value is not None:
                setattr(db_project, key, value)
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)
    return db_project

async def delete_project(db: AsyncSession, project_id: int):
    db_project = await get_project(db, project_id)
    if db_project:
        await db.delete(db_project)
        await db.commit()
    return db_project
