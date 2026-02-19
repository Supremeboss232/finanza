from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentUserDep, SessionDep
from models import Investment as PydanticInvestment, InvestmentCreate
from crud import get_user_investments, create_user_investment, get_investment

investments_router = APIRouter(prefix="/investments", tags=["investments"])

@investments_router.post("/", response_model=PydanticInvestment, status_code=status.HTTP_201_CREATED)
async def create_investment_for_current_user(
    investment: InvestmentCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    return await create_user_investment(db_session=db_session, investment=investment, user_id=current_user.id)

@investments_router.get("/", response_model=List[PydanticInvestment])
async def read_investments_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    return await get_user_investments(db_session=db_session, user_id=current_user.id, skip=skip, limit=limit)

@investments_router.get("/{investment_id}", response_model=PydanticInvestment)
async def read_investment_by_id(
    investment_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    db_investment = await get_investment(db_session, investment_id)
    if db_investment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investment not found")
    if db_investment.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this investment")
    return db_investment
