from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated
import uuid
import json
from decimal import Decimal

from deps import CurrentUserDep, SessionDep
from schemas import Deposit as PydanticDeposit, DepositCreate, TransactionCreate
from crud import get_user_deposits, create_user_deposit, get_deposit, create_user_transaction
from transaction_validator import TransactionValidator
from models import Account as DBAccount, User as DBUser, Transaction as DBTransaction
from ws_manager import manager

deposits_router = APIRouter(prefix="/api/v1/deposits", tags=["deposits"])


@deposits_router.post("/", response_model=PydanticDeposit, status_code=status.HTTP_201_CREATED)
async def create_deposit_for_current_user(
    deposit: DepositCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep,
):
    """
    Create a Term / Savings Deposit for the current user by locking funds from their
    existing Account balance (never minting unbacked funds).
    """
    try:
        is_valid, reason = await TransactionValidator.validate_deposit(
            db=db_session,
            user_id=current_user.id,
            amount=deposit.amount,
            account_id=getattr(deposit, "account_id", None),
        )
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        account_result = await db_session.execute(
            select(DBAccount).where(DBAccount.owner_id == current_user.id).order_by(DBAccount.id.asc()).limit(1)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no active bank account")

        amount = float(deposit.amount)
        available = float(account.balance or 0)
        if available < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient account balance (${available:,.2f} available) to lock ${amount:,.2f} into a term deposit.",
            )

        # Deduct from available account balance to fund term deposit
        account.balance = Decimal(str(round(available - amount, 2)))
        db_session.add(account)

        reference_number = f"DEPL-{uuid.uuid4().hex[:10].upper()}"
        transaction = DBTransaction(
            user_id=current_user.id,
            account_id=account.id,
            transaction_type="deposit_lock",
            amount=Decimal(str(round(amount, 2))),
            status="completed",
            direction="debit",
            description="Term / Savings Deposit Lock",
            reference_number=reference_number,
            kyc_status_at_time=current_user.kyc_status,
        )
        db_session.add(transaction)

        db_deposit = await create_user_deposit(db=db_session, deposit=deposit, user_id=current_user.id)
        await db_session.commit()
        await db_session.refresh(transaction)

        try:
            await manager.broadcast(json.dumps({
                "event": "deposit:created",
                "user_id": current_user.id,
                "amount": amount,
                "new_balance": float(account.balance or 0),
                "status": "completed",
                "reference": reference_number,
            }))
        except Exception:
            pass

        return db_deposit
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deposit: {str(e)}",
        )


@deposits_router.get("/", response_model=List[PydanticDeposit])
async def read_deposits_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100,
):
    return await get_user_deposits(db=db_session, user_id=current_user.id, skip=skip, limit=limit)


@deposits_router.get("/{deposit_id}", response_model=PydanticDeposit)
async def read_deposit_by_id(
    deposit_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep,
):
    db_deposit = await get_deposit(db_session, deposit_id)
    if db_deposit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit not found")
    if db_deposit.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this deposit")
    return db_deposit
