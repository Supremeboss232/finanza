from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from auth_utils import create_access_token
from deps import CurrentUserDep, CurrentAdminUserDep, SessionDep, validate_password_length
from schemas import User as PydanticUser, UserCreate
from crud import get_user, get_users, create_user, get_user_by_username
from typing import Annotated
from balance_service_ledger import BalanceServiceLedger

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.post("/", response_model=PydanticUser, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user: UserCreate,
    db_session: SessionDep,
    validated_password: str = Depends(validate_password_length) # Add password validation
):
    db_user = await get_user_by_username(db_session, username=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    new_user = await create_user(db=db_session, user=user)
    # Return the created user object directly to match the response_model
    return new_user

@users_router.get("/me/stats")
async def read_user_stats(current_user: CurrentUserDep, db_session: SessionDep):
    """Returns user-specific statistics: balance, investments, loans, transactions."""
    from crud import get_user_deposits, get_user_investments, get_user_loans, get_user_transactions
    
    deposits = await get_user_deposits(db_session, current_user.id, limit=100)
    investments = await get_user_investments(db_session, current_user.id, limit=100)
    loans = await get_user_loans(db_session, current_user.id, limit=100)
    transactions = await get_user_transactions(db_session, current_user.id, limit=50)
    
    total_balance = sum(d.amount for d in deposits if d.amount) if deposits else 0
    total_investments = sum(i.amount for i in investments if i.amount) if investments else 0
    total_loans = sum(l.amount for l in loans if l.amount) if loans else 0
    
    return {
        "user": current_user,
        "balance": total_balance,
        "investments": total_investments,
        "loans": total_loans,
        "recent_transactions": transactions[:10],
        "deposits_count": len(deposits),
        "investments_count": len(investments),
        "loans_count": len(loans),
        "is_verified": getattr(current_user, "is_verified", False),
        "account_number": getattr(current_user, "account_number", None)
    }

@users_router.get("/me/dashboard-data")
async def get_user_dashboard_data(current_user: CurrentUserDep, db_session: SessionDep):
    """
    Get user dashboard data with corrected balance calculations.
    
    THIS IS THE SINGLE SOURCE OF TRUTH FOR USER BALANCES.
    All balance values are calculated from completed transactions, NOT stored account.balance.
    
    Returns:
    {
        "user_id": int,
        "email": str,
        "full_name": str,
        "total_balance": float (sum of all completed transactions),
        "total_deposits": float (sum of deposit transactions),
        "total_withdrawals": float (sum of withdrawal transactions),
        "total_transfers": float (sum of transfers received),
        "transaction_count": int (number of completed transactions),
        "breakdown": {
            "deposits": float,
            "withdrawals": float,
            "transfers": float,
            "balance": float
        }
    }
    """
    try:
        # ISSUE #1 FIX: Use BalanceServiceLedger (source of truth)
        breakdown = await BalanceServiceLedger.get_user_transaction_breakdown(db_session, current_user.id)
        
        return {
            "user_id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "total_balance": float(breakdown['total_balance']),
            "total_deposits": float(breakdown['total_deposits']),
            "total_withdrawals": float(breakdown['total_withdrawals']),
            "total_transfers": float(breakdown['total_transfers']),
            "transaction_count": breakdown['transaction_count'],
            "breakdown": {
                "deposits": float(breakdown['total_deposits']),
                "withdrawals": float(breakdown['total_withdrawals']),
                "transfers": float(breakdown['total_transfers']),
                "balance": float(breakdown['total_balance'])
            },
            "is_verified": getattr(current_user, "is_verified", False),
            "is_active": getattr(current_user, "is_active", True),
            "kyc_status": getattr(current_user, "kyc_status", "not_started")
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard data: {str(e)}")

@users_router.get("/me/balance")
async def get_user_balance(current_user: CurrentUserDep, db_session: SessionDep):
    """
    Get user's current balance (calculated from transactions).
    
    THIS IS THE AUTHORITATIVE BALANCE - computed from transaction sum.
    Never uses the stored account.balance value.
    
    Returns:
    {
        "user_id": int,
        "balance": float (sum of all completed transactions for this user),
        "currency": str
    }
    """
    try:
        # ISSUE #1 FIX: Use BalanceServiceLedger (source of truth)
        balance = await BalanceServiceLedger.get_user_balance(db_session, current_user.id)
        return {
            "user_id": current_user.id,
            "balance": balance,
            "currency": "USD"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating balance: {str(e)}")

@users_router.get("/me/deposits-total")
async def get_user_deposits_total(current_user: CurrentUserDep, db_session: SessionDep):
    """
    Get user's total deposit amount (sum of all completed deposit transactions).
    
    Returns:
    {
        "user_id": int,
        "total_deposits": float,
        "currency": str
    }
    """
    try:
        # ISSUE #1 FIX: Use BalanceServiceLedger (source of truth)
        total = await BalanceServiceLedger.get_user_deposit_total(db_session, current_user.id)
        return {
            "user_id": current_user.id,
            "total_deposits": total,
            "currency": "USD"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating deposits: {str(e)}")

# Generic routes must come last to avoid shadowing specific /me/* routes
@users_router.get("/me/", response_model=PydanticUser)
async def read_users_me(current_user: CurrentUserDep):
    return current_user

@users_router.get("/{user_id}", response_model=PydanticUser)
async def read_user(user_id: int, db_session: SessionDep, current_user: CurrentUserDep):
    """
    Get a user's profile by ID.
    
    SECURITY: 
    - Requires authentication
    - Users can only view their own profile
    - Admins can view any user's profile
    """
    # Admins can view any user
    if current_user.is_admin:
        db_user = await get_user(db_session, user_id)
        if db_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return db_user
    
    # Regular users can only view their own profile
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You are not authorized to view this user's profile"
        )
    
    return current_user

@users_router.get("/", response_model=List[PydanticUser])
async def read_all_users(
    db_session: SessionDep, 
    current_user: CurrentAdminUserDep,
    skip: int = 0, 
    limit: int = 100
):
    """
    List all users.
    
    SECURITY:
    - Admin-only endpoint
    - Requires get_current_admin_user dependency
    - Returns list of all users in the system
    """
    users = await get_users(db_session, skip=skip, limit=limit)
    return users
