from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentAdminUserDep, SessionDep
from models import User as PydanticUser, Transaction as PydanticTransaction, FormSubmission as PydanticFormSubmission, UserCreate
from crud import get_users, create_user, get_transactions, get_form_submissions, get_user_by_username
from schemas import User as DBUser

admin_router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(CurrentAdminUserDep)])

@admin_router.get("/users/", response_model=List[PydanticUser])
async def read_all_users_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    users = await get_users(db_session, skip=skip, limit=limit)
    return users

@admin_router.post("/users/", response_model=PydanticUser, status_code=status.HTTP_201_CREATED)
async def create_new_user_admin(user: UserCreate, db_session: SessionDep):
    db_user = await get_user_by_username(db_session, user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    # You might want to add more validation or default values for admin-created users
    return await create_user(db_session=db_session, user=user)

@admin_router.get("/transactions/", response_model=List[PydanticTransaction])
async def read_all_transactions_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    transactions = await get_transactions(db_session, skip=skip, limit=limit)
    return transactions

@admin_router.get("/forms/", response_model=List[PydanticFormSubmission])
async def read_all_form_submissions_admin(
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    submissions = await get_form_submissions(db_session, skip=skip, limit=limit)
    return submissions

# Add more admin-specific routes for updates, deletions, etc.
# For example, to change a user's admin status
@admin_router.put("/users/{user_id}/set_admin", response_model=PydanticUser)
async def set_user_admin_status(user_id: int, is_admin: bool, db_session: SessionDep):
    from sqlalchemy import select
    db_user = await db_session.execute(select(DBUser).filter(DBUser.id == user_id))
    user_to_update = db_user.scalar_one_or_none()
    if not user_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user_to_update.is_admin = is_admin
    await db_session.commit()
    await db_session.refresh(user_to_update)
    return PydanticUser.model_validate(user_to_update)
