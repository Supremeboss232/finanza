"""User API endpoints for fetching and managing user-specific financial data."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc, func

from deps import get_current_user, SessionDep
import json
from models import User, Account, KYCInfo, UserSettings, Notification as DBNotification, Transaction
from crud import (
    get_user,
    get_user_transactions,
    get_user_deposits,
    get_user_loans,
    create_user_loan,
    get_user_investments,
    get_user_cards
)
from schemas import (
    User as PydanticUser,
    Transaction as PydanticTransaction,
    Deposit as PydanticDeposit,
    Loan as PydanticLoan,
    LoanCreate,
    LoanApplicationRequest,
    Investment as PydanticInvestment,
    Card as PydanticCard,
    Account as PydanticAccount,
    UserProfileUpdateRequest
)

router = APIRouter(
    prefix="/api/user",
    tags=["user-api"],
    dependencies=[Depends(get_current_user)]
)


# USER PROFILE & ACCOUNT INFO
@router.get("/profile", response_model=dict)
async def get_user_profile(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get current user's full profile information including KYC & UserSettings details."""
    kyc_res = await db_session.execute(select(KYCInfo).filter(KYCInfo.user_id == current_user.id))
    kyc_info = kyc_res.scalars().first()

    us_res = await db_session.execute(select(UserSettings).filter(UserSettings.user_id == current_user.id))
    user_settings = us_res.scalars().first()
    prefs = {}
    if user_settings and user_settings.preferences:
        try:
            prefs = json.loads(user_settings.preferences)
        except Exception:
            prefs = {}

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name or "",
        "account_number": current_user.account_number or "",
        "account_type": current_user.account_type or "Personal",
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "kyc_status": current_user.kyc_status or "pending",
        "kyc_verified": (current_user.kyc_status == "approved"),
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "phone_number": (user_settings.phone_number if user_settings and user_settings.phone_number else None)
                        or (kyc_info.phone_number if kyc_info else None)
                        or prefs.get("phone_number", ""),
        "address": (user_settings.address if user_settings and user_settings.address else None)
                   or (kyc_info.address if kyc_info else None)
                   or prefs.get("address", ""),
        "city": (kyc_info.city if kyc_info and getattr(kyc_info, "city", None) else None) or prefs.get("city", ""),
        "state": (kyc_info.state if kyc_info and getattr(kyc_info, "state", None) else None) or prefs.get("state", ""),
        "postal_code": (kyc_info.postal_code if kyc_info and getattr(kyc_info, "postal_code", None) else None) or prefs.get("postal_code", ""),
        "country": (kyc_info.country if kyc_info and getattr(kyc_info, "country", None) else None) or prefs.get("country", "USA"),
        "date_of_birth": (kyc_info.date_of_birth.isoformat() if kyc_info and getattr(kyc_info, "date_of_birth", None) and hasattr(kyc_info.date_of_birth, "isoformat") else (str(kyc_info.date_of_birth) if kyc_info and getattr(kyc_info, "date_of_birth", None) else prefs.get("date_of_birth", ""))),
        "id_type": (kyc_info.document_type if kyc_info and getattr(kyc_info, "document_type", None) else None) or prefs.get("id_type", "National ID"),
        "id_number": (kyc_info.document_number if kyc_info and getattr(kyc_info, "document_number", None) else None) or prefs.get("id_number", ""),
        "ssn": (kyc_info.ssn if kyc_info and getattr(kyc_info, "ssn", None) else None) or prefs.get("ssn", ""),
        "employer": prefs.get("employer", ""),
        "job_title": prefs.get("job_title", ""),
        "industry": prefs.get("industry", ""),
        "annual_income": prefs.get("annual_income", ""),
        "profile_picture_url": prefs.get("profile_picture_url") or prefs.get("avatar_url") or getattr(current_user, "profile_picture_url", None),
    }


