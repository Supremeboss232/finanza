from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.card_processing_service import CardProcessingService

router = APIRouter(prefix="/cards", tags=["cards"])


class CardValidationRequest(BaseModel):
    card_number: str
    amount: float = 0.0


@router.post("/validate")
async def validate_card(request: CardValidationRequest):
    """Validate a card number and simulate an authorization attempt."""
    is_valid = CardProcessingService.validate_card_number(request.card_number)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Card number is invalid")

    return CardProcessingService.authorize(request.amount, request.card_number)
