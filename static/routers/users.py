from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentUserDep, SessionDep
from models import User as PydanticUser, UserBase
from crud import get_user, get_users, create_user

users_router = APIRouter(prefix="/users", tags=["users"])

@users_router.post("/", response_model=PydanticUser, status_code=status.HTTP_201_CREATED)
async def create_new_user(user: UserBase, db_session: SessionDep):
    db_user = await get_user(db_session, user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    # For simplicity, password handling during creation is moved to auth.register
    # This endpoint is more for admin or internal creation without direct password
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="Please use /auth/register to create a user.")

@users_router.get("/me/", response_model=PydanticUser)
async def read_users_me(current_user: CurrentUserDep):
    return current_user

@users_router.get("/{user_id}", response_model=PydanticUser)
async def read_user(user_id: int, db_session: SessionDep):
    db_user = await get_user(db_session, user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user

@users_router.get("/", response_model=List[PydanticUser])
async def read_all_users(db_session: SessionDep, skip: int = 0, limit: int = 100, current_user: CurrentUserDep = None):
    # This endpoint would typically be admin-only or require specific permissions
    # For now, it's accessible to any logged-in user.
    # Consider adding admin-specific dependency here: Depends(get_current_admin_user)
    users = await get_users(db_session, skip=skip, limit=limit)
    return users
