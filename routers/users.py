from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from auth_utils import create_access_token
from deps import CurrentUserDep, CurrentAdminUserDep, SessionDep, validate_password_length
from schemas import User as PydanticUser, UserCreate
from crud import get_user, get_users, create_user, get_user_by_username
from balance_service_ledger import BalanceServiceLedger
from rbac import require_permission
from models import User as DBUser, Account as DBAccount

users_router = APIRouter(prefix="/api/v1/users", tags=["users"])


@users_router.post("/", response_model=PydanticUser, status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user: UserCreate,
    db_session: SessionDep,
    validated_password: str = Depends(validate_password_length)
):
    db_user = await get_user_by_username(db_session, username=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    new_user = await create_user(db=db_session, user=user)
    return new_user


@users_router.get("/search")
async def search_users_v1(
    db_session: SessionDep,
    current_admin: CurrentAdminUserDep,
    q: str = "",
    limit: int = 15
):
    """Search users by email, full_name, or account_number (used by Admin Fund & Search consoles)."""
    stmt = select(DBUser)
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.filter(
            or_(
                DBUser.email.ilike(term),
                DBUser.full_name.ilike(term),
                DBUser.account_number.ilike(term)
            )
        )
    res = await db_session.execute(stmt.limit(limit))
    users = res.scalars().all()
    items = []
    for u in users:
        bal = await BalanceServiceLedger.get_user_balance(db_session, u.id)
        acc_res = await db_session.execute(select(DBAccount).filter(DBAccount.owner_id == u.id))
        acc = acc_res.scalars().first()
        items.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name or u.email,
            "account_number": (acc.account_number if acc else u.account_number) or f"ACC-{u.id}",
            "balance": bal,
            "is_active": u.is_active,
            "kyc_status": getattr(u, "kyc_status", "pending")
        })
    return {"users": items, "data": items, "total": len(items)}


@users_router.get("/me/stats")
async def read_user_stats(current_user: CurrentUserDep, db_session: SessionDep):
    """Returns user-specific statistics: balance, investments, loans, transactions."""
    from crud import get_user_deposits, get_user_investments, get_user_loans, get_user_transactions

    deposits = await get_user_deposits(db_session, current_user.id, limit=100)
    investments = await get_user_investments(db_session, current_user.id, limit=100)
    loans = await get_user_loans(db_session, current_user.id, limit=100)
    transactions = await get_user_transactions(db_session, current_user.id, limit=50)

    total_balance = await BalanceServiceLedger.get_user_balance(db_session, current_user.id)
    total_investments = sum(float(i.amount) for i in investments if i.amount) if investments else 0
    total_loans = sum(float(l.amount) for l in loans if l.amount) if loans else 0

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
    """Get user dashboard data with unified balance calculations."""
    try:
        breakdown = await BalanceServiceLedger.get_user_transaction_breakdown(db_session, current_user.id)
        bal = float(breakdown.get("balance", 0))
        dep = float(breakdown.get("deposits", 0))
        wd = float(breakdown.get("withdrawals", 0))
        tr = float(breakdown.get("transfers_received", 0))

        return {
            "user_id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "total_balance": bal,
            "total_deposits": dep,
            "total_withdrawals": wd,
            "total_transfers": tr,
            "transaction_count": 0,
            "breakdown": {
                "deposits": dep,
                "withdrawals": wd,
                "transfers": tr,
                "balance": bal
            },
            "is_verified": getattr(current_user, "is_verified", False),
            "is_active": getattr(current_user, "is_active", True),
            "kyc_status": getattr(current_user, "kyc_status", "not_started")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard data: {str(e)}")


@users_router.get("/me/balance")
async def get_user_balance(current_user: CurrentUserDep, db_session: SessionDep):
    """Get user's current authoritative balance."""
    try:
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
    """Get user's total deposit amount."""
    try:
        total = await BalanceServiceLedger.get_user_deposit_total(db_session, current_user.id)
        return {
            "user_id": current_user.id,
            "total_deposits": total,
            "currency": "USD"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating deposits: {str(e)}")


@users_router.get("/me", response_model=PydanticUser)
@users_router.get("/me/", response_model=PydanticUser)
async def read_users_me(current_user: CurrentUserDep):
    return current_user


@users_router.get("/profile")
async def read_users_profile(current_user: CurrentUserDep, db_session: SessionDep):
    """Get current user's profile (used by admin_profile.html and user profile pages)."""
    bal = await BalanceServiceLedger.get_user_balance(db_session, current_user.id)
    return {
        "success": True,
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name or current_user.email,
        "phone": getattr(current_user, "phone", None) or "+1 (555) 019-2834",
        "address": getattr(current_user, "address", None) or "100 Financial Plaza, Suite 400",
        "country": getattr(current_user, "country", None) or "United States",
        "region": getattr(current_user, "region", None) or "NY",
        "account_number": getattr(current_user, "account_number", None) or f"ACC-{current_user.id:06d}",
        "account_type": getattr(current_user, "account_type", None) or ("admin" if current_user.is_admin else "checking"),
        "role": getattr(current_user, "admin_role", None) or ("SUPER_ADMIN" if current_user.is_admin else "USER"),
        "admin_role": getattr(current_user, "admin_role", None) or ("SUPER_ADMIN" if current_user.is_admin else "USER"),
        "is_admin": bool(current_user.is_admin),
        "is_active": bool(current_user.is_active),
        "is_verified": bool(getattr(current_user, "is_verified", True)),
        "kyc_status": getattr(current_user, "kyc_status", "approved"),
        "mfa_enabled": bool(getattr(current_user, "mfa_enabled", False)),
        "balance": bal,
        "created_at": current_user.created_at.isoformat() if getattr(current_user, "created_at", None) else None,
    }


@users_router.put("/profile")
@users_router.post("/profile")
async def update_users_profile(
    payload: dict,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    """Update current user's profile."""
    for field in ("full_name", "phone", "address", "country", "region"):
        if field in payload and payload[field] is not None and hasattr(current_user, field):
            setattr(current_user, field, payload[field])
    db_session.add(current_user)
    await db_session.commit()
    await db_session.refresh(current_user)
    return {
        "success": True,
        "message": "Profile updated successfully",
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": getattr(current_user, "phone", None),
        "address": getattr(current_user, "address", None),
    }



@users_router.get("/{user_id}", response_model=PydanticUser)
async def read_user(user_id: int, db_session: SessionDep, current_user: CurrentUserDep):
    """Get a user's profile by ID."""
    if current_user.is_admin:
        db_user = await get_user(db_session, user_id)
        if db_user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return db_user

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
    _perm=Depends(require_permission("users:view")),
    skip: int = 0,
    limit: int = 100
):
    """List all users (admin only)."""
    users = await get_users(db_session, skip=skip, limit=limit)
    return users
