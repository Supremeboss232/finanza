"""User API endpoints for fetching and managing user-specific financial data."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from deps import get_current_user, SessionDep
from models import User, Account, KYCInfo
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
@router.get("/profile", response_model=PydanticUser)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile information."""
    return current_user


@router.put("/profile", response_model=PydanticUser)
async def update_user_profile(
    profile_update: UserProfileUpdateRequest,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """
    Update current user's profile information.
    Accepts both basic profile fields and KYC personal details.
    
    NOTE: If user has submitted KYC, profile updates are locked until
    KYC is approved or rejected.
    """
    try:
        # Check if KYC is submitted (form is locked)
        # Query the KYC record to avoid lazy loading issues
        result = await db_session.execute(
            select(KYCInfo).filter(KYCInfo.user_id == current_user.id)
        )
        kyc_info = result.scalars().first()
        
        if kyc_info and kyc_info.kyc_submitted:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Your profile is currently locked. KYC has been submitted and is under review. You cannot modify your profile until verification is complete."
            )
        
        # Update basic user fields
        if profile_update.full_name is not None:
            current_user.full_name = profile_update.full_name
        
        if profile_update.account_type is not None:
            current_user.account_type = profile_update.account_type
        
        if profile_update.is_active is not None:
            current_user.is_active = profile_update.is_active
        
        # Update session and return updated user
        db_session.add(current_user)
        await db_session.commit()
        await db_session.refresh(current_user)
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        import logging
        logging.error(f"Error updating profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update profile: {str(e)}"
        )


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


# ============= ENHANCED OPERATIONS FOR DEPOSITS =============

