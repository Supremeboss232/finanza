from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from deps import CurrentUserDep, SessionDep
from models import Card as PydanticCard, CardCreate
from crud import get_user_cards, create_user_card, get_card

cards_router = APIRouter(prefix="/cards", tags=["cards"])

@cards_router.post("/", response_model=PydanticCard, status_code=status.HTTP_201_CREATED)
async def create_card_for_current_user(
    card: CardCreate,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    return await create_user_card(db_session=db_session, card=card, user_id=current_user.id)

@cards_router.get("/", response_model=List[PydanticCard])
async def read_cards_for_current_user(
    current_user: CurrentUserDep,
    db_session: SessionDep,
    skip: int = 0,
    limit: int = 100
):
    return await get_user_cards(db_session=db_session, user_id=current_user.id, skip=skip, limit=limit)

@cards_router.get("/{card_id}", response_model=PydanticCard)
async def read_card_by_id(
    card_id: int,
    current_user: CurrentUserDep,
    db_session: SessionDep
):
    db_card = await get_card(db_session, card_id)
    if db_card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    if db_card.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this card")
    return db_card
