from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentUserDep, SessionDep
from models import Transaction as PydanticTransaction, TransactionCreate
from crud import get_transaction, create_user_transaction, get_transactions

transactions_router = APIRouter(prefix="/transactions", tags=["transactions"])

@transactions_router.post("/", response_model=PydanticTransaction, status_code=status.HTTP_201_CREATED)
async def create_transaction_for_current_user(
    transaction: TransactionCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    return await create_user_transaction(db_session=db_session, transaction=transaction, user_id=current_user.id)

@transactions_router.get("/", response_model=List[PydanticTransaction])
async def read_transactions_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    return await get_user_transactions(db_session=db_session, user_id=current_user.id, skip=skip, limit=limit)

@transactions_router.get("/{transaction_id}", response_model=PydanticTransaction)
async def read_transaction_by_id(
    transaction_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    db_transaction = await get_transaction(db_session, transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    if db_transaction.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this transaction")
    return db_transaction