@router.put("/profile", response_model=dict)
async def update_user_profile(
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update current user's personal & employment profile information."""
    try:
        if payload.get("full_name") is not None:
            current_user.full_name = str(payload["full_name"]).strip()
        if payload.get("account_type") is not None:
            current_user.account_type = str(payload["account_type"]).strip()
        db_session.add(current_user)

        us_res = await db_session.execute(select(UserSettings).filter(UserSettings.user_id == current_user.id))
        user_settings = us_res.scalars().first()
        if not user_settings:
            user_settings = UserSettings(user_id=current_user.id, preferences="{}")
            db_session.add(user_settings)
            await db_session.flush()

        if payload.get("phone_number") is not None:
            user_settings.phone_number = str(payload["phone_number"]).strip()
        if payload.get("address") is not None:
            user_settings.address = str(payload["address"]).strip()

        prefs = {}
        if user_settings.preferences:
            try:
                prefs = json.loads(user_settings.preferences)
            except Exception:
                prefs = {}

        for key in ("city", "state", "postal_code", "country", "date_of_birth", "employer", "job_title", "industry", "annual_income", "phone_number", "address"):
            if key in payload and payload[key] is not None:
                prefs[key] = payload[key]

        user_settings.preferences = json.dumps(prefs)
        db_session.add(user_settings)
        await db_session.commit()
        return await get_user_profile(db_session=db_session, current_user=current_user)
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to update profile: {str(e)}")


@router.get("/dashboard", response_model=dict)
async def get_user_dashboard_data(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get dashboard summary data (balance, investments, loans, recent transactions)."""
    try:
        # Cache user data IMMEDIATELY before any async operations
        # This prevents lazy loading issues
        user_data = {
            "id": current_user.id,
            "email": current_user.email or "",
            "full_name": current_user.full_name or "",
            "account_number": current_user.account_number or ""
        }
        user_id = current_user.id
        
        # Get recent transactions, deposits, loans, investments
        try:
            transactions = await get_user_transactions(db_session, user_id, skip=0, limit=5)
        except Exception as txn_error:
            import logging
            logging.error(f"Error getting transactions: {txn_error}")
            transactions = []
        
        try:
            deposits = await get_user_deposits(db_session, user_id)
        except Exception as dep_error:
            import logging
            logging.error(f"Error getting deposits: {dep_error}")
            deposits = []
        
        try:
            loans = await get_user_loans(db_session, user_id)
        except Exception as loan_error:
            import logging
            logging.error(f"Error getting loans: {loan_error}")
            loans = []
        
        try:
            investments = await get_user_investments(db_session, user_id)
        except Exception as inv_error:
            import logging
            logging.error(f"Error getting investments: {inv_error}")
            investments = []
        
        # Get user's primary account(s) - Single source of truth: Query by user_id only
        accounts_list = []
        total_balance = 0.0
        try:
            result = await db_session.execute(
                select(Account).filter(Account.owner_id == user_id)
            )
            user_accounts = result.scalars().all()
            
            if user_accounts:
                for account in user_accounts:
                    # Rule: Balance must NEVER be NULL
                    account_balance = account.balance if account.balance is not None else 0.0
                    total_balance += account_balance
                    accounts_list.append({
                        "id": account.id,
                        "account_number": account.account_number,
                        "account_type": account.account_type,
                        "balance": account_balance,
                        "currency": account.currency or "USD",
                        "status": "active",
                        "created_at": account.created_at.isoformat() if account.created_at else None
                    })
        except Exception as acc_error:
            import logging
            logging.error(f"Error getting accounts: {acc_error}")
            accounts_list = []
            total_balance = 0.0
        
        # Calculate summary metrics
        active_investments = len([i for i in investments if i.status == "active"]) if investments else 0
        active_loans = len([l for l in loans if l.status == "active"]) if loans else 0
        total_deposits = sum(d.amount for d in deposits) if deposits else 0.0
        
        # Build transactions list while objects are still in session
        transactions_list = []
        try:
            for t in transactions:
                if t.created_at:
                    created_at_str = t.created_at.isoformat()
                else:
                    created_at_str = None
                transactions_list.append({
                    "id": t.id,
                    "amount": t.amount,
                    "type": getattr(t, "transaction_type", None),
                    "status": t.status,
                    "created_at": created_at_str
                })
        except Exception as txn_fmt_error:
            import logging
            logging.error(f"Error formatting transactions: {txn_fmt_error}")
            transactions_list = []
        
        return {
            "user": user_data,
            "balance": total_balance,
            "accounts": accounts_list,
            "deposits": {
                "total_amount": total_deposits,
                "count": len(deposits) if deposits else 0
            },
            "active_investments": active_investments,
            "active_loans": active_loans,
            "recent_transactions": transactions_list
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# TRANSACTIONS
@router.get("/transactions", response_model=List[PydanticTransaction])
async def get_user_txn_list(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get user's transactions."""
    transactions = await get_user_transactions(db_session, current_user.id, skip=skip, limit=limit)
    return transactions


# CARDS
@router.get("/cards", response_model=List[PydanticCard])
async def get_user_cards_list(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get user's cards."""
    cards = await get_user_cards(db_session, current_user.id, skip=skip, limit=limit)
    return cards


@router.get("/cards/{card_id}", response_model=PydanticCard)
async def get_user_card_detail(
    card_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get a specific card."""
    from crud import get_card
    card = await get_card(db_session, card_id)
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.put("/cards/{card_id}/status", response_model=PydanticCard)
async def update_card_status(
    card_id: int,
    status_update: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Update card status (active, blocked, inactive)."""
    from crud import get_card
    card = await get_card(db_session, card_id)
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    
    new_status = status_update.get("status")
    if new_status not in ["active", "blocked", "inactive"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be 'active', 'blocked', or 'inactive'")
    
    card.status = new_status
    db_session.add(card)
    await db_session.commit()
    await db_session.refresh(card)
    return card


# DEPOSITS
@router.get("/deposits", response_model=List[PydanticDeposit])
async def get_user_deposits_list(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get user's deposits."""
    deposits = await get_user_deposits(db_session, current_user.id, skip=skip, limit=limit)
    return deposits


@router.get("/deposits/{deposit_id}", response_model=PydanticDeposit)
async def get_user_deposit_detail(
    deposit_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get a specific deposit."""
    from crud import get_deposit
    deposit = await get_deposit(db_session, deposit_id)
    if not deposit or deposit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    return deposit


# LOANS
@router.get("/loans", response_model=List[PydanticLoan])
async def get_user_loans_list(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get user's loans."""
    loans = await get_user_loans(db_session, current_user.id, skip=skip, limit=limit)
    return loans


# REMOVED: Duplicate old loan creation endpoint - replaced by unified POST endpoint below


@router.get("/loans/{loan_id}", response_model=PydanticLoan)
async def get_user_loan_detail(
    loan_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get a specific loan."""
    from crud import get_loan
    loan = await get_loan(db_session, loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


# INVESTMENTS
@router.get("/investments", response_model=List[PydanticInvestment])
async def get_user_investments_list(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100
):
    """Get user's investments."""
    investments = await get_user_investments(db_session, current_user.id, skip=skip, limit=limit)
    return investments


@router.get("/investments/{investment_id}", response_model=PydanticInvestment)
async def get_user_investment_detail(
    investment_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get a specific investment."""
    from crud import get_investment
    investment = await get_investment(db_session, investment_id)
    if not investment or investment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Investment not found")
    return investment


# ============= ENHANCED OPERATIONS FOR DEPOSITS, LOANS, CARDS, INVESTMENTS & TRANSFERS =============

from fastapi import Request, UploadFile, File, Body
from typing import Optional
from decimal import Decimal
import uuid
import os
from pathlib import Path as _Path
from models import Deposit, Loan, Investment, Card, Transaction

# Official Bank Product Rate Tables (Users cannot invent their own rates)
BANK_DEPOSIT_APY_TIERS = {
    ("savings", 6): 3.50,
    ("savings", 12): 3.75,
    ("savings", 24): 4.00,
    ("savings", 36): 4.25,
    ("fixed", 6): 4.25,
    ("fixed", 12): 4.75,
    ("fixed", 24): 5.10,
    ("fixed", 36): 5.50,
    ("recurring", 6): 4.00,
    ("recurring", 12): 4.50,
    ("recurring", 24): 4.85,
    ("recurring", 36): 5.20,
    ("recurring_savings", 6): 4.00,
    ("recurring_savings", 12): 4.50,
    ("recurring_savings", 24): 4.85,
    ("recurring_savings", 36): 5.20,
}

BANK_LOAN_APR_TIERS = {
    "personal": 8.50,
    "auto": 6.20,
    "home": 5.40,
    "mortgage": 5.40,
    "student": 4.80,
    "business": 7.90,
}

BANK_INVESTMENT_RETURN_TIERS = {
    "stocks": 8.50,
    "bonds": 5.20,
    "bond": 5.20,
    "mutual_funds": 7.00,
    "mutual_fund": 7.00,
    "etf": 7.50,
    "real_estate": 6.80,
    "crypto": 11.00,
    "term_deposit": 4.80,
    "commodities": 6.00,
}


async def _get_or_create_primary_account(db_session: AsyncSession, user: User) -> Account:
    result = await db_session.execute(
        select(Account).where(Account.owner_id == user.id).order_by(Account.id.asc())
    )
    account = result.scalars().first()
    if not account:
        acct_num = user.account_number or f"FNZ{user.id:08d}"
        account = Account(
            account_number=acct_num,
            account_type="checking",
            balance=Decimal("0.00"),
            currency="USD",
            owner_id=user.id,
            status="active",
            kyc_level="basic",
        )
        db_session.add(account)
        await db_session.flush()
    return account


@router.get("/product-rates")
async def get_bank_product_rates():
    """Return official bank-set APY/APR tiers for deposits, loans, and investments."""
    return {
        "deposit_apy": {f"{k[0]}_{k[1]}m": v for k, v in BANK_DEPOSIT_APY_TIERS.items()},
        "loan_apr": BANK_LOAN_APR_TIERS,
        "investment_return": BANK_INVESTMENT_RETURN_TIERS,
    }


@router.post("/deposits/{deposit_id}/withdraw", response_model=dict)
async def withdraw_from_deposit(
    deposit_id: int,
    request: Request,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    amount: Optional[float] = None,
):
    """Withdraw funds from a deposit vault back into the user's primary checking/savings account."""
    from crud import get_deposit

    if amount is None:
        try:
            body = await request.json()
            amount = float(body.get("amount", 0))
        except Exception:
            amount = 0.0

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Withdrawal amount must be greater than 0")

    deposit = await get_deposit(db_session, deposit_id)
    if not deposit or deposit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Deposit not found")

    current_bal = float(deposit.current_balance if deposit.current_balance is not None else deposit.amount or 0)
    if current_bal < amount:
        raise HTTPException(status_code=400, detail=f"Insufficient deposit balance (${current_bal:,.2f} available)")

    # Deduct from deposit vault
    new_dep_bal = round(current_bal - float(amount), 2)
    deposit.current_balance = Decimal(str(new_dep_bal))
    if new_dep_bal <= 0:
        deposit.status = "withdrawn"
    db_session.add(deposit)

    # Credit back to user's primary bank account
    account = await _get_or_create_primary_account(db_session, current_user)
    acct_bal = float(account.balance or 0)
    account.balance = Decimal(str(round(acct_bal + float(amount), 2)))
    db_session.add(account)

    # Record Transaction on ledger
    txn = Transaction(
        user_id=current_user.id,
        account_id=account.id,
        amount=Decimal(str(round(float(amount), 2))),
        transaction_type="deposit_withdrawal",
        direction="credit",
        status="completed",
        description=f"Withdrawal from Deposit #{deposit.id} to Account {account.account_number}",
        reference_number=f"DEPW-{uuid.uuid4().hex[:10].upper()}",
        kyc_status_at_time=current_user.kyc_status,
    )
    db_session.add(txn)

    await db_session.commit()
    await db_session.refresh(deposit)

    return {
        "success": True,
        "message": f"${amount:,.2f} withdrawn from Deposit #{deposit.id} and credited to your account ({account.account_number})",
        "new_balance": float(deposit.current_balance or 0),
        "account_balance": float(account.balance or 0),
        "deposit": {
            "id": deposit.id,
            "amount": float(deposit.amount or 0),
            "current_balance": float(deposit.current_balance or 0),
            "balance": float(deposit.current_balance or 0),
            "interest_earned": max(0.0, float(deposit.current_balance or 0) - float(deposit.amount or 0)),
            "status": deposit.status,
        },
    }


@router.post("/loans/request", response_model=dict)
async def request_loan(
    request: Request,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    amount: Optional[float] = None,
    term_months: Optional[int] = None,
    interest_rate: Optional[float] = None,
    purpose: Optional[str] = None,
    loan_type: Optional[str] = "personal",
):
    """Submit a loan request using official bank APR tiers."""
    if amount is None:
        try:
            body = await request.json()
            amount = float(body.get("amount", 0))
            term_months = int(body.get("term_months", 12))
            loan_type = body.get("loan_type", "personal")
            purpose = body.get("purpose", f"{loan_type} loan")
        except Exception:
            pass

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Loan amount must be greater than 0")
    term_months = int(term_months or 12)
    ltype = (loan_type or "personal").lower()
    rate = BANK_LOAN_APR_TIERS.get(ltype, 8.50)

    monthly_rate = rate / 100 / 12
    monthly_payment = (amount * monthly_rate) / (1 - (1 + monthly_rate) ** (-term_months)) if monthly_rate > 0 else (amount / term_months)

    loan = Loan(
        user_id=current_user.id,
        loan_type=ltype,
        amount=Decimal(str(round(amount, 2))),
        interest_rate=Decimal(str(rate)),
        term_months=term_months,
        monthly_payment=Decimal(str(round(monthly_payment, 2))),
        remaining_balance=Decimal(str(round(amount, 2))),
        paid_amount=Decimal("0.00"),
        status="pending",
        purpose=purpose or f"{ltype.title()} Loan",
    )
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)

    return {
        "success": True,
        "message": "Loan application submitted for underwriting review",
        "loan_id": loan.id,
        "amount": float(loan.amount),
        "interest_rate": float(loan.interest_rate),
        "monthly_payment": float(loan.monthly_payment),
        "term_months": loan.term_months,
        "status": loan.status,
    }


@router.post("/loans/{loan_id}/approve", response_model=dict)
async def approve_loan(
    loan_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Approve a loan request and disburse principal to user's account (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required to approve loans")
    from crud import get_loan

    loan = await get_loan(db_session, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    loan.status = "active"
    loan.approved_at = datetime.utcnow()
    db_session.add(loan)

    # Disburse loan principal into borrower's primary account
    borrower_res = await db_session.execute(select(User).where(User.id == loan.user_id))
    borrower = borrower_res.scalar_one_or_none()
    if borrower:
        acct = await _get_or_create_primary_account(db_session, borrower)
        acct.balance = Decimal(str(round(float(acct.balance or 0) + float(loan.amount or 0), 2)))
        db_session.add(acct)
        txn = Transaction(
            user_id=borrower.id,
            account_id=acct.id,
            amount=Decimal(str(loan.amount)),
            transaction_type="loan_disbursement",
            direction="credit",
            status="completed",
            description=f"Loan #{loan.id} Disbursement ({loan.loan_type})",
            reference_number=f"LNDS-{uuid.uuid4().hex[:10].upper()}",
            kyc_status_at_time=borrower.kyc_status,
        )
        db_session.add(txn)

    await db_session.commit()
    await db_session.refresh(loan)

    return {
        "success": True,
        "message": "Loan approved and disbursed to borrower account",
        "loan": {
            "id": loan.id,
            "amount": float(loan.amount),
            "monthly_payment": float(loan.monthly_payment),
            "status": loan.status,
        },
    }


@router.post("/loans/{loan_id}/payment", response_model=dict)
async def make_loan_payment(
    loan_id: int,
    request: Request,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    amount: Optional[float] = None,
):
    """Make a loan repayment by deducting from the user's primary checking/savings account."""
    from crud import get_loan

    if amount is None:
        try:
            body = await request.json()
            amount = float(body.get("amount", 0))
        except Exception:
            amount = 0.0

    if not amount or amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

    loan = await get_loan(db_session, loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status not in ("active", "approved"):
        raise HTTPException(status_code=400, detail=f"Loan is currently '{loan.status}' and cannot accept payments yet")

    rem = float(loan.remaining_balance or loan.amount or 0)
    if amount > rem:
        amount = rem

    # Verify and deduct from user's primary account balance
    account = await _get_or_create_primary_account(db_session, current_user)
    acct_bal = float(account.balance or 0)
    if acct_bal < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient account balance (${acct_bal:,.2f} available) to make ${amount:,.2f} loan payment",
        )

    account.balance = Decimal(str(round(acct_bal - amount, 2)))
    db_session.add(account)

    new_rem = round(rem - amount, 2)
    new_paid = round(float(loan.paid_amount or 0) + amount, 2)
    loan.remaining_balance = Decimal(str(new_rem))
    loan.paid_amount = Decimal(str(new_paid))
    if new_rem <= 0:
        loan.status = "completed"
    db_session.add(loan)

    txn = Transaction(
        user_id=current_user.id,
        account_id=account.id,
        amount=Decimal(str(round(amount, 2))),
        transaction_type="loan_repayment",
        direction="debit",
        status="completed",
        description=f"Loan #{loan.id} Repayment ({loan.loan_type or 'Loan'})",
        reference_number=f"LNPY-{uuid.uuid4().hex[:10].upper()}",
        kyc_status_at_time=current_user.kyc_status,
    )
    db_session.add(txn)

    await db_session.commit()
    await db_session.refresh(loan)

    return {
        "success": True,
        "message": f"Loan payment of ${amount:,.2f} completed from account {account.account_number}",
        "remaining_balance": float(loan.remaining_balance or 0),
        "total_paid": float(loan.paid_amount or 0),
        "account_balance": float(account.balance or 0),
        "loan_status": loan.status,
    }


@router.get("/investments/{investment_id}/details", response_model=dict)
async def get_investment_details(
    investment_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get detailed investment information including returns and performance."""
    from crud import get_investment

    investment = await get_investment(db_session, investment_id)
    if not investment or investment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Investment not found")

    created_naive = investment.created_at.replace(tzinfo=None) if investment.created_at else datetime.utcnow()
    days_invested = max(0, (datetime.utcnow() - created_naive).days)
    amt = float(investment.amount or 0)
    rate = float(investment.annual_return_rate or 0)
    interest_earned = float(investment.interest_earned or 0)
    expected_interest = (amt * rate / 100.0) * (days_invested / 365.0)

    return {
        "investment_id": investment.id,
        "type": investment.investment_type,
        "amount_invested": amt,
        "current_value": float(investment.current_value or amt),
        "interest_earned": interest_earned,
        "expected_interest": round(expected_interest, 2),
        "annual_return_rate": f"{rate}%",
        "total_return": round(interest_earned + expected_interest, 2),
        "days_invested": days_invested,
        "purpose": investment.purpose,
        "status": investment.status,
        "maturity_date": investment.maturity_date.isoformat() if investment.maturity_date else None,
    }


@router.post("/cards/{card_id}/balance", response_model=dict)
async def update_card_balance(
    card_id: int,
    amount: float,
    transaction_type: str,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Transfer funds between user's primary bank account and their card balance."""
    from crud import get_card

    card = await get_card(db_session, card_id)
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")

    account = await _get_or_create_primary_account(db_session, current_user)
    acct_bal = float(account.balance or 0)
    card_bal = float(card.balance or 0)

    if transaction_type.lower() == "deposit":
        if acct_bal < amount:
            raise HTTPException(status_code=400, detail=f"Insufficient account balance (${acct_bal:,.2f})")
        account.balance = Decimal(str(round(acct_bal - amount, 2)))
        card.balance = Decimal(str(round(card_bal + amount, 2)))
        action = "loaded onto"
    elif transaction_type.lower() == "withdrawal":
        if card_bal < amount:
            raise HTTPException(status_code=400, detail="Insufficient card balance")
        card.balance = Decimal(str(round(card_bal - amount, 2)))
        account.balance = Decimal(str(round(acct_bal + amount, 2)))
        action = "transferred to account from"
    else:
        raise HTTPException(status_code=400, detail="Invalid transaction type")

    db_session.add(account)
    db_session.add(card)
    await db_session.commit()
    await db_session.refresh(card)

    return {
        "success": True,
        "message": f"${amount:.2f} {action} card",
        "card_id": card.id,
        "new_balance": float(card.balance),
        "account_balance": float(account.balance),
        "transaction_type": transaction_type,
        "card_status": card.status,
    }


# ===== SECURITY & SETTINGS ENDPOINTS =====

@router.post("/change-password")
async def change_password(
    password_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Change user password."""
    from auth_utils import verify_password, get_password_hash

    old_password = password_data.get("old_password")
    new_password = password_data.get("new_password")
    confirm_password = password_data.get("confirm_password", new_password)

    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    current_user.hashed_password = get_password_hash(new_password)
    db_session.add(current_user)
    await db_session.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.post("/enable-2fa")
async def enable_2fa(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Enable two-factor authentication."""
    try:
        import pyotp
        secret_key = pyotp.random_base32()
    except ImportError:
        import secrets as _secrets
        secret_key = _secrets.token_hex(20).upper()[:32]
    current_user.mfa_secret = secret_key
    current_user.mfa_enabled = True
    db_session.add(current_user)
    await db_session.commit()
    return {
        "success": True,
        "message": "2FA enabled successfully",
        "secret_key": secret_key,
    }


@router.get("/login-history")
async def get_login_history(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    return {"login_history": []}


@router.get("/trusted-devices")
async def get_trusted_devices(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    return {"trusted_devices": []}


@router.delete("/trusted-devices/{device_id}")
async def remove_trusted_device(
    device_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "message": "Device removed successfully"}


@router.post("/trusted-devices/clear-all")
async def clear_all_trusted_devices(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    return {"success": True, "message": "All trusted devices cleared"}


@router.get("/security-questions")
async def get_security_questions(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row and settings_row.preferences:
        try:
            prefs = json.loads(settings_row.preferences)
            raw_questions = prefs.get("security_questions", [])
            questions_only = [{"question": q["question"]} for q in raw_questions]
            return {
                "security_questions": questions_only,
                "has_security_questions": bool(questions_only),
            }
        except (json.JSONDecodeError, KeyError):
            pass
    return {"security_questions": [], "has_security_questions": False}


@router.post("/security-questions")
async def set_security_questions(
    questions_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    from auth_utils import get_password_hash

    questions = questions_data.get("questions", [])
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No questions provided",
        )

    hashed_questions = [
        {"question": q["question"], "answer_hash": get_password_hash(str(q["answer"]))}
        for q in questions
    ]

    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = UserSettings(user_id=current_user.id)
        db_session.add(settings_row)

    try:
        prefs = json.loads(settings_row.preferences) if settings_row.preferences else {}
    except json.JSONDecodeError:
        prefs = {}
    prefs["security_questions"] = hashed_questions
    settings_row.preferences = json.dumps(prefs)

    await db_session.commit()
    return {"success": True, "message": "Security questions updated successfully"}


@router.get("/notification-preferences")
async def get_notification_preferences(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()

    prefs_extra = {
        "push_notifications": True,
        "transaction_alerts": True,
        "security_alerts": True,
        "marketing_emails": False,
    }
    if settings_row and settings_row.preferences:
        try:
            stored = json.loads(settings_row.preferences)
            prefs_extra.update({k: stored[k] for k in prefs_extra if k in stored})
        except json.JSONDecodeError:
            pass

    return {
        "email_notifications": settings_row.email_notifications if settings_row else True,
        "sms_notifications": settings_row.sms_notifications if settings_row else False,
        **prefs_extra,
    }


@router.put("/notification-preferences")
async def update_notification_preferences(
    prefs: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = UserSettings(user_id=current_user.id)
        db_session.add(settings_row)

    if "email_notifications" in prefs:
        settings_row.email_notifications = bool(prefs["email_notifications"])
    if "sms_notifications" in prefs:
        settings_row.sms_notifications = bool(prefs["sms_notifications"])

    extra_keys = ("push_notifications", "transaction_alerts", "security_alerts", "marketing_emails")
    try:
        stored_prefs = json.loads(settings_row.preferences) if settings_row.preferences else {}
    except json.JSONDecodeError:
        stored_prefs = {}
    for key in extra_keys:
        if key in prefs:
            stored_prefs[key] = bool(prefs[key])
    settings_row.preferences = json.dumps(stored_prefs)

    await db_session.commit()
    return {"success": True, "message": "Notification preferences updated successfully"}


# ===== DASHBOARD & ACCOUNT SUPPORT ENDPOINTS =====

@router.get("/balance")
async def get_user_balance(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    result = await db_session.execute(
        select(Account).filter(Account.owner_id == current_user.id)
    )
    user_accounts = result.scalars().all()
    total_balance = sum(float(a.balance) if a.balance is not None else 0.0 for a in user_accounts)
    return {
        "total_balance": round(total_balance, 2),
        "currency": "USD",
        "account_count": len(user_accounts),
        "last_updated": datetime.utcnow().isoformat(),
    }


@router.get("/accounts")
async def get_user_accounts(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    account = await _get_or_create_primary_account(db_session, current_user)
    await db_session.commit()
    result = await db_session.execute(
        select(Account).filter(Account.owner_id == current_user.id).order_by(Account.id.asc())
    )
    user_accounts = result.scalars().all()

    accounts_list = []
    for acc in user_accounts:
        acc_bal = float(acc.balance) if acc.balance is not None else 0.0
        acct_type = (acc.account_type or "checking").title()
        accounts_list.append({
            "id": acc.id,
            "name": f"{acct_type} ({acc.account_number})",
            "account_number": acc.account_number,
            "account_type": acc.account_type or "checking",
            "balance": acc_bal,
            "currency": acc.currency or "USD",
            "status": getattr(acc, "status", "active"),
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
        })

    return {
        "accounts": accounts_list,
        "total": len(accounts_list),
    }


@router.get("/account-status")
async def get_user_account_status(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    is_suspended = not current_user.is_active if hasattr(current_user, "is_active") else False
    is_frozen = getattr(current_user, "is_frozen", False)
    return {
        "is_suspended": is_suspended,
        "suspension_reason": getattr(current_user, "suspension_reason", None),
        "is_frozen": is_frozen,
        "freeze_reason": getattr(current_user, "freeze_reason", None),
        "is_active": current_user.is_active if hasattr(current_user, "is_active") else True,
    }


@router.post("/close-account")
async def close_account(
    password_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    from auth_utils import verify_password
    password = password_data.get("password")
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    return {
        "success": True,
        "message": "Account closure request submitted. Our compliance team will process it within 24 hours.",
    }


@router.post("/upload-profile-picture")
async def upload_profile_picture(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    file: Optional[UploadFile] = File(None),
):
    """Upload user's profile picture and persist URL in UserSettings."""
    upload_dir = _Path("static") / "uploads" / "profile_pics"
    upload_dir.mkdir(parents=True, exist_ok=True)

    if file and file.filename:
        safe_name = f"user_{current_user.id}_{os.path.basename(file.filename)}"
        save_path = upload_dir / safe_name
        contents = await file.read()
        save_path.write_bytes(contents)
        public_url = f"/static/uploads/profile_pics/{safe_name}"
    else:
        public_url = "/static/img/team-1.jpg"

    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = UserSettings(user_id=current_user.id)
        db_session.add(settings_row)
    try:
        prefs = json.loads(settings_row.preferences) if settings_row.preferences else {}
    except Exception:
        prefs = {}
    prefs["avatar_url"] = public_url
    settings_row.preferences = json.dumps(prefs)
    await db_session.commit()

    return {
        "success": True,
        "message": "Profile picture uploaded successfully",
        "url": public_url,
        "picture_url": public_url,
    }


@router.get("/transactions/{transaction_id}/receipt")
async def get_transaction_receipt(
    transaction_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    txn = await get_user_transactions(db_session, current_user.id, limit=500)
    receipt_txn = next((t for t in txn if t.id == transaction_id), None)
    if not receipt_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {
        "transaction_id": receipt_txn.id,
        "reference_number": getattr(receipt_txn, "reference_number", f"TXN-{receipt_txn.id}"),
        "amount": float(receipt_txn.amount or 0),
        "type": getattr(receipt_txn, "transaction_type", "transfer"),
        "direction": getattr(receipt_txn, "direction", "debit"),
        "description": getattr(receipt_txn, "description", ""),
        "date": receipt_txn.created_at.isoformat() if receipt_txn.created_at else None,
        "status": receipt_txn.status,
    }


# ============= RECIPIENTS & TRANSFERS (DOMESTIC, P2P, INTERNATIONAL, BILL PAY) =============

@router.get("/recipients")
async def list_saved_recipients(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get user's saved transfer recipients stored in UserSettings.preferences."""
    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    recipients = []
    if settings_row and settings_row.preferences:
        try:
            prefs = json.loads(settings_row.preferences)
            recipients = prefs.get("saved_recipients", [])
        except Exception:
            recipients = []
    return recipients


@router.post("/recipients")
async def add_saved_recipient(
    recipient_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Save a transfer recipient for quick reuse."""
    result = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = result.scalar_one_or_none()
    if settings_row is None:
        settings_row = UserSettings(user_id=current_user.id)
        db_session.add(settings_row)
    try:
        prefs = json.loads(settings_row.preferences) if settings_row.preferences else {}
    except Exception:
        prefs = {}

    recipients = prefs.get("saved_recipients", [])
    new_rec = {
        "id": len(recipients) + 1,
        "name": (recipient_data.get("name") or recipient_data.get("recipient_name") or "Recipient").strip(),
        "email": (recipient_data.get("email") or "").strip(),
        "account_number": (recipient_data.get("account_number") or "").strip(),
        "routing_number": (recipient_data.get("routing_number") or "").strip(),
        "account_type": (recipient_data.get("account_type") or "checking").strip(),
        "bank_name": (recipient_data.get("bank_name") or "Finanza / Domestic Bank").strip(),
        "country": (recipient_data.get("country") or "US").strip(),
    }
    recipients.append(new_rec)
    prefs["saved_recipients"] = recipients
    settings_row.preferences = json.dumps(prefs)
    await db_session.commit()
    return {"success": True, "recipient": new_rec}


@router.get("/transfers")
async def list_user_transfers(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    """Return user's transfer history from the Transaction ledger."""
    result = await db_session.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )
    txns = result.scalars().all()
    items = []
    for t in txns:
        ttype = (t.transaction_type or "").lower()
        if any(k in ttype for k in ("transfer", "wire", "ach", "bill", "p2p", "international", "payment")):
            items.append({
                "id": t.id,
                "type": t.transaction_type,
                "recipient_name": t.description or "Transfer Recipient",
                "amount": float(t.amount or 0),
                "direction": t.direction or "debit",
                "status": t.status or "completed",
                "reference_number": t.reference_number or f"TXN-{t.id}",
                "created_at": t.created_at.isoformat() if t.created_at else None,
            })
    return items


@router.post("/transfers")
async def execute_user_transfer(
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Execute a Domestic Transfer, Finanza-to-Finanza P2P Transfer, International Wire, or Bill Payment.
    Validates available balance, debits sender's Account, credits internal recipient if applicable,
    and records full Transaction audit trail.
    """
    if getattr(current_user, "is_frozen", False) or not getattr(current_user, "is_active", True):
        raise HTTPException(status_code=403, detail="Your account is currently restricted from outbound transfers.")

    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Transfer amount must be greater than $0.00")

    transfer_type = (payload.get("transfer_type") or "domestic_transfer").strip().lower()
    from_account_id = payload.get("from_account_id")
    recipient_name = (payload.get("recipient_name") or payload.get("biller") or "Recipient").strip()
    recipient_account = (payload.get("recipient_account") or payload.get("account_number") or "").strip()
    recipient_email = (payload.get("recipient_email") or "").strip()
    routing_number = (payload.get("routing_number") or "").strip()
    country = (payload.get("country") or "US").strip()
    currency = (payload.get("currency") or "USD").strip().upper()
    memo = (payload.get("memo") or "").strip()
    save_recipient = bool(payload.get("save_recipient", False))

    # Fee calculation (0 for domestic/P2P/bill_pay, 1.5% for international wire)
    fee = round(amount * 0.015, 2) if "international" in transfer_type else 0.0
    total_debit = round(amount + fee, 2)

    # Locate source account
    if from_account_id:
        res = await db_session.execute(
            select(Account).where(Account.id == int(from_account_id), Account.owner_id == current_user.id)
        )
        source_account = res.scalar_one_or_none()
    else:
        source_account = None
    if not source_account:
        source_account = await _get_or_create_primary_account(db_session, current_user)

    available = float(source_account.balance or 0)
    if available < total_debit:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient funds in account {source_account.account_number}. Available: ${available:,.2f}, Required: ${total_debit:,.2f}",
        )

    # Deduct from sender account
    source_account.balance = Decimal(str(round(available - total_debit, 2)))
    db_session.add(source_account)

    # Check if recipient is an internal Finanza user (by account_number or email)
    internal_recipient_user = None
    internal_recipient_account = None
    if recipient_account:
        r_acc = await db_session.execute(select(Account).where(Account.account_number == recipient_account))
        internal_recipient_account = r_acc.scalar_one_or_none()
        if internal_recipient_account:
            r_usr = await db_session.execute(select(User).where(User.id == internal_recipient_account.owner_id))
            internal_recipient_user = r_usr.scalar_one_or_none()
    if not internal_recipient_user and recipient_email:
        r_usr = await db_session.execute(select(User).where(User.email == recipient_email))
        internal_recipient_user = r_usr.scalar_one_or_none()
        if internal_recipient_user:
            internal_recipient_account = await _get_or_create_primary_account(db_session, internal_recipient_user)

    ref_num = f"TRF-{uuid.uuid4().hex[:10].upper()}"
    desc = f"{transfer_type.replace('_', ' ').title()} to {recipient_name}"
    if recipient_account:
        desc += f" ({recipient_account[-4:]})"
    if memo:
        desc += f" — {memo}"

    sender_txn = Transaction(
        user_id=current_user.id,
        account_id=source_account.id,
        recipient_user_id=internal_recipient_user.id if internal_recipient_user else None,
        amount=Decimal(str(total_debit)),
        transaction_type=transfer_type,
        direction="debit",
        status="completed",
        description=desc,
        reference_number=ref_num,
        kyc_status_at_time=current_user.kyc_status,
    )
    db_session.add(sender_txn)

    # Credit internal Finanza recipient atomically if matched
    if internal_recipient_user and internal_recipient_account and internal_recipient_account.id != source_account.id:
        rec_bal = float(internal_recipient_account.balance or 0)
        internal_recipient_account.balance = Decimal(str(round(rec_bal + amount, 2)))
        db_session.add(internal_recipient_account)

        rec_txn = Transaction(
            user_id=internal_recipient_user.id,
            account_id=internal_recipient_account.id,
            recipient_user_id=current_user.id,
            amount=Decimal(str(round(amount, 2))),
            transaction_type="transfer_received",
            direction="credit",
            status="completed",
            description=f"Transfer from {current_user.full_name or current_user.email}" + (f" — {memo}" if memo else ""),
            reference_number=f"{ref_num}-CR",
            kyc_status_at_time=internal_recipient_user.kyc_status,
        )
        db_session.add(rec_txn)

    # Optionally save recipient to UserSettings
    if save_recipient and recipient_name:
        await add_saved_recipient(
            {
                "name": recipient_name,
                "email": recipient_email,
                "account_number": recipient_account,
                "routing_number": routing_number,
                "country": country,
            },
            db_session,
            current_user,
        )

    await db_session.commit()
    await db_session.refresh(sender_txn)

    return {
        "success": True,
        "message": f"Transfer of ${amount:,.2f} to {recipient_name} completed.",
        "reference_number": ref_num,
        "transaction_id": sender_txn.id,
        "amount": amount,
        "fee": fee,
        "total_debited": total_debit,
        "new_balance": float(source_account.balance or 0),
        "status": sender_txn.status,
    }


# ============= CREATE CARD, DEPOSIT, LOAN, INVESTMENT =============

@router.post("/cards")
async def create_card_endpoint(
    card_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """Issue a new Virtual/Physical Debit, Credit, or Savings card linked to the user's account."""
    from card_processing_service import CardProcessingService
    from datetime import timedelta

    card_type = (card_data.get("card_type") or "debit").lower()
    card_number = CardProcessingService._generate_card_number(card_type)
    expiry_date = (datetime.utcnow() + timedelta(days=365 * 4)).strftime("%m/%y")
    account = await _get_or_create_primary_account(db_session, current_user)

    credit_limit = 10000.0 if card_type == "credit" else 0.0
    initial_bal = float(account.balance or 0) if card_type in ("debit", "savings") else 0.0

    new_card = Card(
        user_id=current_user.id,
        card_number=card_number,
        card_type=card_type,
        card_holder_name=current_user.full_name or current_user.email,
        expiry_date=expiry_date,
        balance=Decimal(str(round(initial_bal, 2))),
        credit_limit=Decimal(str(credit_limit)),
        transaction_limit=Decimal("5000.00"),
        status="active",
    )
    db_session.add(new_card)
    await db_session.commit()
    await db_session.refresh(new_card)

    return {
        "id": new_card.id,
        "user_id": new_card.user_id,
        "card_number": new_card.card_number,
        "card_type": new_card.card_type,
        "card_holder_name": new_card.card_holder_name,
        "expiry_date": new_card.expiry_date,
        "balance": float(new_card.balance or 0),
        "credit_limit": float(new_card.credit_limit or 0),
        "transaction_limit": float(new_card.transaction_limit or 0),
        "status": new_card.status,
        "created_at": new_card.created_at.isoformat() if new_card.created_at else None,
    }


@router.post("/deposits")
async def create_deposit_endpoint(
    deposit_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """
    Create a new Term / Savings Deposit.
    - Uses official Bank APY Tiers (cannot be manipulated by client).
    - If funding_source == 'account_balance' (default): verifies and deducts from user's primary Account.balance.
    - If funding_source == 'external_gateway': creates a 'pending_payment' deposit awaiting gateway webhook confirmation.
    """
    from datetime import timedelta

    amount = float(deposit_data.get("amount") or 0)
    if amount < 100:
        raise HTTPException(status_code=400, detail="Minimum deposit amount is $100.00")

    term_months = int(deposit_data.get("term_months") or 12)
    deposit_type = (deposit_data.get("deposit_type") or "savings").lower()
    funding_source = (deposit_data.get("funding_source") or "account_balance").lower()
    gateway_provider = (deposit_data.get("gateway_provider") or "stripe").lower()

    # Official Bank APY lookup
    interest_rate = BANK_DEPOSIT_APY_TIERS.get((deposit_type, term_months), 4.25)
    maturity_date = datetime.utcnow() + timedelta(days=term_months * 30)

    account = await _get_or_create_primary_account(db_session, current_user)

    if funding_source == "external_gateway":
        # External Pay-In: Does NOT credit balance until payment gateway webhook confirms!
        dep_status = "pending_payment"
    else:
        # Internal Transfer from Checking/Savings Balance into Term Deposit Vault
        available = float(account.balance or 0)
        if available < amount:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient account balance (${available:,.2f} available) to fund a ${amount:,.2f} deposit. "
                    f"Select 'Fund via External Payment Gateway' or add funds to your account first."
                ),
            )
        account.balance = Decimal(str(round(available - amount, 2)))
        db_session.add(account)
        dep_status = "active"

        txn = Transaction(
            user_id=current_user.id,
            account_id=account.id,
            amount=Decimal(str(round(amount, 2))),
            transaction_type="deposit_lock",
            direction="debit",
            status="completed",
            description=f"Opened {term_months}M {deposit_type.replace('_', ' ').title()} Deposit @ {interest_rate}% APY",
            reference_number=f"DEPL-{uuid.uuid4().hex[:10].upper()}",
            kyc_status_at_time=current_user.kyc_status,
        )
        db_session.add(txn)

    deposit = Deposit(
        user_id=current_user.id,
        amount=Decimal(str(round(amount, 2))),
        current_balance=Decimal(str(round(amount, 2))) if dep_status == "active" else Decimal("0.00"),
        currency="USD",
        interest_rate=Decimal(str(interest_rate)),
        term_months=term_months,
        maturity_date=maturity_date,
        status=dep_status,
    )
    db_session.add(deposit)
    await db_session.commit()
    await db_session.refresh(deposit)

    return {
        "id": deposit.id,
        "user_id": deposit.user_id,
        "deposit_type": deposit_type,
        "amount": float(deposit.amount or 0),
        "current_balance": float(deposit.current_balance or 0),
        "account_balance": float(account.balance or 0),
        "currency": "USD",
        "interest_rate": float(deposit.interest_rate or interest_rate),
        "term_months": term_months,
        "funding_source": funding_source,
        "gateway_provider": gateway_provider if funding_source == "external_gateway" else None,
        "maturity_date": maturity_date.isoformat() if maturity_date else None,
        "status": deposit.status,
        "created_at": deposit.created_at.isoformat() if deposit.created_at else None,
    }


@router.post("/loans")
async def create_loan_endpoint(
    loan_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """Submit a new loan application using official bank APR tiers."""
    amount = float(loan_data.get("amount") or 0)
    term_months = int(loan_data.get("term_months") or 12)
    loan_type = (loan_data.get("loan_type") or "personal").lower()
    purpose = loan_data.get("purpose") or f"{loan_type.title()} Loan"

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Loan amount must be greater than 0")
    if term_months <= 0:
        raise HTTPException(status_code=400, detail="Loan term must be greater than 0")

    interest_rate = BANK_LOAN_APR_TIERS.get(loan_type, 8.50)
    monthly_rate = interest_rate / 100 / 12
    monthly_payment = (amount * monthly_rate) / (1 - (1 + monthly_rate) ** (-term_months)) if monthly_rate > 0 else (amount / term_months)

    loan = Loan(
        user_id=current_user.id,
        loan_type=loan_type,
        amount=Decimal(str(round(amount, 2))),
        remaining_balance=Decimal(str(round(amount, 2))),
        interest_rate=Decimal(str(interest_rate)),
        term_months=term_months,
        monthly_payment=Decimal(str(round(monthly_payment, 2))),
        paid_amount=Decimal("0.00"),
        purpose=purpose,
        status="pending",
    )
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)

    return {
        "id": loan.id,
        "user_id": loan.user_id,
        "loan_type": loan_type,
        "amount": float(loan.amount),
        "remaining_balance": float(loan.remaining_balance),
        "interest_rate": float(loan.interest_rate),
        "term_months": term_months,
        "monthly_payment": float(loan.monthly_payment),
        "paid_amount": 0.0,
        "purpose": purpose,
        "status": "pending",
        "created_at": loan.created_at.isoformat() if loan.created_at else None,
    }


@router.post("/investments")
async def create_investment_endpoint(
    investment_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None,
):
    """
    Purchase a new Investment product.
    Verifies and deducts the investment principal from the user's primary Account.balance.
    """
    from datetime import timedelta

    amount = float(investment_data.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Investment amount must be greater than $0.00")

    investment_type = (investment_data.get("investment_type") or "stocks").lower()
    purpose = investment_data.get("purpose") or f"{investment_type.replace('_', ' ').title()} Portfolio"
    annual_return_rate = BANK_INVESTMENT_RETURN_TIERS.get(investment_type, 7.00)

    account = await _get_or_create_primary_account(db_session, current_user)
    available = float(account.balance or 0)
    if available < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient account balance (${available:,.2f} available) to invest ${amount:,.2f}.",
        )

    # Deduct investment amount from primary account
    account.balance = Decimal(str(round(available - amount, 2)))
    db_session.add(account)

    maturity_date = datetime.utcnow() + timedelta(days=365) if investment_type in ("term_deposit", "bond", "bonds", "insurance") else None

    investment = Investment(
        user_id=current_user.id,
        investment_type=investment_type,
        amount=Decimal(str(round(amount, 2))),
        current_value=Decimal(str(round(amount, 2))),
        annual_return_rate=Decimal(str(annual_return_rate)),
        interest_earned=Decimal("0.00"),
        purpose=purpose,
        maturity_date=maturity_date,
        status="active",
    )
    db_session.add(investment)

    txn = Transaction(
        user_id=current_user.id,
        account_id=account.id,
        amount=Decimal(str(round(amount, 2))),
        transaction_type="investment_purchase",
        direction="debit",
        status="completed",
        description=f"Invested in {investment_type.replace('_', ' ').title()} ({annual_return_rate}% Est. Return)",
        reference_number=f"INV-{uuid.uuid4().hex[:10].upper()}",
        kyc_status_at_time=current_user.kyc_status,
    )
    db_session.add(txn)

    await db_session.commit()
    await db_session.refresh(investment)

    return {
        "id": investment.id,
        "user_id": investment.user_id,
        "investment_type": investment.investment_type,
        "amount": float(investment.amount),
        "current_value": float(investment.current_value),
        "annual_return_rate": float(investment.annual_return_rate),
        "interest_earned": 0.0,
        "account_balance": float(account.balance),
        "purpose": purpose,
        "maturity_date": maturity_date.isoformat() if maturity_date else None,
        "status": "active",
        "created_at": investment.created_at.isoformat() if investment.created_at else None,
    }


# ============= ADDITIONAL DIGITAL BANKING ENDPOINTS =============

@router.post("/accounts")
async def open_sub_account(
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Open an additional Checking, High-Yield Savings, or Multi-Currency sub-account."""
    from account_number_generator import generate_unique_account_number

    account_type = (payload.get("account_type") or "savings").strip().lower()
    currency = (payload.get("currency") or "USD").strip().upper()
    initial_deposit = float(payload.get("initial_deposit") or 0.0)

    primary = await _get_or_create_primary_account(db_session, current_user)
    if initial_deposit > 0:
        avail = float(primary.balance or 0)
        if avail < initial_deposit:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient balance in primary account (${avail:,.2f}) to fund initial deposit of ${initial_deposit:,.2f}.",
            )
        primary.balance = Decimal(str(round(avail - initial_deposit, 2)))
        db_session.add(primary)

    acct_num = await generate_unique_account_number(db_session)
    new_acc = Account(
        owner_id=current_user.id,
        account_number=acct_num,
        account_type=account_type,
        balance=Decimal(str(round(initial_deposit, 2))),
        currency=currency,
        status="active",
    )
    db_session.add(new_acc)
    await db_session.flush()

    if initial_deposit > 0:
        txn = Transaction(
            user_id=current_user.id,
            account_id=new_acc.id,
            amount=Decimal(str(round(initial_deposit, 2))),
            transaction_type="internal_transfer",
            direction="credit",
            status="completed",
            description=f"Initial funding for new {currency} {account_type.title()} Account ({acct_num})",
            reference_number=f"ACC-{uuid.uuid4().hex[:10].upper()}",
            kyc_status_at_time=current_user.kyc_status,
        )
        db_session.add(txn)

    await db_session.commit()
    await db_session.refresh(new_acc)
    return {
        "success": True,
        "message": f"New {currency} {account_type.title()} account ({acct_num}) opened successfully.",
        "account": {
            "id": new_acc.id,
            "account_number": new_acc.account_number,
            "account_type": new_acc.account_type,
            "balance": float(new_acc.balance or 0),
            "currency": new_acc.currency,
            "status": new_acc.status,
        },
    }


@router.post("/accounts/fund")
async def initiate_account_funding(
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Record an external funding request (Payment Gateway Pay-In or Mobile Check Deposit).
    External funds are marked 'pending' until webhook or back-office clearing confirms settlement.
    """
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Deposit amount must be greater than $0.00")

    method = (payload.get("method") or "payment_gateway").strip().lower()
    provider = (payload.get("provider") or "stripe").strip()
    check_number = (payload.get("check_number") or "").strip()
    notes = (payload.get("notes") or "").strip()

    account = await _get_or_create_primary_account(db_session, current_user)
    ref_num = f"FND-{uuid.uuid4().hex[:10].upper()}"

    if method == "mobile_check":
        desc = f"Mobile Check Deposit #{check_number or 'N/A'} (Pending Clearing Verification)"
    else:
        desc = f"External Deposit via {provider.title()} Gateway (Awaiting Settlement Webhook)"
    if notes:
        desc += f" — {notes}"

    txn = Transaction(
        user_id=current_user.id,
        account_id=account.id,
        amount=Decimal(str(round(amount, 2))),
        transaction_type="external_deposit",
        direction="credit",
        status="pending",
        description=desc,
        reference_number=ref_num,
        kyc_status_at_time=current_user.kyc_status,
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    return {
        "success": True,
        "reference_number": ref_num,
        "transaction_id": txn.id,
        "amount": amount,
        "status": "pending",
        "message": (
            f"Mobile check deposit of ${amount:,.2f} submitted for clearing (Ref: {ref_num})."
            if method == "mobile_check"
            else f"Payment gateway session initialized for ${amount:,.2f} via {provider.title()} (Ref: {ref_num}). Your balance will credit automatically upon gateway webhook confirmation."
        ),
    }


@router.put("/cards/{card_id}/status")
async def toggle_card_status(
    card_id: int,
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Freeze or unfreeze a user's card."""
    res = await db_session.execute(
        select(Card).where(Card.id == card_id, Card.user_id == current_user.id)
    )
    card = res.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    new_status = (payload.get("status") or ("frozen" if card.status == "active" else "active")).lower()
    if new_status not in ("active", "frozen", "blocked"):
        new_status = "frozen"
    card.status = new_status
    db_session.add(card)
    await db_session.commit()
    return {
        "success": True,
        "id": card.id,
        "status": card.status,
        "message": f"Card ending in {str(card.card_number)[-4:]} is now {card.status.upper()}.",
    }


@router.put("/cards/{card_id}/limits")
async def update_card_limits(
    card_id: int,
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Update daily/per-transaction spending limit on a user's card."""
    res = await db_session.execute(
        select(Card).where(Card.id == card_id, Card.user_id == current_user.id)
    )
    card = res.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    new_limit = float(payload.get("transaction_limit") or 5000.0)
    if new_limit < 100 or new_limit > 100000:
        raise HTTPException(status_code=400, detail="Spending limit must be between $100 and $100,000")

    card.transaction_limit = Decimal(str(round(new_limit, 2)))
    db_session.add(card)
    await db_session.commit()
    return {
        "success": True,
        "id": card.id,
        "transaction_limit": float(card.transaction_limit),
        "message": f"Spending limit updated to ${new_limit:,.2f}.",
    }


@router.post("/investments/{investment_id}/liquidate")
async def liquidate_investment_endpoint(
    investment_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Sell/liquidate an active investment and credit its current value back to the user's primary account."""
    res = await db_session.execute(
        select(Investment).where(Investment.id == investment_id, Investment.user_id == current_user.id)
    )
    inv = res.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investment not found")
    if (inv.status or "").lower() in ("sold", "liquidated", "closed"):
        raise HTTPException(status_code=400, detail="This investment has already been liquidated.")

    payout = float(inv.current_value or inv.amount or 0)
    account = await _get_or_create_primary_account(db_session, current_user)
    account.balance = Decimal(str(round(float(account.balance or 0) + payout, 2)))
    inv.status = "liquidated"
    db_session.add(account)
    db_session.add(inv)

    ref_num = f"LIQ-{uuid.uuid4().hex[:10].upper()}"
    txn = Transaction(
        user_id=current_user.id,
        account_id=account.id,
        amount=Decimal(str(round(payout, 2))),
        transaction_type="investment_liquidation",
        direction="credit",
        status="completed",
        description=f"Liquidated {inv.purpose or inv.investment_type.title()} Investment #{inv.id}",
        reference_number=ref_num,
        kyc_status_at_time=current_user.kyc_status,
    )
    db_session.add(txn)
    await db_session.commit()

    return {
        "success": True,
        "investment_id": inv.id,
        "credited_amount": payout,
        "new_account_balance": float(account.balance),
        "reference_number": ref_num,
        "message": f"${payout:,.2f} credited to your primary account ({account.account_number}).",
    }


@router.get("/support-tickets")
async def list_support_tickets(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Return user's support tickets stored in UserSettings.preferences."""
    res = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = res.scalar_one_or_none()
    tickets = []
    if settings_row and settings_row.preferences:
        try:
            prefs = json.loads(settings_row.preferences)
            tickets = prefs.get("support_tickets", [])
        except Exception:
            tickets = []
    return tickets


@router.post("/support-tickets")
async def create_support_ticket(
    payload: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Create a priority support or transaction dispute ticket."""
    subject = (payload.get("subject") or "Account Inquiry").strip()
    category = (payload.get("category") or "general").strip()
    priority = (payload.get("priority") or "normal").strip()
    message = (payload.get("message") or "").strip()
    transaction_ref = (payload.get("transaction_ref") or "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="Please provide a message describing your request.")

    res = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_row = res.scalar_one_or_none()
    if settings_row is None:
        settings_row = UserSettings(user_id=current_user.id)
        db_session.add(settings_row)
    try:
        prefs = json.loads(settings_row.preferences) if settings_row.preferences else {}
    except Exception:
        prefs = {}

    tickets = prefs.get("support_tickets", [])
    ticket = {
        "id": f"TKT-{1000 + len(tickets) + 1}",
        "subject": subject,
        "category": category,
        "priority": priority,
        "message": message,
        "transaction_ref": transaction_ref,
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
    }
    tickets.insert(0, ticket)
    prefs["support_tickets"] = tickets
    settings_row.preferences = json.dumps(prefs)
    await db_session.commit()

    return {
        "success": True,
        "ticket": ticket,
        "message": f"Support ticket {ticket['id']} created. A private banking specialist will respond shortly.",
    }


@router.get("/statements/official")
async def get_official_bank_statement(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    days: str = Query("30"),
    account_id: Optional[int] = Query(None),
    format: str = Query("html"),
    autoprint: int = Query(1),
):
    """
    Generate a Certified Official Bank Statement (HTML printable PDF or JSON)
    with opening/closing balances, total credits/debits, and running balance ledger.
    """
    from fastapi.responses import HTMLResponse
    from models import Transaction
    import html as _html

    acct_res = await db_session.execute(
        select(Account).where(Account.owner_id == current_user.id).order_by(Account.id.asc())
    )
    accounts = acct_res.scalars().all()
    if not accounts:
        primary = await _get_or_create_primary_account(db_session, current_user)
        accounts = [primary]

    selected_accounts = [a for a in accounts if account_id is None or a.id == account_id] or accounts
    closing_balance = sum(float(a.balance or 0) for a in selected_accounts)
    primary_acc = selected_accounts[0]

    txn_stmt = select(Transaction).where(Transaction.user_id == current_user.id)
    if account_id is not None:
        txn_stmt = txn_stmt.where(Transaction.account_id == account_id)

    now = datetime.utcnow()
    period_label = "All-Time Statement"
    if days != "all":
        try:
            d_int = max(1, int(days))
            cutoff = now - timedelta(days=d_int)
            txn_stmt = txn_stmt.where(Transaction.created_at >= cutoff)
            period_label = f"Last {d_int} Days ({cutoff.strftime('%b %d, %Y')} – {now.strftime('%b %d, %Y')})"
        except ValueError:
            pass

    tx_res = await db_session.execute(txn_stmt.order_by(Transaction.created_at.desc()).limit(500))
    txns_desc = tx_res.scalars().all()

    def _is_credit(t: Transaction) -> bool:
        d = (t.direction or "").lower()
        tt = (t.transaction_type or "").lower()
        if d == "credit":
            return True
        if d == "debit":
            return False
        if tt in ("deposit", "credit", "transfer_received", "investment_liquidation"):
            return True
        return float(t.amount or 0) > 0 and tt not in ("withdrawal", "bill_pay", "debit", "loan_repayment")

    total_credits = 0.0
    total_debits = 0.0
    for t in txns_desc:
        amt = abs(float(t.amount or 0))
        if _is_credit(t):
            total_credits += amt
        else:
            total_debits += amt

    net_change = round(total_credits - total_debits, 2)
    opening_balance = round(closing_balance - net_change, 2)

    # Compute running balance chronologically
    running = opening_balance
    chronological_items = []
    for t in reversed(txns_desc):
        amt = abs(float(t.amount or 0))
        is_cr = _is_credit(t)
        running = round(running + (amt if is_cr else -amt), 2)
        chronological_items.append({
            "id": t.id,
            "date": (t.created_at or now).strftime("%Y-%m-%d %H:%M UTC"),
            "reference": t.reference_number or f"TXN-{t.id}",
            "description": t.description or "Ledger Transaction",
            "category": (t.transaction_type or "transfer").replace("_", " ").title(),
            "status": (t.status or "completed").upper(),
            "direction": "CREDIT" if is_cr else "DEBIT",
            "amount": amt,
            "signed_amount": amt if is_cr else -amt,
            "running_balance": running,
        })

    # Display newest first
    statement_rows = list(reversed(chronological_items))
    stmt_ref = f"STMT-{now.strftime('%Y%m%d')}-{current_user.id:04d}"

    if format.lower() == "json":
        return {
            "success": True,
            "statement_reference": stmt_ref,
            "generated_at": now.isoformat(),
            "period_label": period_label,
            "customer": {
                "full_name": current_user.full_name or current_user.email,
                "email": current_user.email,
                "account_number": primary_acc.account_number,
                "routing_number": "021000021",
                "swift_bic": "FNZAUS33XXX",
            },
            "summary": {
                "opening_balance": opening_balance,
                "total_credits": round(total_credits, 2),
                "total_debits": round(total_debits, 2),
                "net_change": net_change,
                "closing_balance": round(closing_balance, 2),
            },
            "transactions": statement_rows,
        }

    rows_html = ""
    if not statement_rows:
        rows_html = '<tr><td colspan="7" style="text-align:center;padding:28px;color:#64748b;">No posted transactions during this statement period.</td></tr>'
    else:
        for r in statement_rows:
            amt_color = "#059669" if r["direction"] == "CREDIT" else "#0f172a"
            sign = "+" if r["direction"] == "CREDIT" else "-"
            rows_html += f"""
            <tr>
                <td style="white-space:nowrap;">{_html.escape(r['date'])}</td>
                <td><code style="font-family:monospace;font-size:11px;">{_html.escape(r['reference'])}</code></td>
                <td><strong>{_html.escape(r['description'])}</strong></td>
                <td>{_html.escape(r['category'])}</td>
                <td><span style="font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px;background:#f1f5f9;color:#334155;">{_html.escape(r['status'])}</span></td>
                <td style="text-align:right;font-weight:700;color:{amt_color};">{sign}${r['amount']:,.2f}</td>
                <td style="text-align:right;font-family:monospace;color:#334155;">${r['running_balance']:,.2f}</td>
            </tr>
            """

    auto_print_script = "window.addEventListener('load', () => setTimeout(() => window.print(), 350));" if autoprint else ""
    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Finanza Bank Official Statement — {stmt_ref}</title>
<style>
    * {{ box-sizing: border-box; }}
    body {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: #0f172a;
        background: #f8fafc;
        margin: 0;
        padding: 24px;
    }}
    .toolbar {{
        max-width: 960px;
        margin: 0 auto 16px auto;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0f172a;
        color: #fff;
        padding: 12px 20px;
        border-radius: 10px;
    }}
    .toolbar button {{
        background: #2563eb;
        color: #fff;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        margin-left: 8px;
    }}
    .toolbar button.secondary {{ background: #334155; }}
    .sheet {{
        max-width: 960px;
        margin: 0 auto;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 40px;
        box-shadow: 0 10px 25px rgba(15,23,42,0.06);
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 2px solid #0f172a;
        padding-bottom: 20px;
        margin-bottom: 24px;
    }}
    .brand {{
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #0f172a;
    }}
    .brand-sub {{ font-size: 12px; color: #475569; margin-top: 4px; }}
    .meta-box {{ text-align: right; font-size: 12px; line-height: 1.6; color: #334155; }}
    .info-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 24px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        font-size: 13px;
    }}
    .summary-grid {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 12px;
        margin-bottom: 28px;
    }}
    .summary-card {{
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
        background: #fff;
    }}
    .summary-card .lbl {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 700; }}
    .summary-card .val {{ font-size: 16px; font-weight: 800; margin-top: 4px; color: #0f172a; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th {{
        text-align: left;
        padding: 10px 12px;
        background: #f1f5f9;
        border-bottom: 2px solid #cbd5e1;
        font-size: 11px;
        text-transform: uppercase;
        color: #475569;
    }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }}
    .footer {{
        margin-top: 32px;
        padding-top: 16px;
        border-top: 1px solid #cbd5e1;
        font-size: 11px;
        color: #64748b;
        display: flex;
        justify-content: space-between;
    }}
    @media print {{
        body {{ background: #fff; padding: 0; }}
        .toolbar {{ display: none !important; }}
        .sheet {{ border: none; box-shadow: none; padding: 16px; max-width: 100%; }}
    }}
</style>
</head>
<body>
    <div class="toolbar">
        <div><strong>Finanza Bank Certified Statement</strong> • {_html.escape(stmt_ref)}</div>
        <div>
            <button onclick="window.print()">Print / Save as PDF</button>
            <button class="secondary" onclick="window.close()">Close Window</button>
        </div>
    </div>
    <div class="sheet">
        <div class="header">
            <div>
                <div class="brand">FINANZA BANK, N.A.</div>
                <div class="brand-sub">Institutional & Private Banking Division • New York, NY 10001 • Member FDIC</div>
            </div>
            <div class="meta-box">
                <div><strong>OFFICIAL STATEMENT OF ACCOUNT</strong></div>
                <div>Statement Ref: <strong>{_html.escape(stmt_ref)}</strong></div>
                <div>Period: <strong>{_html.escape(period_label)}</strong></div>
                <div>Generated: {_html.escape(now.strftime('%b %d, %Y %H:%M UTC'))}</div>
            </div>
        </div>

        <div class="info-grid">
            <div>
                <div style="font-size:11px;text-transform:uppercase;color:#64748b;font-weight:700;margin-bottom:4px;">Account Holder</div>
                <div><strong>{_html.escape(current_user.full_name or 'Valued Client')}</strong></div>
                <div>{_html.escape(current_user.email)}</div>
                <div>KYC Verification Status: <strong>{_html.escape((current_user.kyc_status or 'approved').upper())}</strong></div>
            </div>
            <div>
                <div style="font-size:11px;text-transform:uppercase;color:#64748b;font-weight:700;margin-bottom:4px;">Depository Coordinates</div>
                <div>Primary Account Number: <strong>{_html.escape(primary_acc.account_number)}</strong> ({_html.escape(primary_acc.currency or 'USD')})</div>
                <div>ABA Routing Number: <strong>021000021</strong></div>
                <div>SWIFT / BIC Code: <strong>FNZAUS33XXX</strong></div>
            </div>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <div class="lbl">Opening Balance</div>
                <div class="val">${opening_balance:,.2f}</div>
            </div>
            <div class="summary-card">
                <div class="lbl">Total Credits (+)</div>
                <div class="val" style="color:#059669;">+${total_credits:,.2f}</div>
            </div>
            <div class="summary-card">
                <div class="lbl">Total Debits (-)</div>
                <div class="val" style="color:#dc2626;">-${total_debits:,.2f}</div>
            </div>
            <div class="summary-card">
                <div class="lbl">Net Period Change</div>
                <div class="val">{'+' if net_change >= 0 else ''}${net_change:,.2f}</div>
            </div>
            <div class="summary-card" style="background:#eff6ff;border-color:#bfdbfe;">
                <div class="lbl" style="color:#1d4ed8;">Closing Balance</div>
                <div class="val" style="color:#1e40af;">${closing_balance:,.2f}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Date (UTC)</th>
                    <th>Reference #</th>
                    <th>Description</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th style="text-align:right;">Amount</th>
                    <th style="text-align:right;">Running Balance</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            <div>Finanza Bank, N.A. • Certified Electronic Statement • Member FDIC • Equal Housing Lender</div>
            <div>Page 1 of 1 • Verification Hash: {stmt_ref}</div>
        </div>
    </div>
    <script>{auto_print_script}</script>
</body>
</html>"""
    return HTMLResponse(content=html_doc)


# ============================================================================
# USER NOTIFICATIONS (Standard Banking Alerts - Persisted in Database)
# ============================================================================

@router.get("/notifications")
async def get_user_notifications_endpoint(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 50,
):
    """
    Get user's real persistent banking notifications.
    If user has zero notifications in DB, generates baseline real alerts from account & history.
    """
    result = await db_session.execute(
        select(DBNotification)
        .where(DBNotification.user_id == current_user.id)
        .order_by(DBNotification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    notifications = result.scalars().all()
    if notifications:
        return [
            {
                "id": n.id,
                "user_id": n.user_id,
                "title": n.title,
                "message": n.message,
                "notification_type": n.notification_type or "alert",
                "is_read": bool(n.is_read),
                "created_at": n.created_at.isoformat() if n.created_at else datetime.utcnow().isoformat()
            }
            for n in notifications
        ]

    # Generate initial real baseline alerts if user has 0 notifications
    created = []
    now = datetime.utcnow()

    # 1. Welcome & Security Notice
    notif_welcome = DBNotification(
        user_id=current_user.id,
        title="Welcome to Finanza Online Banking",
        message="Your banking profile is established with multi-layered encryption. 24/7 transaction monitoring is active.",
        notification_type="security",
        is_read=False,
        created_at=current_user.created_at or now
    )
    db_session.add(notif_welcome)
    created.append(notif_welcome)

    # 2. Account Alert
    accts_res = await db_session.execute(
        select(Account).where(Account.owner_id == current_user.id)
    )
    for acct in accts_res.scalars().all():
        acct_notif = DBNotification(
            user_id=current_user.id,
            title=f"{acct.account_type.capitalize()} Account #{acct.account_number} Active",
            message=f"Your {acct.account_type} account (#{acct.account_number}) is ready with currency {acct.currency}.",
            notification_type="alert",
            is_read=False,
            created_at=acct.created_at or now
        )
        db_session.add(acct_notif)
        created.append(acct_notif)

    # 3. KYC Status Notice
    kyc_st = getattr(current_user, 'kyc_status', 'not_started')
    if kyc_st and kyc_st != 'not_started':
        title = "KYC Verification Approved" if kyc_st == "approved" else f"KYC Status: {kyc_st.capitalize()}"
        msg = "Your identity verification documents have been approved. All higher transaction limits are unlocked." if kyc_st == "approved" else f"Your identity verification is currently {kyc_st}."
        kyc_notif = DBNotification(
            user_id=current_user.id,
            title=title,
            message=msg,
            notification_type="kyc",
            is_read=False,
            created_at=now
        )
        db_session.add(kyc_notif)
        created.append(kyc_notif)

    # 4. Recent Transactions
    tx_res = await db_session.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(5)
    )
    for tx in tx_res.scalars().all():
        direction_label = "Credit" if tx.direction == "credit" else "Debit"
        tx_notif = DBNotification(
            user_id=current_user.id,
            title=f"Transaction: {tx.transaction_type.capitalize()}",
            message=f"{direction_label} of ${float(tx.amount):,.2f} ({tx.status.capitalize()}). Ref: {tx.reference_number or tx.id}",
            notification_type="transaction",
            is_read=False,
            created_at=tx.created_at or now
        )
        db_session.add(tx_notif)
        created.append(tx_notif)

    try:
        await db_session.commit()
        for item in created:
            await db_session.refresh(item)
    except Exception:
        await db_session.rollback()
        return []

    return [
        {
            "id": n.id,
            "user_id": n.user_id,
            "title": n.title,
            "message": n.message,
            "notification_type": n.notification_type or "alert",
            "is_read": bool(n.is_read),
            "created_at": n.created_at.isoformat() if n.created_at else now.isoformat()
        }
        for n in sorted(created, key=lambda x: x.created_at or now, reverse=True)
    ]


@router.post("/notifications/{notification_id}/read")
async def mark_user_notification_read_api(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read in the database."""
    res = await db_session.execute(
        select(DBNotification).where(
            DBNotification.id == notification_id,
            DBNotification.user_id == current_user.id
        )
    )
    notif = res.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = True
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)
    return {"success": True, "id": notif.id, "is_read": True}


@router.delete("/notifications")
async def clear_all_notifications_endpoint(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Clear all notifications for the authenticated user from the database."""
    await db_session.execute(
        delete(DBNotification).where(DBNotification.user_id == current_user.id)
    )
    await db_session.commit()
    return {"success": True, "message": "All notifications cleared"}


@router.delete("/notifications/{notification_id}")
async def delete_single_notification_endpoint(
    notification_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Delete a single notification from the database."""
    res = await db_session.execute(
        select(DBNotification).where(
            DBNotification.id == notification_id,
            DBNotification.user_id == current_user.id
        )
    )
    notif = res.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await db_session.delete(notif)
    await db_session.commit()
    return {"success": True, "id": notification_id}


@router.get("/notifications/unread-count")
@router.get("/notifications/unread/count")
async def get_user_notifications_unread_count(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications for navbar bell icon."""
    res = await db_session.execute(
        select(func.count(DBNotification.id)).where(
            DBNotification.user_id == current_user.id,
            DBNotification.is_read == False
        )
    )
    count = res.scalar() or 0
    return {"unread_count": count}


# ============================================================================
# USER KYC SUBMISSIONS (/api/user/kyc-submissions)
# ============================================================================

@router.get("/kyc-submissions")
async def get_user_kyc_submissions(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Get user's identity verification (KYC) submissions history.
    Returns real database records from KYCInfo.
    """
    res = await db_session.execute(
        select(KYCInfo).where(KYCInfo.user_id == current_user.id).order_by(KYCInfo.submitted_at.desc())
    )
    records = res.scalars().all()
    if not records:
        if getattr(current_user, 'kyc_status', None) == 'approved' or getattr(current_user, 'is_verified', False):
            return [{
                "id": 1,
                "user_id": current_user.id,
                "document_type": "Government Photo ID",
                "document_number": getattr(current_user, 'account_number', 'VERIFIED'),
                "status": "approved",
                "submitted_at": current_user.created_at.isoformat() if current_user.created_at else datetime.utcnow().isoformat(),
                "approved_at": datetime.utcnow().isoformat(),
            }]
        return []

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "document_type": r.document_type or "Government ID",
            "document_number": r.document_number or "",
            "status": r.status or "pending",
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else datetime.utcnow().isoformat(),
            "approved_at": r.approved_at.isoformat() if r.approved_at else None,
            "id_front_uploaded": bool(r.id_front_uploaded),
            "id_back_uploaded": bool(r.id_back_uploaded),
            "proof_of_address_uploaded": bool(r.proof_of_address_uploaded),
        }
        for r in records
    ]


# ============================================================================
# USER SETTINGS (/api/user/settings)
# ============================================================================

@router.get("/settings")
async def get_user_settings_endpoint(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's security & notification settings.
    """
    res = await db_session.execute(
        select(UserSettings).where(UserSettings.user_id == current_user.id)
    )
    settings_obj = res.scalars().first()
    two_factor = bool(
        getattr(current_user, 'mfa_enabled', False) or
        (settings_obj and settings_obj.two_factor_enabled)
    )
    return {
        "user_id": current_user.id,
        "two_factor_enabled": two_factor,
        "email_notifications": settings_obj.email_notifications if settings_obj else True,
        "sms_notifications": settings_obj.sms_notifications if settings_obj else False,
        "phone_number": getattr(current_user, 'phone_number', None) or (settings_obj.phone_number if settings_obj else None),
        "address": getattr(current_user, 'address', None) or (settings_obj.address if settings_obj else None),
    }
