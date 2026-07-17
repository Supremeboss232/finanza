from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict

from services.investment_portfolio_service import InvestmentPortfolioService

router = APIRouter(prefix="/investments", tags=["investments"])


class PositionInput(BaseModel):
    symbol: str
    shares: float
    price: float


@router.post("/portfolio/value")
async def portfolio_value(positions: List[PositionInput]):
    """Return a simple portfolio valuation summary for development use."""
    return InvestmentPortfolioService.calculate_portfolio_value(
        [position.dict() for position in positions]
    )
