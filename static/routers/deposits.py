from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentUserDep, SessionDep
from models import Deposit as PydanticDeposit, DepositCreate
from crud import get_user_deposits, create_user_deposit, get_deposit

deposits_router = APIRouter(prefix="/deposits", tags=["deposits"])

@deposits_router.post("/", response_model=PydanticDeposit, status_code=status.HTTP_201_CREATED)
async def create_deposit_for_current_user(
    deposit: DepositCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    return await create_user_deposit(db_session=db_session, deposit=deposit, user_id=current_user.id)

@deposits_router.get("/", response_model=List[PydanticDeposit])
async def read_deposits_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    return await get_user_deposits(db_session=db_session, user_id=current_user.id, skip=skip, limit=limit)

@deposits_router.get("/{deposit_id}", response_model=PydanticDeposit)
async def read_deposit_by_id(
    deposit_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    db_deposit = await get_deposit(db_session, deposit_id)
    if db_deposit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deposit not found")
    if db_deposit.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this deposit")
    return db_deposit
