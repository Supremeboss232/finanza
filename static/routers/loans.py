from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentUserDep, SessionDep
from models import Loan as PydanticLoan, LoanCreate
from crud import get_user_loans, create_user_loan, get_loan

loans_router = APIRouter(prefix="/loans", tags=["loans"])

@loans_router.post("/", response_model=PydanticLoan, status_code=status.HTTP_201_CREATED)
async def create_loan_for_current_user(
    loan: LoanCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    return await create_user_loan(db_session=db_session, loan=loan, user_id=current_user.id)

@loans_router.get("/", response_model=List[PydanticLoan])
async def read_loans_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    return await get_user_loans(db_session=db_session, user_id=current_user.id, skip=skip, limit=limit)

@loans_router.get("/{loan_id}", response_model=PydanticLoan)
async def read_loan_by_id(
    loan_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    db_loan = await get_loan(db_session, loan_id)
    if db_loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if db_loan.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this loan")
    return db_loan