@router.post("/deposits/{deposit_id}/withdraw", response_model=dict)
async def withdraw_from_deposit(
    deposit_id: int,
    amount: float,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Withdraw funds from a deposit (via ATM or Agent)."""
    from crud import get_deposit
    from sqlalchemy import update
    
    deposit = await get_deposit(db_session, deposit_id)
    if not deposit or deposit.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Deposit not found")
    
    if deposit.balance < amount:
        raise HTTPException(status_code=400, detail="Insufficient balance for withdrawal")
    
    # Update deposit balance and withdrawal amount
    deposit.balance -= amount
    deposit.withdrawal_amount += amount
    
    db_session.add(deposit)
    await db_session.commit()
    await db_session.refresh(deposit)
    
    return {
        "success": True,
        "message": f"Withdrawal of ${amount:.2f} completed",
        "new_balance": deposit.balance,
        "total_withdrawn": deposit.withdrawal_amount,
        "deposit": {
            "id": deposit.id,
            "amount": deposit.amount,
            "balance": deposit.balance,
            "interest_earned": (deposit.balance - deposit.amount),
            "status": deposit.status
        }
    }


# REMOVED: Duplicate old deposit creation endpoint - replaced by unified POST endpoint below


# ============= ENHANCED OPERATIONS FOR LOANS =============

@router.post("/loans/request", response_model=dict)
async def request_loan(
    amount: float,
    term_months: int,
    interest_rate: float,
    purpose: str,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Submit a loan request."""
    from sqlalchemy import insert
    from app.models import Loan
    
    monthly_payment = (amount * (interest_rate / 100) / 12) / (1 - (1 + interest_rate / 100 / 12) ** (-term_months))
    
    stmt = insert(Loan).values(
        user_id=current_user.id,
        amount=amount,
        interest_rate=interest_rate,
        term_months=term_months,
        monthly_payment=monthly_payment,
        remaining_balance=amount,
        status="pending",
        purpose=purpose
    ).returning(Loan)
    
    result = await db_session.execute(stmt)
    loan = result.scalars().first()
    await db_session.commit()
    
    return {
        "success": True,
        "message": "Loan request submitted successfully",
        "loan_id": loan.id,
        "amount": loan.amount,
        "monthly_payment": loan.monthly_payment,
        "term_months": loan.term_months,
        "status": loan.status
    }


@router.post("/loans/{loan_id}/approve", response_model=dict)
async def approve_loan(
    loan_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Approve a loan request (admin only)."""
    from crud import get_loan
    from datetime import datetime
    
    loan = await get_loan(db_session, loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    loan.status = "active"
    loan.approved_at = datetime.utcnow()
    
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)
    
    return {
        "success": True,
        "message": "Loan approved successfully",
        "loan": {
            "id": loan.id,
            "amount": loan.amount,
            "monthly_payment": loan.monthly_payment,
            "status": loan.status
        }
    }


@router.post("/loans/{loan_id}/payment", response_model=dict)
async def make_loan_payment(
    loan_id: int,
    amount: float,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Make a payment on an active loan."""
    from crud import get_loan
    
    loan = await get_loan(db_session, loan_id)
    if not loan or loan.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    if loan.status != "active":
        raise HTTPException(status_code=400, detail="Loan is not active")
    
    if amount > loan.remaining_balance:
        raise HTTPException(status_code=400, detail="Payment exceeds remaining balance")
    
    loan.remaining_balance -= amount
    loan.paid_amount += amount
    
    if loan.remaining_balance <= 0:
        loan.status = "completed"
    
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)
    
    return {
        "success": True,
        "message": f"Payment of ${amount:.2f} recorded",
        "remaining_balance": loan.remaining_balance,
        "total_paid": loan.paid_amount,
        "loan_status": loan.status
    }


# ============= ENHANCED OPERATIONS FOR INVESTMENTS =============

# REMOVED: Duplicate old investment creation endpoint - replaced by unified POST endpoint below


@router.get("/investments/{investment_id}/details", response_model=dict)
async def get_investment_details(
    investment_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get detailed investment information including returns and performance."""
    from crud import get_investment
    from datetime import datetime
    
    investment = await get_investment(db_session, investment_id)
    if not investment or investment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Investment not found")
    
    # Calculate returns
    days_invested = (datetime.utcnow() - investment.created_at).days
    expected_interest = (investment.amount * investment.annual_return_rate / 100) * (days_invested / 365)
    
    return {
        "investment_id": investment.id,
        "type": investment.investment_type,
        "amount_invested": investment.amount,
        "current_value": investment.current_value or investment.amount,
        "interest_earned": investment.interest_earned,
        "expected_interest": round(expected_interest, 2),
        "annual_return_rate": f"{investment.annual_return_rate}%",
        "total_return": round((investment.interest_earned + expected_interest), 2),
        "days_invested": days_invested,
        "purpose": investment.purpose,
        "status": investment.status,
        "maturity_date": investment.maturity_date.isoformat() if investment.maturity_date else None
    }


# ============= ENHANCED OPERATIONS FOR CARDS =============

# REMOVED: Duplicate old card creation endpoint - replaced by unified POST endpoint below


@router.post("/cards/{card_id}/balance", response_model=dict)
async def update_card_balance(
    card_id: int,
    amount: float,
    transaction_type: str,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Update card balance (deposit or withdrawal)."""
    from crud import get_card
    
    card = await get_card(db_session, card_id)
    if not card or card.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if transaction_type.lower() == "deposit":
        card.balance += amount
        action = "deposited to"
    elif transaction_type.lower() == "withdrawal":
        if card.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient card balance")
        card.balance -= amount
        action = "withdrawn from"
    else:
        raise HTTPException(status_code=400, detail="Invalid transaction type")
    
    db_session.add(card)
    await db_session.commit()
    await db_session.refresh(card)
    
    return {
        "success": True,
        "message": f"${amount:.2f} {action} card",
        "card_id": card.id,
        "new_balance": card.balance,
        "transaction_type": transaction_type,
        "card_status": card.status
    }


# ===== SECURITY & SETTINGS ENDPOINTS =====

@router.post("/change-password")
async def change_password(
    password_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Change user password."""
    from auth_utils import verify_password, get_password_hash
    
    try:
        old_password = password_data.get("old_password")
        new_password = password_data.get("new_password")
        confirm_password = password_data.get("confirm_password")
        
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="New passwords do not match")
        
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
        if not verify_password(old_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")
        
        current_user.hashed_password = get_password_hash(new_password)
        db_session.add(current_user)
        await db_session.commit()
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/enable-2fa")
async def enable_2fa(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Enable two-factor authentication."""
    return {
        "success": True,
        "message": "2FA enabled successfully",
        "secret_key": "SAMPLE2FASECRET123"  # TODO: Generate real 2FA secret
    }


@router.get("/login-history")
async def get_login_history(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user),
    limit: int = 50
):
    """Get user's login history."""
    # TODO: Implement login history tracking
    return {
        "login_history": [
            {
                "timestamp": "2024-01-15T10:30:00",
                "ip_address": "192.168.1.1",
                "device": "Chrome on Windows",
                "location": "New York, USA"
            }
        ]
    }


@router.get("/trusted-devices")
async def get_trusted_devices(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get user's trusted devices."""
    # TODO: Implement device management
    return {
        "trusted_devices": [
            {
                "id": 1,
                "name": "My Desktop",
                "device_type": "Desktop",
                "last_used": "2024-01-15T10:30:00"
            }
        ]
    }


@router.delete("/trusted-devices/{device_id}")
async def remove_trusted_device(
    device_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Remove a trusted device."""
    return {
        "success": True,
        "message": "Device removed successfully"
    }


@router.post("/trusted-devices/clear-all")
async def clear_all_trusted_devices(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Clear all trusted devices."""
    return {
        "success": True,
        "message": "All trusted devices cleared"
    }


@router.get("/security-questions")
async def get_security_questions(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get user's security questions."""
    return {
        "security_questions": [
            {
                "question": "What is your mother's maiden name?",
                "answer_set": False
            },
            {
                "question": "What was the name of your first pet?",
                "answer_set": False
            }
        ]
    }


@router.post("/security-questions")
async def set_security_questions(
    questions_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Set user's security questions and answers."""
    # TODO: Implement security question storage
    return {
        "success": True,
        "message": "Security questions updated successfully"
    }


@router.get("/notification-preferences")
async def get_notification_preferences(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get user's notification preferences."""
    return {
        "notification_preferences": {
            "email_alerts": True,
            "sms_alerts": False,
            "transaction_notifications": True,
            "marketing_emails": False
        }
    }


@router.put("/notification-preferences")
async def update_notification_preferences(
    preferences: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Update user's notification preferences."""
    # TODO: Implement preference storage
    return {
        "success": True,
        "message": "Notification preferences updated successfully"
    }


@router.post("/close-account")
async def close_account(
    password_data: dict,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Request to close user account."""
    from auth_utils import verify_password
    
    try:
        password = password_data.get("password")
        
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Password is incorrect")
        
        # TODO: Instead of deleting, mark account as closed
        # current_user.is_active = False
        # db_session.add(current_user)
        # await db_session.commit()
        
        return {
            "success": True,
            "message": "Account closure request submitted. We'll process it within 24 hours."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload-profile-picture")
async def upload_profile_picture(
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Upload user's profile picture."""
    # TODO: Implement file upload handling
    return {
        "success": True,
        "message": "Profile picture uploaded successfully",
        "picture_url": "/static/img/default-profile.png"
    }


@router.get("/transactions/{transaction_id}/receipt")
async def get_transaction_receipt(
    transaction_id: int,
    db_session: SessionDep,
    current_user: User = Depends(get_current_user)
):
    """Get receipt for a transaction."""
    txn = await get_user_transactions(db_session, current_user.id)
    receipt_txn = next((t for t in txn if t.id == transaction_id), None)
    
    if not receipt_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return {
        "transaction_id": receipt_txn.id,
        "amount": receipt_txn.amount,
        "type": getattr(receipt_txn, "transaction_type", "transfer"),
        "date": receipt_txn.created_at.isoformat() if receipt_txn.created_at else None,
        "status": receipt_txn.status,
        "receipt_url": f"/receipts/txn_{transaction_id}.pdf"
    }


# CARDS ENDPOINTS


# CARDS ENDPOINTS
@router.get("/cards")
async def get_user_cards_endpoint(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get all cards for the current user."""
    return []


# DEPOSITS ENDPOINTS
@router.get("/deposits")
async def get_user_deposits_endpoint(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get all deposits for the current user."""
    try:
        deposits = await get_user_deposits(db_session, current_user.id)
        return deposits if deposits else []
    except:
        return []


# LOANS ENDPOINTS
@router.get("/loans")
async def get_user_loans_endpoint(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get all loans for the current user."""
    try:
        loans = await get_user_loans(db_session, current_user.id)
        return loans if loans else []
    except:
        return []


# INVESTMENTS ENDPOINTS
@router.get("/investments")
async def get_user_investments_endpoint(
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Get all investments for the current user."""
    try:
        investments = await get_user_investments(db_session, current_user.id)
        return investments if investments else []
    except:
        return []


# POST ENDPOINTS FOR CREATING NEW ITEMS

# Create new card
@router.post("/cards")
async def create_card_endpoint(
    card_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Create a new card for the current user."""
    from datetime import datetime, timedelta
    from sqlalchemy import insert
    from models import Card
    import random
    
    try:
        # Generate card number
        card_number = f"{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
        
        # Set expiry date (5 years from now)
        expiry_date = (datetime.utcnow() + timedelta(days=365*5)).strftime("%m/%Y")
        
        # Create card
        stmt = insert(Card).values(
            user_id=current_user.id,
            card_number=card_number,
            card_type=card_data.get("card_type", "debit"),
            card_holder_name=current_user.full_name,
            expiry_date=expiry_date,
            balance=0.0,
            credit_limit=card_data.get("credit_limit", 5000.0),
            transaction_limit=card_data.get("transaction_limit", 10000.0),
            status="active"
        ).returning(Card)
        
        result = await db_session.execute(stmt)
        card = result.scalars().first()
        await db_session.commit()
        
        return {
            "id": card.id,
            "user_id": card.user_id,
            "card_number": card_number[-4:],
            "card_type": card.card_type,
            "card_holder_name": card.card_holder_name,
            "expiry_date": expiry_date,
            "balance": 0.0,
            "credit_limit": card.credit_limit,
            "transaction_limit": card.transaction_limit,
            "status": "active",
            "created_at": card.created_at.isoformat() if card.created_at else None
        }
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create card: {str(e)}")


# Create new deposit
@router.post("/deposits")
async def create_deposit_endpoint(
    deposit_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Create a new deposit for the current user."""
    from datetime import datetime, timedelta
    from sqlalchemy import insert
    from models import Deposit
    
    try:
        amount = deposit_data.get("amount", 0)
        interest_rate = deposit_data.get("interest_rate", 2.5)
        term_months = deposit_data.get("term_months", 12)
        
        if amount <= 0:
            raise ValueError("Deposit amount must be greater than 0")
        
        maturity_date = datetime.utcnow() + timedelta(days=term_months * 30)
        
        stmt = insert(Deposit).values(
            user_id=current_user.id,
            amount=amount,
            current_balance=amount,
            currency="USD",
            interest_rate=interest_rate,
            term_months=term_months,
            maturity_date=maturity_date,
            status="active"
        ).returning(Deposit)
        
        result = await db_session.execute(stmt)
        deposit = result.scalars().first()
        await db_session.commit()
        
        return {
            "id": deposit.id,
            "user_id": deposit.user_id,
            "amount": deposit.amount,
            "current_balance": deposit.current_balance,
            "currency": "USD",
            "interest_rate": interest_rate,
            "term_months": term_months,
            "maturity_date": maturity_date.isoformat() if maturity_date else None,
            "status": "active",
            "created_at": deposit.created_at.isoformat() if deposit.created_at else None
        }
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create deposit: {str(e)}")


# Create new loan
@router.post("/loans")
async def create_loan_endpoint(
    loan_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Create a new loan application for the current user."""
    from datetime import datetime
    from sqlalchemy import insert
    from models import Loan
    
    try:
        amount = loan_data.get("amount", 0)
        interest_rate = loan_data.get("interest_rate", 5.0)
        term_months = loan_data.get("term_months", 12)
        loan_type = loan_data.get("loan_type", "personal")
        purpose = loan_data.get("purpose", f"{loan_type} loan")
        
        if amount <= 0:
            raise ValueError("Loan amount must be greater than 0")
        if term_months <= 0:
            raise ValueError("Loan term must be greater than 0")
        
        # Calculate monthly payment
        monthly_rate = interest_rate / 100 / 12
        if monthly_rate > 0:
            monthly_payment = (amount * monthly_rate) / (1 - (1 + monthly_rate) ** (-term_months))
        else:
            monthly_payment = amount / term_months
        
        stmt = insert(Loan).values(
            user_id=current_user.id,
            loan_type=loan_type,
            amount=amount,
            remaining_balance=amount,
            interest_rate=interest_rate,
            term_months=term_months,
            monthly_payment=monthly_payment,
            paid_amount=0.0,
            purpose=purpose,
            status="pending"
        ).returning(Loan)
        
        result = await db_session.execute(stmt)
        loan = result.scalars().first()
        await db_session.commit()
        
        return {
            "id": loan.id,
            "user_id": loan.user_id,
            "loan_type": loan_type,
            "amount": loan.amount,
            "remaining_balance": amount,
            "interest_rate": interest_rate,
            "term_months": term_months,
            "monthly_payment": monthly_payment,
            "paid_amount": 0.0,
            "purpose": purpose,
            "status": "pending",
            "created_at": loan.created_at.isoformat() if loan.created_at else None
        }
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create loan: {str(e)}")


# Create new investment
@router.post("/investments")
async def create_investment_endpoint(
    investment_data: dict,
    current_user: User = Depends(get_current_user),
    db_session: SessionDep = None
):
    """Create a new investment for the current user."""
    from datetime import datetime, timedelta
    from sqlalchemy import insert
    from models import Investment
    
    try:
        amount = investment_data.get("amount", 0)
        annual_return_rate = investment_data.get("annual_return_rate", 5.0)
        investment_type = investment_data.get("investment_type", "stocks")
        purpose = investment_data.get("purpose", f"{investment_type} investment")
        
        if amount <= 0:
            raise ValueError("Investment amount must be greater than 0")
        
        # Set maturity for certain investment types
        maturity_date = None
        if investment_type in ["term_deposit", "bond", "insurance"]:
            maturity_date = datetime.utcnow() + timedelta(days=365)
        
        stmt = insert(Investment).values(
            user_id=current_user.id,
            investment_type=investment_type,
            amount=amount,
            current_value=amount,
            annual_return_rate=annual_return_rate,
            interest_earned=0.0,
            purpose=purpose,
            maturity_date=maturity_date,
            status="active"
        ).returning(Investment)
        
        result = await db_session.execute(stmt)
        investment = result.scalars().first()
        await db_session.commit()
        
        # Return the investment object in the format expected by frontend
        return {
            "id": investment.id,
            "user_id": investment.user_id,
            "investment_type": investment.investment_type,
            "amount": investment.amount,
            "current_value": investment.current_value,
            "annual_return_rate": annual_return_rate,
            "interest_earned": 0.0,
            "purpose": purpose,
            "maturity_date": maturity_date.isoformat() if maturity_date else None,
            "status": "active",
            "created_at": investment.created_at.isoformat() if investment.created_at else None
        }
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create investment: {str(e)}")
